"""Issue 1295: schema/parse diagnostics and unknown values survive ingestion.

Synthetic rows exercise the import loop; no historical workbook is qualified.
Expected missing states follow issue 1295, not a numerical engineering model.
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from worldenergydata.pipeline_safety.database.models import Base, PipelineIncident
from worldenergydata.pipeline_safety.importers import phmsa_importer as imp
from worldenergydata.pipeline_safety.pipeline_safety import PipelineSafety


@pytest.mark.parametrize(
    "converter, value",
    [
        (imp._safe_int, "bad"),
        (imp._safe_int, 2.9),
        (imp._safe_float, "$500"),
        (imp._safe_float, "1,234"),
        (imp._safe_float, "nan"),
        (imp._safe_float, float("inf")),
        (imp._parse_bool_indicator, "maybe"),
        (imp._parse_datetime, "bad"),
    ],
)
def test_malformed_is_not_missing(converter, value):
    with pytest.raises(ValueError):
        converter(value)


def test_missing_source_column_is_reported():
    with pytest.warns(imp.MissingSourceColumnWarning, match="ABSENT"):
        assert pd.isna(imp._get_col(pd.Series({"PRESENT": 0}), "ABSENT"))


@pytest.mark.parametrize("era", ["pre2004", "2004_2009", "2010_present"])
def test_unknown_consequences_and_units_in_normalized_output(era, tmp_path):
    importer = imp.PHMSAImporter(MagicMock(), str(tmp_path))
    record = importer._normalize_row(pd.Series(dtype=object), "gas_transmission", era)
    assert record["fatalities"] is None
    assert record["injuries"] is None
    assert record["missing_source_columns"]
    assert record["unit_assumptions"]["pipeline_diameter"].startswith("unknown")


def test_partial_consequence_sum_is_unknown():
    """One reported person plus one unknown count is an unknown total."""
    with pytest.warns(imp.MissingSourceColumnWarning, match="B"):
        assert imp._sum_columns(pd.Series({"A": 1}), ["A", "B"]) is None
    assert imp._sum_columns(pd.Series({"A": 0, "B": 0}), ["A", "B"]) == 0
    assert imp._sum_columns(pd.Series({"A": 1, "B": 2}), ["A", "B"]) == 3


def test_persistence_preserves_unknown_counts():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        importer = imp.PHMSAImporter(db_session, ".")
        importer._persist(
            {
                "report_number": "SYNTHETIC",
                "report_type": "gas_transmission",
                "operator_name": "synthetic",
                "incident_date": datetime(2020, 1, 1),
            }
        )
        db_session.commit()
        row = db_session.query(PipelineIncident).one()
        assert row.fatalities is None
        assert row.injuries is None
        assert importer._is_duplicate("SYNTHETIC")


def test_import_loop_counts_parse_error_and_reports_schema(monkeypatch, tmp_path):
    filename = "synthetic.xlsx"
    (tmp_path / filename).touch()
    monkeypatch.setattr(
        imp, "FILE_MANIFEST", [(filename, "sheet", "gas_transmission", "2010_present")]
    )
    valid = {
        "REPORT_NUMBER": "valid",
        "NAME": "synthetic",
        "LOCAL_DATETIME": "2020-01-01",
    }
    frame = pd.DataFrame(
        [dict(valid, IGNITE_IND="maybe"), dict(valid, IGNITE_IND="YES")]
    )
    monkeypatch.setattr(pd, "read_excel", lambda *args, **kwargs: frame)
    db_session = MagicMock()
    db_session.query.return_value.filter.return_value.first.return_value = None
    stats = imp.PHMSAImporter(db_session, str(tmp_path)).import_data()
    assert stats["total_records"] == 2
    assert stats["error_count"] == 1
    assert stats["imported_count"] == 1
    assert "PIPE_DIAMETER" in stats["missing_source_columns"]
    assert "boolean field" in stats["validation_errors"][0]
    assert "maybe" not in stats["validation_errors"][0]
    assert "unverified" in stats["unit_assumptions"]["latitude_longitude"]
    db_session.commit.assert_called_once()


@pytest.mark.parametrize("content", ["", "depth_pct_wall,length_mm\n"])
def test_empty_csv_leaves_no_output_bundle(tmp_path, content):
    (tmp_path / "empty.csv").write_text(content)
    result_dir = tmp_path / "results"
    cfg = {
        "data": {"source": "csv", "file": "empty.csv"},
        "Analysis": {
            "analysis_root_folder": str(tmp_path),
            "result_folder": str(result_dir),
        },
    }
    with pytest.raises(ValueError):
        PipelineSafety().router(cfg)
    assert not result_dir.exists()


@pytest.mark.parametrize("pipeline_type", ["hazardous_liquid", "lng"])
def test_partial_release_is_unknown(tmp_path, pipeline_type):
    importer = imp.PHMSAImporter(MagicMock(), str(tmp_path))
    row = pd.Series({"UNINTENTIONAL_RELEASE_BBLS": 1, "UNINTENTIONAL_RELEASE": 1})
    with pytest.warns(imp.MissingSourceColumnWarning):
        quantity, _ = importer._extract_release_quantity(row, pipeline_type)
    assert quantity is None


def test_unknown_category_and_era_raise(tmp_path):
    with pytest.raises(ValueError, match="category"):
        imp.PHMSAImporter(MagicMock(), str(tmp_path), pipeline_types=["unknown"])
    importer = imp.PHMSAImporter(MagicMock(), str(tmp_path))
    with pytest.raises(ValueError, match="era"):
        importer._normalize_row(pd.Series(dtype=object), "gas_transmission", "unknown")


def test_registered_example_bundle(tmp_path):
    """Run the registered CSV through its router with outputs confined to temp.

    Expected pressures and counts are documented by independent hand calculation
    alongside the pipeline-safety entry in docs/registry/workflows.yaml.
    """
    root = Path(__file__).resolve().parents[3]
    registry = yaml.safe_load((root / "docs/registry/workflows.yaml").read_text())
    entry = next(w for w in registry["workflows"] if w["id"] == "pipeline-safety-ffs")
    source = root / "examples/workflows/pipeline-safety-ffs/defects.csv"
    (tmp_path / "defects.csv").write_text(source.read_text())
    cfg = {
        "data": {"source": "csv", "file": "defects.csv"},
        "Analysis": {
            "analysis_root_folder": str(tmp_path),
            "result_folder": str(tmp_path / "results"),
        },
    }
    outputs = PipelineSafety().router(cfg)["pipeline_safety"]["outputs"]
    summary = json.loads(Path(outputs["summary_json"]).read_text())
    expected = entry["assertions"]["json"][0]
    assert summary["minimum_safe_pressure_mpa"] == pytest.approx(
        expected["approx"]["minimum_safe_pressure_mpa"]
    )
    for key, value in expected["equals"].items():
        assert summary["verdict_summary"][key.split(".")[1]] == value
    report = pd.read_csv(outputs["report_csv"])
    assert (
        report["verdict"].value_counts().to_dict()
        == entry["assertions"]["csv"][0]["column_counts"]["verdict"]
    )
    assert summary["units"]["maop_mpa"] == "MPa"
    assert "0.9 * SMYS" in summary["flow_stress_basis"][0]
    assert "0.9 * SMYS" in Path(outputs["narrative_txt"]).read_text()


@pytest.mark.parametrize(
    "frame",
    [
        pd.DataFrame({"other": [1]}),
        pd.DataFrame({"verdict": [None]}),
        pd.DataFrame({"verdict": ["invalid"]}),
    ],
)
def test_summary_cannot_hide_unknown_verdicts(frame):
    from worldenergydata.pipeline_safety.workflow import PipelineSafetyWorkflow

    with pytest.raises(ValueError, match="verdict"):
        PipelineSafetyWorkflow().verdict_summary(frame)


def test_synthetic_example_module_runs():
    """The demonstration must stay within the sourced depth domain.

    Pressure qualification is independently tested in test_criteria.py; this
    checks the shipped demonstration remains runnable after input hardening.
    """
    from worldenergydata.pipeline_safety.examples.phmsa_ffs_case_study import main

    assert main() is None
