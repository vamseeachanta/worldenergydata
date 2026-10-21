"""Text expectations follow issue 1297 (2026), independent of FFS calculations.

By inspection, an empty CSV field supplies no identifier or location. With no
populated fallback the expected value is None; otherwise the first populated
fallback is expected verbatim. The narrative shall describe an absent ID as
missing. All examples are synthetic text cases, not engineering benchmarks.
"""

from io import StringIO

import pandas as pd
import pytest

from worldenergydata.pipeline_safety.workflow import PipelineSafetyWorkflow

MISSING_TEXT = [
    pytest.param(None, id="none"),
    pytest.param(float("nan"), id="nan"),
    pytest.param(pd.NA, id="nullable"),
    pytest.param(pd.NaT, id="nat"),
    pytest.param("", id="empty"),
    pytest.param(" \t ", id="whitespace"),
]


@pytest.mark.parametrize("missing", MISSING_TEXT)
def test_missing_text_remains_missing(missing):
    """No primary or fallback value means both text fields are None."""
    workflow = PipelineSafetyWorkflow()
    defect = workflow.characterize({"incident_id": missing, "location": missing})

    assert defect.incident_id is None
    assert defect.location is None
    assert workflow.assess_ffs(defect).incident_id is None


@pytest.mark.parametrize("missing", MISSING_TEXT)
def test_missing_primary_text_uses_populated_fallback(missing):
    """Report number and state are the first populated alternatives."""
    defect = PipelineSafetyWorkflow().characterize(
        {
            "incident_id": missing,
            "report_number": "record-A",
            "location": missing,
            "state": "region-A",
            "city": "city-A",
        }
    )

    assert defect.incident_id == "record-A"
    assert defect.location == "region-A"


@pytest.mark.parametrize("missing", MISSING_TEXT)
def test_missing_secondary_text_uses_city_or_remains_missing(missing):
    """An absent report number stays missing; an absent state falls to city."""
    defect = PipelineSafetyWorkflow().characterize(
        {
            "incident_id": missing,
            "report_number": missing,
            "location": missing,
            "state": missing,
            "city": "city-A",
        }
    )

    assert defect.incident_id is None
    assert defect.location == "city-A"


@pytest.mark.parametrize("missing", MISSING_TEXT)
def test_all_text_candidates_missing(missing):
    """Missing fallback cells cannot become literal sentinel strings."""
    defect = PipelineSafetyWorkflow().characterize(
        dict.fromkeys(
            ("incident_id", "report_number", "location", "state", "city"), missing
        )
    )

    assert defect.incident_id is None
    assert defect.location is None


@pytest.mark.parametrize("value", ["record-A", " record-A ", 0])
def test_populated_primary_text_is_preserved(value):
    """A supplied scalar, including synthetic numeric ID zero, is present."""
    defect = PipelineSafetyWorkflow().characterize(
        {
            "incident_id": value,
            "report_number": "fallback",
            "location": value,
            "state": "fallback",
        }
    )

    assert defect.incident_id == str(value)
    assert defect.location == str(value)


def test_blank_csv_text_through_report_and_narrative():
    """Empty CSV cells -> absent text -> None in report -> 'missing' in prose."""
    incidents = pd.read_csv(
        StringIO("incident_id,report_number,location,state,city\n,,,,\n")
    )
    workflow = PipelineSafetyWorkflow()
    defect = workflow.characterize(incidents.iloc[0].to_dict())
    report = workflow.generate_report(incidents)

    assert defect.incident_id is None
    assert defect.location is None
    assert report.iloc[0]["incident_id"] is None
    assert "Incident ID      : missing" in workflow.case_study_narrative(report)


@pytest.mark.parametrize("missing", MISSING_TEXT)
def test_narrative_marks_missing_id_in_supplied_report(missing):
    """Missing IDs in an existing report also require an explicit missing label."""
    workflow = PipelineSafetyWorkflow()
    report = workflow.generate_report(pd.DataFrame([{"incident_id": "record-A"}]))
    report["incident_id"] = missing

    assert "Incident ID      : missing" in workflow.case_study_narrative(report)


def test_populated_csv_fallbacks_and_primary_precedence():
    """Empty primaries select fallbacks; populated primaries precede fallbacks."""
    incidents = pd.read_csv(
        StringIO(
            "incident_id,report_number,location,state,city\n"
            ",record-A,,region-A,city-A\n"
            "record-B,unused,segment-B,unused,unused\n"
        )
    )
    workflow = PipelineSafetyWorkflow()
    defects = [workflow.characterize(row) for row in incidents.to_dict("records")]

    assert [(defect.incident_id, defect.location) for defect in defects] == [
        ("record-A", "region-A"),
        ("record-B", "segment-B"),
    ]
