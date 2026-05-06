import json

from mcp.server.fastmcp import FastMCP

from ..connection import get_project

_NOT_LONGITUDINAL = "Error: this project is not longitudinal."


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def export_arms(arms: list[str] | None = None) -> str:
        """Export arms for a longitudinal REDCap project.

        Args:
            arms: Specific arm numbers to export. None exports all arms.

        Returns:
            JSON array of arms with arm_num and name fields.
        """
        project = get_project()
        if not project.is_longitudinal:
            return _NOT_LONGITUDINAL
        try:
            result = project.export_arms(format_type="json", arms=arms)
            return json.dumps(result, indent=2, default=str)
        except Exception as exc:
            return f"Error exporting arms: {exc}"

    @mcp.tool()
    def import_arms(data: str, override: bool = False) -> str:
        """Import (create or update) arms in a longitudinal REDCap project.

        Args:
            data: JSON array of arm objects, each with arm_num and name fields.
            override: If True, existing arms not in the import will be deleted.

        Returns:
            Confirmation message with the count of imported arms.
        """
        project = get_project()
        if not project.is_longitudinal:
            return _NOT_LONGITUDINAL
        try:
            arms_data = json.loads(data)
            count = project.import_arms(
                to_import=arms_data,
                return_format_type="json",
                override=int(override),
            )
            return f"Successfully imported {count} arm(s)."
        except Exception as exc:
            return f"Error importing arms: {exc}"

    @mcp.tool()
    def delete_arms(arms: list[str]) -> str:
        """Delete arms from a longitudinal REDCap project.

        Args:
            arms: List of arm numbers to delete.

        Returns:
            Confirmation message with the count of deleted arms.
        """
        project = get_project()
        if not project.is_longitudinal:
            return _NOT_LONGITUDINAL
        try:
            count = project.delete_arms(arms=arms, return_format_type="json")
            return f"Successfully deleted {count} arm(s)."
        except Exception as exc:
            return f"Error deleting arms: {exc}"

    @mcp.tool()
    def export_events(arms: list[str] | None = None) -> str:
        """Export events for a longitudinal REDCap project.

        Args:
            arms: Filter to specific arm numbers. None exports events for all arms.

        Returns:
            JSON array of events with event_name, arm_num, day_offset, and other fields.
        """
        project = get_project()
        if not project.is_longitudinal:
            return _NOT_LONGITUDINAL
        try:
            result = project.export_events(format_type="json", arms=arms)
            return json.dumps(result, indent=2, default=str)
        except Exception as exc:
            return f"Error exporting events: {exc}"

    @mcp.tool()
    def import_events(data: str, override: bool = False) -> str:
        """Import (create or update) events in a longitudinal REDCap project.

        Args:
            data: JSON array of event objects with event_name, arm_num, day_offset, etc.
            override: If True, existing events not in the import will be deleted.

        Returns:
            Confirmation message with the count of imported events.
        """
        project = get_project()
        if not project.is_longitudinal:
            return _NOT_LONGITUDINAL
        try:
            events_data = json.loads(data)
            count = project.import_events(
                to_import=events_data,
                return_format_type="json",
                override=int(override),
            )
            return f"Successfully imported {count} event(s)."
        except Exception as exc:
            return f"Error importing events: {exc}"

    @mcp.tool()
    def delete_events(events: list[str]) -> str:
        """Delete events from a longitudinal REDCap project.

        Args:
            events: List of unique event names to delete.

        Returns:
            Confirmation message with the count of deleted events.
        """
        project = get_project()
        if not project.is_longitudinal:
            return _NOT_LONGITUDINAL
        try:
            count = project.delete_events(events=events, return_format_type="json")
            return f"Successfully deleted {count} event(s)."
        except Exception as exc:
            return f"Error deleting events: {exc}"
