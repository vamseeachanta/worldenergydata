"""Configured-gate verdicts for synthetic pressure-screen observations."""

import json

import numpy as np
import pandas as pd
import pytest
import yaml

from worldenergydata.analysis.underpressured_screen.screen import (
    build_screen_summary,
    run_screen,
)


@pytest.fixture(params=[0, 1], ids=["empty", "one-well"])
def summary_frames(request):
    wells = pd.DataFrame(
        {
            "well_key": ["synthetic-control"],
            "state": ["KS"],
            "source_name": ["synthetic_source"],
            "era": ["depleted"],
            "pressure_tier": ["severely_underpressured"],
            "near_vacuum": [False],
            "bhp_gradient_psi_ft": [0.24],
        }
    ).iloc[: request.param]
    ranking = pd.DataFrame({"field": ["SYNTHETIC CONTROL"]}).iloc[: request.param]
    return wells, ranking


@pytest.mark.parametrize(
    "validation,participation,expected",
    [
        (True, True, "pass"),
        (True, False, "fail"),
        (False, True, "fail"),
        (False, False, "fail"),
    ],
)
def test_summary_status_preserves_evidence(
    summary_frames, validation, participation, expected
):
    wells, ranking = summary_frames
    load_summary = {
        "input_row_counts": {"synthetic_source": 1},
        "loaded_row_counts": {"synthetic_source": len(wells)},
        "source_warnings": {"synthetic_source": ["synthetic warning"]},
    }
    summary = build_screen_summary(
        wells, ranking, {"passed": validation}, {"passed": participation}, load_summary
    )

    assert summary["screening_status"] == expected
    assert summary["screening_scope"] == (
        "Configured validation and participation gates only; does not establish "
        "measured virgin bottom-hole pressure, coverage beyond configured "
        "requirements, or commercial viability."
    )
    assert {
        key: value
        for key, value in summary.items()
        if key not in {"screening_status", "screening_scope"}
    } == {
        "wells_screened": len(wells),
        "tier_counts": {"severely_underpressured": 1} if len(wells) else {},
        "near_vacuum_wells": 0,
        "fields_ranked": len(ranking),
        "median_gradient_psi_ft": 0.24 if len(wells) else None,
        "validation_gate": {"passed": validation},
        "participation_gate": {"passed": participation},
        "era_note": ["depleted"] if len(wells) else [],
        "state_counts": {"KS": 1} if len(wells) else {},
        "source_counts": {"synthetic_source": 1} if len(wells) else {},
        **load_summary,
    }


@pytest.mark.parametrize("gate_name", ["validation_gate", "participation_gate"])
@pytest.mark.parametrize(
    "malformed",
    [
        {},
        {"passed": None},
        {"passed": "true"},
        {"passed": "false"},
        {"passed": 0},
        {"passed": 1},
        {"passed": []},
        {"passed": {}},
        {"passed": np.bool_(True)},
        {"passed": pd.NA},
    ],
    ids=[
        "missing",
        "null",
        "true-text",
        "false-text",
        "zero",
        "one",
        "list",
        "mapping",
        "numpy-bool",
        "pandas-null",
    ],
)
def test_malformed_gate_verdicts_raise(summary_frames, gate_name, malformed):
    wells, ranking = summary_frames
    # A false companion gate must not hide a malformed result via short-circuiting.
    gates = {
        "validation_gate": {"passed": False},
        "participation_gate": {"passed": False},
    }
    gates[gate_name] = malformed

    with pytest.raises(ValueError, match=rf"{gate_name}\.passed must be a boolean"):
        build_screen_summary(wells, ranking, load_summary={}, **gates)


@pytest.fixture
def screen_config(tmp_path):
    # Synthetic measured BHP: 1200 psia / 5000 ft = 0.24 psi/ft.
    observations = pd.DataFrame(
        {
            "well_key": ["synthetic-control"],
            "state": ["KS"],
            "field": ["SYNTHETIC CONTROL"],
            "test_year": [2024],
            "pressure_kind": ["BHP_measured"],
            "pressure_psia": [1200.0],
            "reference_depth_ft": [5000.0],
        }
    )
    source = tmp_path / "observations.parquet"
    observations.to_parquet(source)
    output = tmp_path / "outputs"
    config = {
        "inputs": [
            {"name": "synthetic_source", "path": str(source), "era": "depleted"}
        ],
        "bhp_estimate": {"gas_sg": 0.65, "z_avg": 0.95, "t_avg_rankine": 520.0},
        "tiers": {
            "hydrostatic_normal_min": 0.433,
            "mild_underpressure_min": 0.35,
            "near_vacuum_whp_psia": 50.0,
        },
        "field_ranking": {"min_wells_per_field": 1},
        "validation_gate": {
            "required_fields_in_top10": ["SYNTHETIC CONTROL"],
            "required_tier": "severely_underpressured",
        },
        "output": {"base_dir": str(output)},
    }
    return config, output


@pytest.mark.parametrize("failed_gate", [None, "validation", "participation"])
def test_run_screen_persists_status_before_gate_failure(
    tmp_path, screen_config, failed_gate
):
    config, output = screen_config
    if failed_gate == "validation":
        config["validation_gate"]["required_fields_in_top10"] = ["ABSENT CONTROL"]
    elif failed_gate == "participation":
        config["participation_gate"] = {"required_states": {"TX": {"min_wells": 1}}}
    config_path = tmp_path / "screen.yml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    if failed_gate:
        with pytest.raises(RuntimeError, match=f"{failed_gate.title()} gate failed"):
            run_screen(config_path)
    else:
        returned = run_screen(config_path)

    saved = json.loads((output / "screen_summary.json").read_text(encoding="utf-8"))
    assert saved["screening_status"] == ("fail" if failed_gate else "pass")
    assert saved["validation_gate"]["passed"] is (failed_gate != "validation")
    assert saved["participation_gate"]["passed"] is (failed_gate != "participation")
    assert saved["era_note"] == ["depleted"]
    assert saved["wells_screened"] == 1
    assert saved["median_gradient_psi_ft"] == 0.24
    assert "configured" in saved["screening_scope"].lower()
    assert len(pd.read_parquet(output / "well_screen_earliest.parquet")) == 1
    assert len(pd.read_parquet(output / "underpressured_field_ranking.parquet")) == 1
    if not failed_gate:
        assert returned == saved
        assert saved["participation_gate"] == {"passed": True, "states": {}}
