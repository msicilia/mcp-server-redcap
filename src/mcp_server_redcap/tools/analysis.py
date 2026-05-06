import json
import re
from collections import Counter, defaultdict

from mcp.server.fastmcp import FastMCP

from ..connection import get_project

# Matches [field_name] and [field_name(checkbox_code)] in REDCap logic expressions.
_BRACKET_RE = re.compile(r"\[([^\]]+)\]")


def _field_refs(expression: str) -> set[str]:
    """Return the set of base field names referenced in a REDCap logic expression."""
    refs = set()
    for m in _BRACKET_RE.finditer(expression):
        token = m.group(1)
        refs.add(token.split("(")[0].strip())
    return refs


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def get_project_structure() -> str:
        """Return a compact structural overview of the REDCap project.

        Useful as a first call when starting work on an existing project.
        Returns instruments with field counts and type breakdowns. For
        longitudinal projects, includes the full event/instrument matrix.

        Returns:
            JSON object describing the project structure.
        """
        project = get_project()
        info = project.export_project_info(format_type="json")
        metadata = project.export_metadata(format_type="json")
        instruments_list = project.export_instruments(format_type="json")

        fields_by_form: dict[str, list] = defaultdict(list)
        for field in metadata:
            fields_by_form[field["form_name"]].append(field)

        instruments_summary = [
            {
                "form_name": instr["instrument_name"],
                "instrument_label": instr["instrument_label"],
                "field_count": len(fields_by_form.get(instr["instrument_name"], [])),
                "field_types": dict(
                    Counter(
                        f["field_type"]
                        for f in fields_by_form.get(instr["instrument_name"], [])
                    )
                ),
            }
            for instr in instruments_list
        ]

        structure: dict = {
            "project_title": info.get("project_title"),
            "redcap_version": str(project.redcap_version),
            "is_longitudinal": bool(info.get("is_longitudinal")),
            "surveys_enabled": bool(info.get("surveys_enabled")),
            "record_autonumbering_enabled": bool(info.get("record_autonumbering_enabled")),
            "total_fields": len(metadata),
            "instruments": instruments_summary,
        }

        if project.is_longitudinal:
            try:
                events = project.export_events(format_type="json")
                mappings = project.export_instrument_event_mappings(format_type="json")

                event_instruments: dict[str, list] = defaultdict(list)
                for m in mappings:
                    event_instruments[m["unique_event_name"]].append(m["form"])

                structure["events"] = [
                    {
                        "unique_event_name": e["unique_event_name"],
                        "event_label": e.get("event_name", ""),
                        "arm_num": e.get("arm_num"),
                        "day_offset": e.get("day_offset"),
                        "instruments": event_instruments.get(e["unique_event_name"], []),
                    }
                    for e in events
                ]
            except Exception as exc:
                structure["events_error"] = str(exc)

        return json.dumps(structure, indent=2, default=str)

    @mcp.tool()
    def check_field_references(field_name: str) -> str:
        """Find every field that references a given field in branching logic or calculations.

        Run this before removing or renaming a field to avoid breaking the project.
        Returns all fields whose branching_logic or calculated formula reference
        field_name.

        Args:
            field_name: Variable name to search for.

        Returns:
            JSON object with a list of referencing fields, or a confirmation that
            no references exist.
        """
        project = get_project()
        metadata = project.export_metadata(format_type="json")

        # Match [field_name] and [field_name(N)] exactly, not substrings.
        exact_re = re.compile(r"\[" + re.escape(field_name) + r"(?:\([^\)]*\))?\]")

        references = []
        for field in metadata:
            if field["field_name"] == field_name:
                continue

            branching = field.get("branching_logic", "")
            if branching and exact_re.search(branching):
                references.append({
                    "referencing_field": field["field_name"],
                    "instrument": field["form_name"],
                    "reference_type": "branching_logic",
                    "expression": branching,
                })

            if field.get("field_type") == "calc":
                calc = field.get("select_choices_or_calculations", "")
                if calc and exact_re.search(calc):
                    references.append({
                        "referencing_field": field["field_name"],
                        "instrument": field["form_name"],
                        "reference_type": "calculation",
                        "expression": calc,
                    })

        if not references:
            return (
                f"No references to '{field_name}' found in branching logic or calculations. "
                f"Safe to remove or rename."
            )

        return json.dumps(
            {
                "field_name": field_name,
                "reference_count": len(references),
                "references": references,
            },
            indent=2,
        )

    @mcp.tool()
    def validate_branching_logic() -> str:
        """Scan all branching logic expressions for references to non-existent fields.

        Checks every field's branching_logic for [field_name] tokens that do not
        match any field in the data dictionary. For longitudinal projects, event
        names in [event_name][field_name] syntax are excluded from the check.

        Returns:
            A confirmation message if all references are valid, or a JSON object
            listing every broken reference with its location.
        """
        project = get_project()
        metadata = project.export_metadata(format_type="json")
        field_names = {f["field_name"] for f in metadata}

        event_names: set[str] = set()
        if project.is_longitudinal:
            try:
                events = project.export_events(format_type="json")
                event_names = {e["unique_event_name"] for e in events}
            except Exception:
                pass

        known = field_names | event_names
        issues = []

        for field in metadata:
            logic = field.get("branching_logic", "")
            if not logic:
                continue
            for ref in _field_refs(logic):
                if ref not in known:
                    issues.append({
                        "field": field["field_name"],
                        "instrument": field["form_name"],
                        "unresolved_reference": ref,
                        "branching_logic": logic,
                    })

        if not issues:
            return "All branching logic references are valid."

        return json.dumps({"issue_count": len(issues), "issues": issues}, indent=2)
