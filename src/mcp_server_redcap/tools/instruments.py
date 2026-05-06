import json

from mcp.server.fastmcp import FastMCP

from ..connection import get_project


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
