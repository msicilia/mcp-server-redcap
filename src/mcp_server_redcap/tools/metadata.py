import json
from datetime import datetime

from mcp.server.fastmcp import FastMCP

from ..connection import get_project


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def get_project_info() -> str:
        """Get information about the REDCap project.

        Returns project title, PI name, creation time, record count, and other
        project-level settings.

        Returns:
            JSON object with project metadata.
        """
        project = get_project()
        info = project.export_project_info(format_type="json")
        return json.dumps(info, indent=2, default=str)

    @mcp.tool()
    def get_metadata(
        fields: list[str] | None = None,
        forms: list[str] | None = None,
    ) -> str:
        """Get the data dictionary (metadata) for the REDCap project.

        Returns field definitions including type, label, choices, validation,
        branching logic, and required status.

        Args:
            fields: Filter to specific field names. None returns all fields.
            forms: Filter to specific instrument/form names. None returns all forms.

        Returns:
            JSON array of field definitions.
        """
        project = get_project()
        result = project.export_metadata(
            format_type="json",
            fields=fields,
            forms=forms,
        )
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def export_logging(
        log_type: str | None = None,
        user: str | None = None,
        record: str | None = None,
        begin_time: str | None = None,
        end_time: str | None = None,
    ) -> str:
        """Export the audit log for the REDCap project.

        Args:
            log_type: Filter by event type. One of: 'export', 'manage', 'user',
                      'record', 'record_add', 'record_edit', 'record_delete',
                      'lock_record', 'page_view'. None returns all types.
            user: Filter to a specific REDCap username.
            record: Filter to a specific record ID.
            begin_time: Start of date range as ISO 8601 string (e.g. '2024-01-01T00:00:00').
            end_time: End of date range as ISO 8601 string.

        Returns:
            JSON array of log entries.
        """
        project = get_project()
        try:
            result = project.export_logging(
                format_type="json",
                log_type=log_type,
                user=user,
                record=record,
                begin_time=datetime.fromisoformat(begin_time) if begin_time else None,
                end_time=datetime.fromisoformat(end_time) if end_time else None,
            )
            return json.dumps(result, indent=2, default=str)
        except Exception as exc:
            return f"Error exporting log: {exc}"

    @mcp.tool()
    def export_repeating_instruments_events() -> str:
        """Export the repeating instruments and events configuration.

        Requires REDCap 6.16 or later. Returns an error message on older instances.

        Returns:
            JSON array of repeating instrument/event definitions, or an empty array
            if the project has no repeating instruments or events.
        """
        project = get_project()
        try:
            result = project.export_repeating_instruments_events(format_type="json")
            return json.dumps(result, indent=2, default=str)
        except Exception as exc:
            return f"Error: could not retrieve repeating instruments/events: {exc}"

    @mcp.tool()
    def import_repeating_instruments_events(data: str) -> str:
        """Import (create or update) repeating instruments and events configuration.

        Requires REDCap 6.16 or later. Returns an error message on older instances.

        Args:
            data: JSON array of repeating instrument/event objects. Each object
                  should have event_name, form_name, and custom_form_label fields.

        Returns:
            Confirmation message with the count of imported definitions.
        """
        project = get_project()
        try:
            records_data = json.loads(data)
            count = project.import_repeating_instruments_events(
                to_import=records_data,
                return_format_type="json",
            )
            return f"Successfully imported {count} repeating instrument/event definition(s)."
        except Exception as exc:
            return f"Error: could not import repeating instruments/events: {exc}"
