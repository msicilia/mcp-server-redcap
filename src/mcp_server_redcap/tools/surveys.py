import json

from mcp.server.fastmcp import FastMCP

from ..connection import get_project


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def export_survey_link(
        record: str,
        instrument: str,
        event: str | None = None,
        repeat_instance: int = 1,
    ) -> str:
        """Get a unique survey link for a participant to complete an instrument.

        Args:
            record: Record ID of the participant.
            instrument: Internal name of the survey instrument.
            event: Event name (longitudinal projects only).
            repeat_instance: Repeat instance number (default 1).

        Returns:
            The survey URL as a plain string.
        """
        project = get_project()
        return project.export_survey_link(
            record=record,
            instrument=instrument,
            event=event,
            repeat_instance=repeat_instance,
        )

    @mcp.tool()
    def export_survey_participant_list(
        instrument: str,
        event: str | None = None,
    ) -> str:
        """Export the list of survey participants for an instrument.

        Args:
            instrument: Internal name of the survey instrument.
            event: Event name (longitudinal projects only).

        Returns:
            JSON array of participant records with email, name, and response status.
        """
        project = get_project()
        result = project.export_survey_participant_list(
            instrument=instrument,
            format_type="json",
            event=event,
        )
        return json.dumps(result, indent=2, default=str)
