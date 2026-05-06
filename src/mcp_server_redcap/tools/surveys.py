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

        The instrument must be enabled as a survey in REDCap. Returns an error
        if surveys are not enabled or the instrument is not a survey.

        Args:
            record: Record ID of the participant.
            instrument: Internal name of the survey instrument.
            event: Event name (longitudinal projects only).
            repeat_instance: Repeat instance number (default 1).

        Returns:
            The survey URL as a plain string.
        """
        project = get_project()
        try:
            return project.export_survey_link(
                record=record,
                instrument=instrument,
                event=event,
                repeat_instance=repeat_instance,
            )
        except Exception as exc:
            return f"Error retrieving survey link: {exc}"

    @mcp.tool()
    def export_survey_participant_list(
        instrument: str,
        event: str | None = None,
    ) -> str:
        """Export the list of survey participants for an instrument.

        The instrument must be enabled as a survey in REDCap. Returns an error
        if surveys are not enabled or the instrument is not a survey.

        Args:
            instrument: Internal name of the survey instrument.
            event: Event name (longitudinal projects only).

        Returns:
            JSON array of participant records with email, name, and response status.
        """
        project = get_project()
        try:
            result = project.export_survey_participant_list(
                instrument=instrument,
                format_type="json",
                event=event,
            )
            return json.dumps(result, indent=2, default=str)
        except Exception as exc:
            return f"Error retrieving participant list: {exc}"
