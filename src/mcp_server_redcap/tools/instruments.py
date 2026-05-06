import json

from mcp.server.fastmcp import FastMCP

from ..connection import get_project

_EMPTY_FIELD: dict = {
    "field_name": "",
    "form_name": "",
    "section_header": "",
    "field_type": "",
    "field_label": "",
    "select_choices_or_calculations": "",
    "field_note": "",
    "text_validation_type_or_show_slider_number": "",
    "text_validation_min": "",
    "text_validation_max": "",
    "identifier": "",
    "branching_logic": "",
    "required_field": "",
    "custom_alignment": "",
    "question_number": "",
    "matrix_group_name": "",
    "matrix_ranking": "",
    "field_annotation": "",
}


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def get_instruments() -> str:
        """Get the list of instruments (forms/surveys) in the REDCap project.

        Returns:
            JSON array of instruments with their internal names and display labels.
        """
        project = get_project()
        result = project.export_instruments(format_type="json")
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def get_instrument_event_mappings() -> str:
        """Get the mapping of instruments to events (longitudinal projects only).

        Returns:
            JSON array of arm/event/instrument mappings, or an error message if
            the project is not longitudinal.
        """
        project = get_project()
        try:
            result = project.export_instrument_event_mappings(format_type="json")
            return json.dumps(result, indent=2, default=str)
        except Exception as exc:
            return f"Could not retrieve event mappings: {exc}"

    @mcp.tool()
    def add_instrument(form_name: str) -> str:
        """Add a new instrument (form) to the project.

        Creates the instrument by inserting a placeholder descriptive field.
        REDCap requires at least one field per instrument; the placeholder can
        be removed later once real fields have been added via add_field.

        Note: the instrument display label defaults to the prettified form_name
        and can only be changed in the REDCap UI (Designer → instrument name).

        Args:
            form_name: Internal name for the instrument (lowercase, underscores, no spaces).

        Returns:
            Confirmation message with the placeholder field name.
        """
        project = get_project()
        dictionary = project.export_metadata(format_type="json")

        if any(f["form_name"] == form_name for f in dictionary):
            return f"Error: instrument '{form_name}' already exists."

        placeholder_name = f"{form_name}_label"
        if any(f["field_name"] == placeholder_name for f in dictionary):
            placeholder_name = f"{form_name}_placeholder"

        new_field = {
            **_EMPTY_FIELD,
            "field_name": placeholder_name,
            "form_name": form_name,
            "field_type": "descriptive",
            "field_label": form_name.replace("_", " ").title(),
        }
        dictionary.append(new_field)

        count = project.import_metadata(to_import=dictionary, return_format_type="json")
        return (
            f"Successfully created instrument '{form_name}' with placeholder field "
            f"'{placeholder_name}' ({count} field(s) updated). "
            f"Add real fields with add_field, then remove the placeholder with remove_field."
        )

    @mcp.tool()
    def delete_instrument(form_name: str) -> str:
        """Delete an instrument and all its fields from the project.

        Removes every field that belongs to the instrument. REDCap will reject
        the operation if the instrument contains the record-ID field.

        Args:
            form_name: Internal name of the instrument to delete.

        Returns:
            Confirmation message with the count of removed fields.
        """
        project = get_project()
        dictionary = project.export_metadata(format_type="json")

        to_keep = [f for f in dictionary if f["form_name"] != form_name]
        removed = len(dictionary) - len(to_keep)
        if removed == 0:
            return f"Error: instrument '{form_name}' not found."

        count = project.import_metadata(to_import=to_keep, return_format_type="json")
        return (
            f"Successfully deleted instrument '{form_name}' and its "
            f"{removed} field(s) ({count} field(s) updated)."
        )

    @mcp.tool()
    def rename_instrument(old_form_name: str, new_form_name: str) -> str:
        """Rename an instrument by updating the form_name on all its fields.

        Note: this changes the internal name only. The display label shown in
        the REDCap UI must be updated separately in Designer.

        Args:
            old_form_name: Current internal name of the instrument.
            new_form_name: New internal name (lowercase, underscores, no spaces).

        Returns:
            Confirmation message with the count of updated fields.
        """
        project = get_project()
        dictionary = project.export_metadata(format_type="json")

        if not any(f["form_name"] == old_form_name for f in dictionary):
            return f"Error: instrument '{old_form_name}' not found."
        if any(f["form_name"] == new_form_name for f in dictionary):
            return f"Error: instrument '{new_form_name}' already exists."

        updated = 0
        for field in dictionary:
            if field["form_name"] == old_form_name:
                field["form_name"] = new_form_name
                updated += 1

        project.import_metadata(to_import=dictionary, return_format_type="json")
        return (
            f"Successfully renamed instrument '{old_form_name}' → '{new_form_name}' "
            f"({updated} field(s) updated)."
        )

    @mcp.tool()
    def move_field(field_name: str, after_field: str | None = None) -> str:
        """Move a field to a new position in the data dictionary.

        Field order controls the layout of data-entry screens and surveys.

        Args:
            field_name: Variable name of the field to move.
            after_field: Move the field immediately after this field name.
                         If None, the field is moved to the end of its own instrument.

        Returns:
            Confirmation message.
        """
        project = get_project()
        dictionary = project.export_metadata(format_type="json")

        field_idx = next(
            (i for i, f in enumerate(dictionary) if f["field_name"] == field_name), None
        )
        if field_idx is None:
            return f"Error: field '{field_name}' not found."
        if field_idx == 0:
            return "Error: cannot move the record-ID field."

        if after_field is not None:
            if after_field == field_name:
                return "Error: cannot move a field after itself."
            if not any(f["field_name"] == after_field for f in dictionary):
                return f"Error: after_field '{after_field}' not found."

        field = dictionary.pop(field_idx)

        if after_field is None:
            form_name = field["form_name"]
            last_idx = next(
                (
                    i for i in range(len(dictionary) - 1, -1, -1)
                    if dictionary[i]["form_name"] == form_name
                ),
                len(dictionary) - 1,
            )
            dictionary.insert(last_idx + 1, field)
        else:
            after_idx = next(i for i, f in enumerate(dictionary) if f["field_name"] == after_field)
            dictionary.insert(after_idx + 1, field)

        project.import_metadata(to_import=dictionary, return_format_type="json")
        target = (
            f"after '{after_field}'" if after_field else f"end of instrument '{field['form_name']}'"
        )
        return f"Successfully moved field '{field_name}' to {target}."

    @mcp.tool()
    def clone_instrument(source_form: str, new_form_name: str, field_prefix: str) -> str:
        """Clone all fields of an instrument into a new instrument.

        Each cloned field name is prefixed with field_prefix to avoid collisions.
        Branching logic is cleared on cloned fields because it references the
        original field names; update it manually with update_field after cloning.

        Args:
            source_form: Internal name of the instrument to clone.
            new_form_name: Internal name for the new instrument.
            field_prefix: Prefix to prepend to every cloned field name
                          (e.g. 'v2_' turns 'age' into 'v2_age').

        Returns:
            Confirmation message with the count of cloned fields.
        """
        project = get_project()
        dictionary = project.export_metadata(format_type="json")
        record_id_field = project.def_field

        source_fields = [f for f in dictionary if f["form_name"] == source_form]
        if not source_fields:
            return f"Error: instrument '{source_form}' not found."
        if any(f["form_name"] == new_form_name for f in dictionary):
            return f"Error: instrument '{new_form_name}' already exists."
        if not field_prefix:
            return "Error: field_prefix must not be empty."

        existing_names = {f["field_name"] for f in dictionary}
        new_fields = []
        conflicts = []

        for field in source_fields:
            if field["field_name"] == record_id_field:
                continue
            new_name = field_prefix + field["field_name"]
            if new_name in existing_names:
                conflicts.append(new_name)
            else:
                cloned = {
                    **field,
                    "field_name": new_name,
                    "form_name": new_form_name,
                    "branching_logic": "",
                }
                new_fields.append(cloned)

        if conflicts:
            return (
                f"Error: cloned field name(s) would conflict with existing fields: "
                f"{conflicts}. Choose a different field_prefix."
            )
        if not new_fields:
            return f"Error: no clonable fields found in instrument '{source_form}'."

        dictionary.extend(new_fields)
        count = project.import_metadata(to_import=dictionary, return_format_type="json")
        return (
            f"Successfully cloned {len(new_fields)} field(s) from '{source_form}' "
            f"into new instrument '{new_form_name}' ({count} field(s) updated). "
            f"Branching logic was cleared on cloned fields — update with update_field if needed."
        )

    @mcp.tool()
    def assign_instrument_to_event(instrument: str, event: str, arm_num: int = 1) -> str:
        """Assign an instrument to an event in a longitudinal project.

        Args:
            instrument: Internal form name of the instrument.
            event: Unique event name (e.g. 'baseline_arm_1').
            arm_num: Arm number the event belongs to (default 1).

        Returns:
            Confirmation message, or an error if the project is not longitudinal.
        """
        project = get_project()
        if not project.is_longitudinal:
            return "Error: this project is not longitudinal."

        try:
            mappings = project.export_instrument_event_mappings(format_type="json")
        except Exception as exc:
            return f"Error retrieving event mappings: {exc}"

        if any(m["form"] == instrument and m["unique_event_name"] == event for m in mappings):
            return f"Instrument '{instrument}' is already assigned to event '{event}'."

        mappings.append({"arm_num": arm_num, "unique_event_name": event, "form": instrument})
        project.import_instrument_event_mappings(to_import=mappings, return_format_type="json")
        return (
            f"Successfully assigned instrument '{instrument}' to event '{event}' (arm {arm_num})."
        )

    @mcp.tool()
    def unassign_instrument_from_event(instrument: str, event: str) -> str:
        """Remove an instrument from an event in a longitudinal project.

        Args:
            instrument: Internal form name of the instrument.
            event: Unique event name (e.g. 'baseline_arm_1').

        Returns:
            Confirmation message, or an error if the mapping did not exist.
        """
        project = get_project()
        if not project.is_longitudinal:
            return "Error: this project is not longitudinal."

        try:
            mappings = project.export_instrument_event_mappings(format_type="json")
        except Exception as exc:
            return f"Error retrieving event mappings: {exc}"

        updated = [
            m for m in mappings
            if not (m["form"] == instrument and m["unique_event_name"] == event)
        ]
        if len(updated) == len(mappings):
            return f"Error: instrument '{instrument}' is not assigned to event '{event}'."

        project.import_instrument_event_mappings(to_import=updated, return_format_type="json")
        return f"Successfully removed instrument '{instrument}' from event '{event}'."

    @mcp.tool()
    def add_field(
        form_name: str,
        field_name: str,
        field_type: str,
        field_label: str,
        choices: str | None = None,
        required: bool = False,
        branching_logic: str | None = None,
        field_note: str | None = None,
        section_header: str | None = None,
        validation: str | None = None,
        validation_min: str | None = None,
        validation_max: str | None = None,
        field_annotation: str | None = None,
        after_field: str | None = None,
    ) -> str:
        """Add a new field to an existing instrument.

        Exports the current data dictionary, inserts the new field, and imports
        the updated dictionary back. The operation is atomic from REDCap's perspective.

        Args:
            form_name: Internal name of the instrument to add the field to.
            field_name: Variable name for the new field (lowercase, underscores, no spaces).
            field_type: One of: text, notes, calc, radio, checkbox, yesno, truefalse,
                        select, slider, file, descriptive.
            field_label: Display label shown to data-entry users.
            choices: Choice definitions for radio/checkbox/select fields,
                     formatted as "1, Label 1 | 2, Label 2". Ignored for other types.
            required: Whether the field must be filled before saving the record.
            branching_logic: Show/hide logic expression (e.g. "[age] > 18").
            field_note: Helper text displayed below the field.
            section_header: Section header to display above this field.
            validation: Validation type for text fields (e.g. integer, number,
                        date_ymd, email, phone).
            validation_min: Minimum allowed value (for validated text fields).
            validation_max: Maximum allowed value (for validated text fields).
            field_annotation: REDCap action tags and annotations (e.g. @HIDDEN).
            after_field: Insert the new field immediately after this field name.
                         If None, the field is appended at the end of the instrument.

        Returns:
            Confirmation message with the count of updated fields.
        """
        project = get_project()
        dictionary = project.export_metadata(format_type="json")

        if any(f["field_name"] == field_name for f in dictionary):
            return f"Error: field '{field_name}' already exists in this project."

        new_field = {
            **_EMPTY_FIELD,
            "field_name": field_name,
            "form_name": form_name,
            "field_type": field_type,
            "field_label": field_label,
            "select_choices_or_calculations": choices or "",
            "required_field": "y" if required else "",
            "branching_logic": branching_logic or "",
            "field_note": field_note or "",
            "section_header": section_header or "",
            "text_validation_type_or_show_slider_number": validation or "",
            "text_validation_min": validation_min or "",
            "text_validation_max": validation_max or "",
            "field_annotation": field_annotation or "",
        }

        if after_field:
            idx = next(
                (i for i, f in enumerate(dictionary) if f["field_name"] == after_field), None
            )
            if idx is None:
                return f"Error: after_field '{after_field}' not found in the data dictionary."
            dictionary.insert(idx + 1, new_field)
        else:
            # Append after the last field belonging to this form.
            last_form_idx = next(
                (
                    i for i in range(len(dictionary) - 1, -1, -1)
                    if dictionary[i]["form_name"] == form_name
                ),
                None,
            )
            if last_form_idx is None:
                return f"Error: instrument '{form_name}' not found in the data dictionary."
            dictionary.insert(last_form_idx + 1, new_field)

        count = project.import_metadata(to_import=dictionary, return_format_type="json")
        return (
            f"Successfully added field '{field_name}' to instrument '{form_name}' "
            f"({count} field(s) updated)."
        )

    @mcp.tool()
    def remove_field(field_name: str) -> str:
        """Remove a field from the project data dictionary.

        Exports the current data dictionary, removes the field, and imports
        the updated dictionary back.

        Note: REDCap will reject the removal of the record-ID field and may
        reject removals that would break branching logic or calculated fields
        in other instruments.

        Args:
            field_name: Variable name of the field to remove.

        Returns:
            Confirmation message, or an error if the field was not found.
        """
        project = get_project()
        dictionary = project.export_metadata(format_type="json")

        original_len = len(dictionary)
        updated = [f for f in dictionary if f["field_name"] != field_name]
        if len(updated) == original_len:
            return f"Error: field '{field_name}' not found in the data dictionary."

        count = project.import_metadata(to_import=updated, return_format_type="json")
        return f"Successfully removed field '{field_name}' ({count} field(s) updated)."

    @mcp.tool()
    def update_field(
        field_name: str,
        field_label: str | None = None,
        field_note: str | None = None,
        required: bool | None = None,
        branching_logic: str | None = None,
        choices: str | None = None,
        validation: str | None = None,
        validation_min: str | None = None,
        validation_max: str | None = None,
        field_annotation: str | None = None,
        section_header: str | None = None,
    ) -> str:
        """Update properties of an existing field in the data dictionary.

        Only the properties you pass will be changed; all other properties
        are preserved exactly as they are. Exports the full dictionary, patches
        the target field, and imports it back.

        Args:
            field_name: Variable name of the field to update.
            field_label: New display label.
            field_note: New helper text shown below the field.
            required: Set to True to make the field required, False to make it optional.
            branching_logic: New show/hide logic expression.
            choices: New choice definitions for radio/checkbox/select fields,
                     formatted as "1, Label 1 | 2, Label 2".
            validation: New validation type for text fields.
            validation_min: New minimum allowed value.
            validation_max: New maximum allowed value.
            field_annotation: New action tags and annotations.
            section_header: New section header above this field.

        Returns:
            Confirmation message, or an error if the field was not found.
        """
        project = get_project()
        dictionary = project.export_metadata(format_type="json")

        target = next((f for f in dictionary if f["field_name"] == field_name), None)
        if target is None:
            return f"Error: field '{field_name}' not found in the data dictionary."

        if field_label is not None:
            target["field_label"] = field_label
        if field_note is not None:
            target["field_note"] = field_note
        if required is not None:
            target["required_field"] = "y" if required else ""
        if branching_logic is not None:
            target["branching_logic"] = branching_logic
        if choices is not None:
            target["select_choices_or_calculations"] = choices
        if validation is not None:
            target["text_validation_type_or_show_slider_number"] = validation
        if validation_min is not None:
            target["text_validation_min"] = validation_min
        if validation_max is not None:
            target["text_validation_max"] = validation_max
        if field_annotation is not None:
            target["field_annotation"] = field_annotation
        if section_header is not None:
            target["section_header"] = section_header

        count = project.import_metadata(to_import=dictionary, return_format_type="json")
        return f"Successfully updated field '{field_name}' ({count} field(s) updated)."
