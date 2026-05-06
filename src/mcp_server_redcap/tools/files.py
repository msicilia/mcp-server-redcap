import base64
import io
import json

from mcp.server.fastmcp import FastMCP

from ..connection import get_project


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def export_file(
        record: str,
        field: str,
        event: str | None = None,
        repeat_instance: int | None = None,
    ) -> str:
        """Export a file attachment from a REDCap record field.

        Args:
            record: Record ID containing the file.
            field: Name of the file upload field.
            event: Event name (longitudinal projects only).
            repeat_instance: Repeat instance number for repeating instruments/events.

        Returns:
            JSON object with base64-encoded file content, filename, and content type.
        """
        project = get_project()
        content, headers = project.export_file(
            record=record,
            field=field,
            event=event,
            repeat_instance=repeat_instance,
        )
        return json.dumps(
            {
                "content_base64": base64.b64encode(content).decode("utf-8"),
                "content_type": headers.get("content-type", ""),
                "filename": headers.get("content-name", ""),
            }
        )

    @mcp.tool()
    def import_file(
        record: str,
        field: str,
        file_name: str,
        content_base64: str,
        event: str | None = None,
        repeat_instance: int | None = None,
    ) -> str:
        """Import (upload) a file into a REDCap record field.

        Args:
            record: Record ID to attach the file to.
            field: Name of the file upload field.
            file_name: Name to give the file in REDCap.
            content_base64: Base64-encoded file content.
            event: Event name (longitudinal projects only).
            repeat_instance: Repeat instance number for repeating instruments/events.

        Returns:
            Confirmation message.
        """
        project = get_project()
        file_bytes = base64.b64decode(content_base64)
        project.import_file(
            record=record,
            field=field,
            file_name=file_name,
            file_object=io.BytesIO(file_bytes),
            event=event,
            repeat_instance=repeat_instance,
        )
        return f"Successfully uploaded '{file_name}' to record {record}, field {field}."

    @mcp.tool()
    def delete_file(
        record: str,
        field: str,
        event: str | None = None,
    ) -> str:
        """Delete a file attachment from a REDCap record field.

        Args:
            record: Record ID containing the file.
            field: Name of the file upload field.
            event: Event name (longitudinal projects only).

        Returns:
            Confirmation message.
        """
        project = get_project()
        project.delete_file(record=record, field=field, event=event)
        return f"Successfully deleted file from record {record}, field {field}."

    @mcp.tool()
    def export_pdf(
        record: str | None = None,
        event: str | None = None,
        instrument: str | None = None,
        repeat_instance: int | None = None,
        compact_display: bool | None = None,
    ) -> str:
        """Export a PDF of one or all instruments for a record.

        Args:
            record: Record ID to export. None exports all records (use with caution).
            event: Event name (longitudinal projects only).
            instrument: Specific instrument to export. None exports all instruments.
            repeat_instance: Repeat instance number for repeating instruments/events.
            compact_display: If True, uses compact PDF layout.

        Returns:
            JSON object with base64-encoded PDF content.
        """
        project = get_project()
        try:
            content, _ = project.export_pdf(
                record=record,
                event=event,
                instrument=instrument,
                repeat_instance=repeat_instance,
                compact_display=compact_display,
            )
            return json.dumps({"content_base64": base64.b64encode(content).decode("utf-8")})
        except Exception as exc:
            return f"Error exporting PDF: {exc}"
