"""Blank CSV text remains absent (#1297), using pandas 2.3 scalar missingness.

https://pandas.pydata.org/pandas-docs/version/2.3/reference/api/pandas.isna.html
"""

from io import StringIO

import pandas as pd
import pytest

from worldenergydata.pipeline_safety.workflow import PipelineSafetyWorkflow


@pytest.mark.parametrize("identifier", ["", "synthetic-id"])
@pytest.mark.parametrize("location", ["", "synthetic-location"])
def test_csv_missing_text_and_narrative(identifier, location):
    """The expected text is the supplied literal or None for an empty cell.

    The synthetic row checks text propagation only; no engineering result is
    asserted or qualified. Existing workflow defaults are outside this change.
    """
    frame = pd.read_csv(
        StringIO(f"incident_id,location\n{identifier},{location}\n"),
        skip_blank_lines=False,
    )
    workflow = PipelineSafetyWorkflow()
    defect = workflow.characterize(frame.iloc[0].to_dict())
    assert defect.incident_id == (identifier or None)
    assert defect.location == (location or None)
    report = workflow.generate_report(frame)
    assert report.iloc[0]["incident_id"] == (identifier or None)
    assert report.iloc[0]["location"] == (location or None)
    narrative = workflow.case_study_narrative(report)
    assert f"Incident ID      : {identifier or 'missing'}" in narrative
    assert f"Location         : {location or 'missing'}" in narrative
    assert "nan" not in narrative.lower()


@pytest.mark.parametrize("missing", [None, float("nan"), pd.NA, pd.NaT, "", "  "])
def test_text_fallbacks_skip_scalar_nulls(missing):
    """First available alias wins; scalar nulls must not mask later aliases."""
    defect = PipelineSafetyWorkflow().characterize(
        {
            "incident_id": missing,
            "report_number": "synthetic-report",
            "location": missing,
            "state": missing,
            "city": "synthetic-city",
        }
    )
    assert defect.incident_id == "synthetic-report"
    assert defect.location == "synthetic-city"


def test_literal_nan_text_is_not_a_missing_scalar():
    """Already typed dictionary strings are literal, including the text nan."""
    defect = PipelineSafetyWorkflow().characterize(
        {"incident_id": "nan", "location": "NA"}
    )
    assert defect.incident_id == "nan"
    assert defect.location == "NA"


def test_narrative_handles_existing_report_without_location():
    """Older report frames omit location; absence should be explicit."""
    workflow = PipelineSafetyWorkflow()
    report = workflow.generate_report(pd.DataFrame([{"incident_id": "synthetic-id"}]))
    narrative = workflow.case_study_narrative(report.drop(columns="location"))
    assert "Location         : missing" in narrative
