"""Exercise report generation and configuration failures at the cost router."""

import json
from pathlib import Path

import pytest

from worldenergydata.cost.workflow import CostWorkflow


@pytest.fixture
def cfg(tmp_path):
    return {
        "basename": "cost",
        "analysis": {"type": "disclosure_benchmark"},
        "report": {"report_date": "2026-10-20"},
        "Analysis": {"result_folder": str(tmp_path / "outputs")},
    }


def test_router_writes_report_and_preserves_config(cfg):
    result = CostWorkflow().router(cfg)

    assert result is cfg
    assert result["basename"] == "cost"
    assert result["cost"]["status"] == "completed"
    outputs = {key: Path(value) for key, value in result["cost"]["outputs"].items()}
    root = Path(cfg["Analysis"]["result_folder"])
    assert outputs == {
        "html": root / "operator_cost_benchmarking.html",
        "facts": root / "operator_cost_benchmarking_facts.json",
    }
    facts = json.loads(outputs["facts"].read_text())
    assert facts["operators_covered"] == 3
    assert len(facts["operator_rows"]) == 12
    assert facts["report_date"] == cfg["report"]["report_date"]
    assert "<svg" in outputs["html"].read_text()


def test_router_uses_configured_edition_date(cfg):
    cfg["report"]["report_date"] = "2026-11-01"
    result = CostWorkflow().router(cfg)
    facts = json.loads(Path(result["cost"]["outputs"]["facts"]).read_text())
    assert facts["report_date"] == "2026-11-01"


def test_registered_outputs_match_regeneration_and_notebook(cfg):
    result = CostWorkflow().router(cfg)
    repo = Path(__file__).resolve().parents[3]
    registered = repo / "examples/workflows/cost-disclosure-benchmark/outputs"
    for path in result["cost"]["outputs"].values():
        output = Path(path)
        assert output.read_bytes() == (registered / output.name).read_bytes()
        assert output.read_bytes() == (repo / "reports/gtm" / output.name).read_bytes()


def test_router_rejects_unknown_analysis_before_writing(cfg):
    cfg["analysis"]["type"] = "unknown"
    with pytest.raises(ValueError, match="Unsupported cost analysis type: unknown"):
        CostWorkflow().router(cfg)
    assert "cost" not in cfg
    assert not Path(cfg["Analysis"]["result_folder"]).exists()


@pytest.mark.parametrize(
    "section,key",
    [
        ("analysis", "type"),
        ("report", "report_date"),
        ("Analysis", "result_folder"),
    ],
)
def test_router_requires_explicit_configuration(cfg, section, key):
    del cfg[section][key]
    with pytest.raises(KeyError, match=key):
        CostWorkflow().router(cfg)
    assert "cost" not in cfg


def test_router_propagates_invalid_date_without_success_status(cfg):
    cfg["report"]["report_date"] = "invalid-date"
    with pytest.raises(ValueError, match="Invalid isoformat string"):
        CostWorkflow().router(cfg)
    assert "cost" not in cfg
    assert not Path(cfg["Analysis"]["result_folder"]).exists()


def test_router_propagates_output_failure_without_success_status(cfg, tmp_path):
    occupied = tmp_path / "occupied"
    occupied.write_text("existing input")
    cfg["Analysis"]["result_folder"] = str(occupied)
    with pytest.raises(FileExistsError):
        CostWorkflow().router(cfg)
    assert "cost" not in cfg
    assert occupied.read_text() == "existing input"
