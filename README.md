# mcp-server-redcap

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server for interacting with [REDCap](https://projectredcap.org/) (Research Electronic Data Capture) instances.

Exposes 38 tools covering data access, project design, file management, and longitudinal project structure. Designed for use with LLM agents that need to query or build REDCap projects in natural language conversations.

## Tools

### Records

| Tool | Description |
|------|-------------|
| `export_records` | Export records with optional filters by field, record ID, or event |
| `import_records` | Import records from a JSON payload |
| `delete_records` | Delete records by ID |
| `export_report` | Export a saved REDCap report by its ID |
| `export_field_names` | Export the mapping from field names to export names (required for checkbox fields) |
| `generate_next_record_name` | Get the next available record ID respecting the project's auto-numbering |

### Metadata

| Tool | Description |
|------|-------------|
| `get_project_info` | Retrieve project-level information and settings |
| `get_metadata` | Export the data dictionary, optionally filtered by field or form |
| `export_logging` | Export the project audit log, with filters by type, user, record, or date range |
| `export_repeating_instruments_events` | Export the repeating instruments/events configuration |
| `import_repeating_instruments_events` | Update the repeating instruments/events configuration |

### Instruments & project design

| Tool | Description |
|------|-------------|
| `get_instruments` | List all instruments with internal names and display labels |
| `get_instrument_event_mappings` | List arm/event/instrument mappings (longitudinal projects) |
| `add_field` | Add a new field to an instrument (round-trip through data dictionary) |
| `remove_field` | Remove a field from the data dictionary |
| `update_field` | Update specific properties of a field without touching the rest |
| `add_instrument` | Create a new instrument |
| `delete_instrument` | Delete an instrument and all its fields |
| `rename_instrument` | Rename an instrument's internal name |
| `move_field` | Reposition a field within the data dictionary |
| `clone_instrument` | Copy all fields of an instrument into a new one with a field-name prefix |
| `assign_instrument_to_event` | Add an instrument to a longitudinal event |
| `unassign_instrument_from_event` | Remove an instrument from a longitudinal event |

### Analysis

| Tool | Description |
|------|-------------|
| `get_project_structure` | Compact overview of the whole project: instruments, field counts, event matrix |
| `check_field_references` | Find all fields that reference a given field in branching logic or calculations |
| `validate_branching_logic` | Scan all branching logic for references to non-existent fields |

### Files

| Tool | Description |
|------|-------------|
| `export_file` | Download a file attachment from a record field (returned as base64) |
| `import_file` | Upload a file to a record field (accepts base64 content) |
| `delete_file` | Delete a file attachment from a record field |
| `export_pdf` | Export a PDF of one or more instruments for a record (returned as base64) |

### Arms & events (longitudinal)

| Tool | Description |
|------|-------------|
| `export_arms` | List arms |
| `import_arms` | Create or update arms |
| `delete_arms` | Delete arms by number |
| `export_events` | List events, optionally filtered by arm |
| `import_events` | Create or update events |
| `delete_events` | Delete events by unique name |

### Surveys

| Tool | Description |
|------|-------------|
| `export_survey_link` | Get a participant-specific survey URL for a record |
| `export_survey_participant_list` | List survey participants and their response status |

## Installation

```bash
pip install mcp-server-redcap
```

Or with `uv`:

```bash
uvx mcp-server-redcap
```

## REDCap version compatibility

The server works against any REDCap instance running **version 8.0 or later**. Most tools are available from version 6.x, but `export_pdf` requires 8.x. Repeating instruments (`export_repeating_instruments_events`, `import_repeating_instruments_events`) require 6.16+. Tools that are unavailable on a given instance return a plain error string rather than crashing.

The current REDCap version of the connected instance is included in the output of `get_project_structure`.

## Configuration

The server reads connection details from environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `REDCAP_URL` | Yes | Full REDCap API endpoint URL (e.g. `https://redcap.example.org/api/`) |
| `REDCAP_TOKEN` | Yes | Project-level API token from REDCap → API → Generate Token |
| `REDCAP_VERIFY_SSL` | No | Set to `false` to skip SSL verification (default: `true`) |

Create a `.env` file in your working directory and the server will load it automatically:

```env
REDCAP_URL=https://redcap.example.org/api/
REDCAP_TOKEN=your_project_token_here
```

## Usage with Claude Code

Add the server to your Claude Code MCP configuration:

```bash
claude mcp add redcap -e REDCAP_URL=https://redcap.example.org/api/ \
                      -e REDCAP_TOKEN=your_token -- uvx mcp-server-redcap
```

Or edit `.claude/settings.json` manually:

```json
{
  "mcpServers": {
    "redcap": {
      "command": "uvx",
      "args": ["mcp-server-redcap"],
      "env": {
        "REDCAP_URL": "https://redcap.example.org/api/",
        "REDCAP_TOKEN": "your_project_token_here"
      }
    }
  }
}
```

## Development

```bash
git clone https://github.com/msicilia/mcp-server-redcap
cd mcp-server-redcap
uv sync --extra dev
```

Run the MCP inspector for interactive local testing:

```bash
uv run mcp dev src/mcp_server_redcap/server.py
```

Run the server directly (stdio transport, for use with MCP clients):

```bash
uv run mcp-server-redcap
```

## Project structure

```
src/mcp_server_redcap/
├── __init__.py
├── __main__.py          # python -m mcp_server_redcap
├── server.py            # FastMCP server factory and entry point
├── connection.py        # REDCap project connection (lazy, singleton)
└── tools/
    ├── __init__.py
    ├── records.py       # record CRUD, field names, next record name
    ├── metadata.py      # project info, data dictionary, logging, repeating instruments
    ├── instruments.py   # instrument listing, field and instrument mutations
    ├── analysis.py      # project structure overview, reference and logic validation
    ├── files.py         # file attachments and PDF export
    ├── arms_events.py   # longitudinal arms and events CRUD
    └── surveys.py       # survey links and participant lists
```

See [DESIGN.md](https://github.com/msicilia/mcp-server-redcap/blob/master/DESIGN.md) for the full API reference and design rationale.

## License

MIT
