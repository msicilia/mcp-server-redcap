# mcp-server-redcap — Design & API Reference

## Purpose

This MCP server exposes a [REDCap](https://projectredcap.org/) project to LLM agents via the [Model Context Protocol](https://modelcontextprotocol.io). It wraps the REDCap API (through the [PyCap](https://pycap.readthedocs.io/) Python client) into a set of tools that an agent can call to read, build, and modify a REDCap project in natural language conversations.

The primary use cases are:

- **Project building** — an agent helping a researcher design instruments, fields, and longitudinal structure piece by piece
- **Data access** — an agent querying, importing, or auditing research data on behalf of a user
- **Project maintenance** — an agent refactoring an existing project (renaming fields, reorganising instruments, fixing branching logic)

---

## Design principles

### 1. One project per server instance

Each server instance is bound to a single REDCap project via `REDCAP_URL` + `REDCAP_TOKEN`. There is no multi-project routing. This is a deliberate constraint: it keeps the authentication model simple, matches how REDCap tokens work (one token per project), and means the agent never has to specify which project it is talking to.

### 2. Atomic round-trips for mutations

REDCap does not expose field-level or instrument-level write endpoints. All structural mutations (adding a field, renaming an instrument, reordering fields) use the same pattern:

```
export_metadata → mutate the list in Python → import_metadata
```

This is handled entirely inside the tool. The caller never sees the intermediate state and never has to manage the full data dictionary. This makes tools safe for an LLM to use: "add field X to instrument Y" is a single tool call, not a read-modify-write sequence the agent has to orchestrate.

### 3. The agent should not manage raw dictionaries

Early MCP designs for REDCap typically exposed only `get_metadata` + `import_metadata` and expected the agent to handle the full dictionary. This works for humans reading API docs but fails for agents: the dictionary has ~18 columns per field, ordering matters, field names must be unique across the whole project, and REDCap will silently accept a broken import in some cases. The smart tools encapsulate this complexity.

### 4. Read tools stay simple; write tools validate first

Read tools (`get_metadata`, `export_records`, etc.) pass through PyCap with minimal transformation and return JSON strings. Write tools validate pre-conditions before mutating — for example, `add_field` checks for duplicate field names, `move_field` validates both the source and target positions before calling `pop()`, and `clone_instrument` checks for name collisions before touching the dictionary. If a pre-condition fails the tool returns an error string and makes no API call.

### 5. Binary content is base64-encoded

`export_file` and `export_pdf` return binary content. MCP tool results must be strings, so binary content is returned as a base64-encoded JSON envelope:

```json
{ "content_base64": "...", "content_type": "application/pdf", "filename": "..." }
```

`import_file` accepts the same base64 format, so an agent can pipeline an export → transform → import without leaving the MCP tool surface.

### 6. Destructive operations on instruments are deliberate

`delete_instrument` removes all fields in a form in a single call. `rename_instrument` changes the internal `form_name` on every field. These are intentionally blunt: the agent should call `check_field_references` and `validate_branching_logic` first if safety matters. Providing both the safety-check tools and the destructive tools, rather than baking guardrails into the destructive tools themselves, keeps the tools composable and avoids hidden latency on every call.

### 7. Longitudinal-only tools fail gracefully

Tools that only apply to longitudinal projects (`assign_instrument_to_event`, `unassign_instrument_from_event`, `export_arms`, etc.) return a plain error string if called on a non-longitudinal project. They do not raise exceptions that would surface as MCP errors. This lets the agent recover and explain the situation to the user without crashing the tool call.

### 8. Administrative operations are excluded

User management (`import_users`, `import_user_roles`, DAG assignment) is intentionally absent. An agent touching user permissions is a security concern disproportionate to the benefit, and these operations are low-frequency enough that a human doing them in the REDCap UI is the right answer. The full rationale is in the [What is excluded](#what-is-excluded) section.

---

## Tool reference

Tools are organised by module. Each module corresponds to a file under `src/mcp_server_redcap/tools/`.

---

### Records (`tools/records.py`)

Core data access. These are the most frequently called tools.

#### `export_records`

Export records from the project with optional filters.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `fields` | `list[str] \| None` | `None` | Field names to include. `None` = all fields. |
| `records` | `list[str] \| None` | `None` | Record IDs to include. `None` = all records. |
| `events` | `list[str] \| None` | `None` | Event names to include (longitudinal only). |
| `raw_or_label` | `str` | `"raw"` | `"raw"` for coded values, `"label"` for display labels. |
| `export_checkbox_label` | `bool` | `False` | Export checkbox labels instead of 0/1. |
| `limit` | `int` | `1000` | Maximum number of records returned. |

Returns a JSON array of record objects. The `limit` parameter is applied client-side after the API call; for very large projects, filter with `fields` and `records` instead.

#### `import_records`

Import records into the project.

| Parameter | Type | Description |
|-----------|------|-------------|
| `data` | `str` | JSON array of record objects. Each must include the record-ID field. |

Returns a confirmation string with the count of imported records.

#### `delete_records`

Delete records by ID.

| Parameter | Type | Description |
|-----------|------|-------------|
| `record_ids` | `list[str]` | Record IDs to delete. |

#### `export_report`

Export a saved REDCap report by its numeric ID (visible in the REDCap URL when viewing the report).

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_id` | `str` | Numeric report ID. |

#### `export_field_names`

Export the mapping from original field names to export field names. Essential for checkbox fields, which are exported as `fieldname___code` rather than `fieldname`. Use this before constructing `fields` filters for `export_records`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `field` | `str \| None` | `None` | Filter to a specific field. `None` = all fields. |

#### `generate_next_record_name`

Returns the next available record name as a string, respecting the project's auto-numbering scheme. Call this before `import_records` when adding a new record to avoid ID collisions.

---

### Metadata (`tools/metadata.py`)

Project-level information and data dictionary access.

#### `get_project_info`

Returns project title, PI name, creation time, longitudinal status, survey settings, and other project-level flags as a JSON object.

#### `get_metadata`

Export the data dictionary, optionally filtered.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `fields` | `list[str] \| None` | `None` | Filter to specific field names. |
| `forms` | `list[str] \| None` | `None` | Filter to specific instrument names. |

Returns a JSON array of field definition objects. Each object has 18 columns including `field_name`, `form_name`, `field_type`, `field_label`, `select_choices_or_calculations`, `branching_logic`, `required_field`, and others.

#### `export_logging`

Export the project audit log.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `log_type` | `str \| None` | `None` | One of: `export`, `manage`, `user`, `record`, `record_add`, `record_edit`, `record_delete`, `lock_record`, `page_view`. |
| `user` | `str \| None` | `None` | Filter to a specific REDCap username. |
| `record` | `str \| None` | `None` | Filter to a specific record ID. |
| `begin_time` | `str \| None` | `None` | Start of date range (ISO 8601, e.g. `2024-01-01T00:00:00`). |
| `end_time` | `str \| None` | `None` | End of date range (ISO 8601). |

#### `export_repeating_instruments_events`

Returns the repeating instruments/events configuration as a JSON array. Returns an empty array if the project has no repeating instruments.

#### `import_repeating_instruments_events`

| Parameter | Type | Description |
|-----------|------|-------------|
| `data` | `str` | JSON array of repeating instrument/event definition objects. |

---

### Instruments (`tools/instruments.py`)

Instrument listing, field-level mutations, and instrument-level mutations. This is the most tool-rich module because it covers both the read side (listing instruments and event mappings) and the structural write side (all round-trip metadata operations).

#### `get_instruments`

Returns the list of instruments with internal names and display labels as a JSON array.

#### `get_instrument_event_mappings`

Returns the arm/event/instrument mapping matrix as a JSON array (longitudinal projects only). Returns an error string for non-longitudinal projects.

---

#### Field-level mutations (round-trip)

All three tools export the full data dictionary, make a targeted mutation, and import the result.

#### `add_field`

Add a new field to an existing instrument.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `form_name` | `str` | — | Instrument to add the field to. |
| `field_name` | `str` | — | Variable name (lowercase, underscores only). |
| `field_type` | `str` | — | One of: `text`, `notes`, `calc`, `radio`, `checkbox`, `yesno`, `truefalse`, `select`, `slider`, `file`, `descriptive`. |
| `field_label` | `str` | — | Display label shown during data entry. |
| `choices` | `str \| None` | `None` | Choice definitions for `radio`/`checkbox`/`select`: `"1, Label 1 \| 2, Label 2"`. |
| `required` | `bool` | `False` | Whether the field must be completed before saving. |
| `branching_logic` | `str \| None` | `None` | Show/hide logic, e.g. `"[age] > 18"`. |
| `field_note` | `str \| None` | `None` | Helper text shown below the field. |
| `section_header` | `str \| None` | `None` | Section header displayed above this field. |
| `validation` | `str \| None` | `None` | Validation type for `text` fields (e.g. `integer`, `number`, `date_ymd`, `email`). |
| `validation_min` | `str \| None` | `None` | Minimum allowed value. |
| `validation_max` | `str \| None` | `None` | Maximum allowed value. |
| `field_annotation` | `str \| None` | `None` | REDCap action tags, e.g. `@HIDDEN`. |
| `after_field` | `str \| None` | `None` | Insert after this field. `None` appends at end of instrument. |

Returns an error string if `field_name` already exists anywhere in the project.

#### `remove_field`

Remove a field from the data dictionary.

| Parameter | Type | Description |
|-----------|------|-------------|
| `field_name` | `str` | Variable name to remove. |

REDCap will reject removal of the record-ID field and will reject removals that leave a calculated field or branching logic expression with a broken reference. Run `check_field_references` first.

#### `update_field`

Update specific properties of an existing field. Only the parameters you pass are changed; everything else is preserved.

| Parameter | Type | Description |
|-----------|------|-------------|
| `field_name` | `str` | Field to update (required). |
| `field_label` | `str \| None` | New display label. |
| `field_note` | `str \| None` | New helper text. |
| `required` | `bool \| None` | `True` = required, `False` = optional. |
| `branching_logic` | `str \| None` | New show/hide expression. |
| `choices` | `str \| None` | New choice definitions. |
| `validation` | `str \| None` | New validation type. |
| `validation_min` | `str \| None` | New minimum value. |
| `validation_max` | `str \| None` | New maximum value. |
| `field_annotation` | `str \| None` | New action tags. |
| `section_header` | `str \| None` | New section header. |

---

#### Instrument-level mutations (round-trip)

#### `add_instrument`

Create a new instrument by inserting a placeholder descriptive field. The placeholder field can be removed with `remove_field` once real fields have been added.

| Parameter | Type | Description |
|-----------|------|-------------|
| `form_name` | `str` | Internal name (lowercase, underscores). |

**Note:** The instrument display label defaults to the prettified `form_name` and can only be changed in the REDCap UI (Designer → instrument name). The REDCap API does not support setting instrument labels programmatically.

#### `delete_instrument`

Remove an instrument and all its fields.

| Parameter | Type | Description |
|-----------|------|-------------|
| `form_name` | `str` | Internal name of the instrument to delete. |

#### `rename_instrument`

Change the internal `form_name` across all fields of an instrument. Does not change the display label (REDCap UI only).

| Parameter | Type | Description |
|-----------|------|-------------|
| `old_form_name` | `str` | Current internal name. |
| `new_form_name` | `str` | New internal name. |

#### `move_field`

Reposition a field within the data dictionary. Field order controls data-entry screen layout and survey page flow.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `field_name` | `str` | — | Field to move. |
| `after_field` | `str \| None` | `None` | Move after this field. `None` moves to end of the field's own instrument. |

The record-ID field (always first in the dictionary) cannot be moved.

#### `clone_instrument`

Copy all fields of an instrument into a new instrument, prefixing each field name.

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_form` | `str` | Instrument to clone. |
| `new_form_name` | `str` | Internal name for the new instrument. |
| `field_prefix` | `str` | Prefix to prepend to every cloned field name (e.g. `v2_`). |

Branching logic is cleared on cloned fields because it references original field names. Update it with `update_field` after cloning. Returns an error if any prefixed name would collide with an existing field.

---

#### Longitudinal instrument assignment

#### `assign_instrument_to_event`

Add an instrument to an event in the longitudinal matrix.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `instrument` | `str` | — | Internal form name. |
| `event` | `str` | — | Unique event name (e.g. `baseline_arm_1`). |
| `arm_num` | `int` | `1` | Arm number the event belongs to. |

#### `unassign_instrument_from_event`

Remove an instrument from an event.

| Parameter | Type | Description |
|-----------|------|-------------|
| `instrument` | `str` | Internal form name. |
| `event` | `str` | Unique event name. |

---

### Analysis (`tools/analysis.py`)

Read-only tools for orientation and safety checking. These make no writes and are safe to call at any time.

#### `get_project_structure`

Returns a compact structural overview of the entire project in a single call. Designed to orient an agent before it begins making changes.

Includes:
- Project title, longitudinal status, survey and autonumbering flags
- Per-instrument: field count and breakdown of field types
- For longitudinal projects: full event list with arm, day offset, and which instruments are assigned

No parameters.

#### `check_field_references`

Scan the entire data dictionary for fields that reference a given field name in their branching logic or calculated field formula. Uses exact `[field_name]` matching (not substring), and handles the `[field_name(checkbox_code)]` checkbox syntax.

| Parameter | Type | Description |
|-----------|------|-------------|
| `field_name` | `str` | Field name to search for. |

Returns a list of referencing fields with instrument, reference type, and the full expression. Returns a "safe to remove" message if no references exist.

**Usage pattern:** call this before `remove_field` or `rename_instrument` to identify downstream breakage.

#### `validate_branching_logic`

Scan every branching logic expression in the data dictionary and flag references to field names that do not exist. For longitudinal projects, event names are excluded from the check to avoid false positives on `[event_name][field_name]` syntax.

No parameters. Returns a confirmation if all references are valid, or a JSON list of issues with field, instrument, unresolved reference, and the full expression.

---

### Files (`tools/files.py`)

File attachment management. Binary content is transported as base64-encoded strings.

#### `export_file`

Download a file attachment from a record field.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `record` | `str` | — | Record ID. |
| `field` | `str` | — | File upload field name. |
| `event` | `str \| None` | `None` | Event name (longitudinal only). |
| `repeat_instance` | `int \| None` | `None` | Repeat instance number. |

Returns `{ "content_base64": "...", "content_type": "...", "filename": "..." }`.

#### `import_file`

Upload a file into a record field.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `record` | `str` | — | Record ID. |
| `field` | `str` | — | File upload field name. |
| `file_name` | `str` | — | Name to give the file in REDCap. |
| `content_base64` | `str` | — | Base64-encoded file content. |
| `event` | `str \| None` | `None` | Event name (longitudinal only). |
| `repeat_instance` | `int \| None` | `None` | Repeat instance number. |

#### `delete_file`

Delete a file attachment from a record field.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `record` | `str` | — | Record ID. |
| `field` | `str` | — | File upload field name. |
| `event` | `str \| None` | `None` | Event name (longitudinal only). |

#### `export_pdf`

Export a PDF of one or more instruments for a record.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `record` | `str \| None` | `None` | Record ID. `None` exports all records (use with caution on large projects). |
| `event` | `str \| None` | `None` | Event name (longitudinal only). |
| `instrument` | `str \| None` | `None` | Specific instrument. `None` exports all instruments. |
| `repeat_instance` | `int \| None` | `None` | Repeat instance number. |
| `compact_display` | `bool \| None` | `None` | Use compact PDF layout. |

Returns `{ "content_base64": "..." }`.

---

### Arms & Events (`tools/arms_events.py`)

Longitudinal project structure management. All six tools apply to longitudinal projects only; calling them on a non-longitudinal project will produce a REDCap API error.

#### `export_arms`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `arms` | `list[str] \| None` | `None` | Specific arm numbers. `None` = all arms. |

#### `import_arms`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `data` | `str` | — | JSON array of arm objects with `arm_num` and `name`. |
| `override` | `bool` | `False` | If `True`, arms absent from the import are deleted. |

#### `delete_arms`

| Parameter | Type | Description |
|-----------|------|-------------|
| `arms` | `list[str]` | Arm numbers to delete. |

#### `export_events`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `arms` | `list[str] \| None` | `None` | Filter to specific arm numbers. |

#### `import_events`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `data` | `str` | — | JSON array of event objects. |
| `override` | `bool` | `False` | If `True`, events absent from the import are deleted. |

#### `delete_events`

| Parameter | Type | Description |
|-----------|------|-------------|
| `events` | `list[str]` | Unique event names to delete. |

---

### Surveys (`tools/surveys.py`)

Survey participant management. Both tools require the target instrument to be enabled as a survey in REDCap.

#### `export_survey_link`

Get a unique, participant-specific survey URL.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `record` | `str` | — | Record ID of the participant. |
| `instrument` | `str` | — | Survey instrument name. |
| `event` | `str \| None` | `None` | Event name (longitudinal only). |
| `repeat_instance` | `int` | `1` | Repeat instance number. |

Returns the URL as a plain string.

#### `export_survey_participant_list`

Export the list of participants for a survey instrument.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `instrument` | `str` | — | Survey instrument name. |
| `event` | `str \| None` | `None` | Event name (longitudinal only). |

Returns a JSON array of participant objects including email, name, and response status.

---

## What is excluded

### User and role management

`export_users`, `import_users`, `delete_users`, `export_user_roles`, `import_user_roles`, `export_user_dag_assignment`, and related tools are intentionally not exposed.

**Rationale:** These are administrative operations with a large blast radius (misconfiguring user rights can expose data to the wrong people or lock legitimate users out), they are low-frequency (typically done once at project setup), and doing them in the REDCap UI with a human reviewing the changes is the appropriate control. An autonomous agent touching user permissions in a clinical research system is a risk that outweighs the convenience.

### Data Access Groups (DAGs)

Same rationale as user management. DAG assignment determines which participant records a given user can see; this is a data-governance decision, not a data-entry or project-design decision.

### Survey configuration settings

REDCap allows configuring survey titles, instructions, completion text, auto-continue behaviour, and other per-instrument survey settings. These are not exposed by the REDCap API (and therefore not available in PyCap). They can only be changed in the REDCap UI.

### Project XML export/import

The REDCap API supports `Export Project XML` which returns the full project definition including metadata, instrument settings, and optionally data. PyCap does not wrap this endpoint. It is primarily useful for project migration or backup, which is not an agent-driven workflow.

### REDCap version

`export_version` returns the REDCap instance version string. No agent use case requires this.

---

## Tool count summary

| Module | Tools | Description |
|--------|-------|-------------|
| `records.py` | 6 | Record CRUD, field names, next record name |
| `metadata.py` | 5 | Project info, data dictionary, logging, repeating instruments |
| `instruments.py` | 12 | Instrument listing, field mutations, instrument mutations, event assignment |
| `analysis.py` | 3 | Project structure overview, reference checking, branching logic validation |
| `files.py` | 4 | File attachments and PDF export |
| `arms_events.py` | 6 | Longitudinal arms and events CRUD |
| `surveys.py` | 2 | Survey links and participant lists |
| **Total** | **38** | |

---

## Extending the server

New tools follow the same pattern as existing ones:

1. Add a `register(mcp: FastMCP)` function to an existing module (or create a new one under `tools/`)
2. Define tools as nested functions decorated with `@mcp.tool()`
3. If creating a new module, import and call `register(mcp)` in `server.py`

The connection singleton (`get_project()` in `connection.py`) is thread-safe for read operations. Mutations that do a round-trip through `import_metadata` are not atomic with respect to concurrent edits; this is a REDCap API limitation.
