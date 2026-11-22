"""Missing CSV identifiers and locations must remain missing (issue 1297)."""

from io import StringIO
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.pipeline_safety.pipeline_safety import PipelineSafety
from worldenergydata.pipeline_safety.workflow import PipelineSafetyWorkflow


@pytest.fixture
def incident():
    """Use valid geometry from the offline example to isolate text handling."""
    root = Path(__file__).resolve().parents[3]
    return (
        pd.read_csv(root / "examples/workflows/pipeline-safety-ffs/defects.csv")
        .iloc[0]
        .to_dict()
    )


@pytest.mark.parametrize("method", ["modified_b31g", "b31g"])
def test_blank_csv_text_stays_missing_through_report(incident, method):
    incident.update(incident_id="", location="")
    frame = pd.read_csv(StringIO(pd.DataFrame([incident]).to_csv(index=False)))
    workflow = PipelineSafetyWorkflow()

    defect = workflow.characterize(frame.iloc[0].to_dict())
    assert defect.incident_id is None
    assert defect.location is None
    assert workflow.assess_ffs(defect, method=method).incident_id is None

    report = workflow.generate_report(frame, method=method)
    assert report["incident_id"].isna().all()
    narrative = workflow.case_study_narrative(report)
    assert "Incident ID      : missing" in narrative
    assert "Incident ID      : nan" not in narrative


@pytest.mark.parametrize("value", [None, float("nan"), pd.NA, pd.NaT, "", " \t"])
def test_missing_text_scalars_are_not_identifiers(incident, value):
    incident.update(incident_id=value, location=value)
    defect = PipelineSafetyWorkflow().characterize(incident)
    assert defect.incident_id is None
    assert defect.location is None


def test_omitted_text_stays_missing(incident):
    incident.pop("incident_id")
    incident.pop("location")
    defect = PipelineSafetyWorkflow().characterize(incident)
    assert defect.incident_id is None
    assert defect.location is None


@pytest.mark.parametrize("value", [None, float("nan"), pd.NA, "", " \t"])
@pytest.mark.parametrize("location_field", ["state", "city"])
def test_missing_text_uses_available_fallback(incident, value, location_field):
    incident.update(
        incident_id=value, report_number="REPORT-001", location=value, state=value
    )
    incident[location_field] = "fallback location"
    defect = PipelineSafetyWorkflow().characterize(incident)
    assert defect.incident_id == "REPORT-001"
    assert defect.location == "fallback location"


def test_populated_text_takes_precedence_over_fallbacks(incident):
    incident.update(
        incident_id="TEXT-001",
        report_number="REPORT-001",
        location="segment A",
        state="state fallback",
        city="city fallback",
    )
    workflow = PipelineSafetyWorkflow()
    defect = workflow.characterize(incident)
    assert defect.incident_id == "TEXT-001"
    assert defect.location == "segment A"
    report = workflow.generate_report(pd.DataFrame([incident]))
    assert "Incident ID      : TEXT-001" in workflow.case_study_narrative(report)


def test_blank_fallback_columns_stay_missing(incident):
    incident.update(
        incident_id=pd.NA,
        report_number=float("nan"),
        location="",
        state=pd.NaT,
        city=" ",
    )
    defect = PipelineSafetyWorkflow().characterize(incident)
    assert defect.incident_id is None
    assert defect.location is None


@pytest.mark.parametrize("value", [None, float("nan"), pd.NA, "", " \t"])
def test_narrative_discloses_missing_id_in_supplied_report(incident, value):
    workflow = PipelineSafetyWorkflow()
    report = workflow.generate_report(pd.DataFrame([incident]))
    report["incident_id"] = value
    assert "Incident ID      : missing" in workflow.case_study_narrative(report)


def test_csv_router_writes_missing_id_and_explicit_narrative(incident, tmp_path):
    incident.update(incident_id="", location="")
    pd.DataFrame([incident]).to_csv(tmp_path / "defects.csv", index=False)
    cfg = {
        "data": {"source": "csv", "file": "defects.csv"},
        "Analysis": {
            "analysis_root_folder": str(tmp_path),
            "result_folder": str(tmp_path / "results"),
        },
    }
    outputs = PipelineSafety().router(cfg)["pipeline_safety"]["outputs"]
    report = pd.read_csv(outputs["report_csv"], keep_default_na=False)
    assert report["incident_id"].tolist() == [""]
    narrative = Path(outputs["narrative_txt"]).read_text()
    assert "Incident ID      : missing" in narrative
    assert "Incident ID      : nan" not in narrative
