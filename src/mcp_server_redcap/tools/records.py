import json

from mcp.server.fastmcp import FastMCP

from ..connection import get_project


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def export_records(
        fields: list[str] | None = None,
        records: list[str] | None = None,
        events: list[str] | None = None,
        raw_or_label: str = "raw",
        export_checkbox_label: bool = False,
        limit: int = 1000,
    ) -> str:
        """Export records from the REDCap project.

        Args:
            fields: Specific field names to export. None exports all fields.
            records: Specific record IDs to export. None exports all records.
            events: Specific event names to export (longitudinal projects only).
            raw_or_label: 'raw' for coded values, 'label' for choice labels.
            export_checkbox_label: Export checkbox field labels instead of 0/1.
            limit: Maximum number of records to return (default 1000).

        Returns:
            JSON array of records.
        """
        project = get_project()
        result = project.export_records(
            format_type="json",
            fields=fields,
            records=records,
            events=events,
            raw_or_label=raw_or_label,
            export_checkbox_label=export_checkbox_label,
        )
        if isinstance(result, list) and len(result) > limit:
            result = result[:limit]
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def import_records(data: str) -> str:
        """Import records into the REDCap project.

        Args:
            data: JSON array string of records to import. Each record must include
                  the project's record ID field.

        Returns:
            Confirmation message with the count of imported records.
        """
        project = get_project()
        records_data = json.loads(data)
        count = project.import_records(records_data, return_format_type="json")
        return f"Successfully imported {count} record(s)."

    @mcp.tool()
    def delete_records(record_ids: list[str]) -> str:
        """Delete records from the REDCap project by record ID.

        Args:
            record_ids: List of record IDs to delete.

        Returns:
            Confirmation message with the count of deleted records.
        """
        project = get_project()
        count = project.delete_records(record_ids)
        return f"Successfully deleted {count} record(s)."

    @mcp.tool()
    def export_report(report_id: str) -> str:
        """Export a saved REDCap report by its ID.

        Args:
            report_id: The numeric ID of the report (visible in the REDCap URL
                       when viewing the report).

        Returns:
            JSON array of report rows.
        """
        project = get_project()
        result = project.export_report(report_id=report_id, format_type="json")
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def export_field_names(field: str | None = None) -> str:
        """Export the list of export field names for the project.

        Checkbox fields have different export names (e.g. 'chk___1', 'chk___2')
        than their original field name. Use this to resolve the correct names
        before exporting or referencing checkbox data.

        Args:
            field: Filter to a specific field name. None returns all fields.

        Returns:
            JSON array of objects with original_field_name and export_field_name.
        """
        project = get_project()
        result = project.export_field_names(format_type="json", field=field)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def generate_next_record_name() -> str:
        """Generate the next available record name for the project.

        Use this before importing a new record to obtain a valid, unused record ID
        that respects the project's auto-numbering scheme.

        Returns:
            The next record name as a string.
        """
        project = get_project()
        return project.generate_next_record_name()
