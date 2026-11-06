"""Riser preflight contract tests; no solver is imported or executed.

All numbers below are synthetic adapter inputs, not engineering data. Independent
hand checks: a tube with diameter 100 mm and wall 10 mm has bore 80 mm;
two stress bins require two cycle counts; exposure is a fraction of one year.
No fatigue life, S-N coefficient or acceptance criterion is calculated here.
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

DEMO = Path(__file__).resolve().parents[3] / "scripts" / "demo"
sys.path.insert(0, str(DEMO))

from _riser_config import main, prepare_riser_config


@pytest.fixture
def riser_input():
    """Synthetic dimensions and loads; source strings test recording only."""
    return {
        "design_life_years": 20,
        "dff": 3,
        "sn_curve": {"curve": "test-curve", "environment": "test-environment"},
        "segments": [
            {
                "id": "segment-a",
                "material": "test-material",
                "outer_diameter_mm": 100,
                "wall_thickness_mm": 10,
                "wave": {
                    "stress_ranges_MPa": [4, 8],
                    "cycles": [100, 200],
                    "scf": 1.2,
                    "histogram_period_years": 2,
                },
                "viv_cases": [
                    {
                        "stress_range_MPa": 6,
                        "frequency_hz": 0.2,
                        "exposure_fraction": 0.05,
                    }
                ],
            }
        ],
        "sources": {
            "design_life_years": "Synthetic test basis, life assumption",
            "dff": "Synthetic test basis, factor assumption",
            "sn_curve": "Synthetic test basis, curve selection",
            "segments": "Synthetic test basis, geometry and loading",
        },
    }


def test_explicit_config_preserves_inputs_and_sources(riser_input, tmp_path):
    before = copy.deepcopy(riser_input)
    prepared = prepare_riser_config(riser_input, tmp_path / "results")
    config = prepared["workflow_config"]
    assert config["basename"] == "riser_fatigue"
    assert config["riser_fatigue"] == {
        key: value for key, value in riser_input.items() if key != "sources"
    } | {"output_dir": str(tmp_path / "results")}
    assert prepared["sources"] == riser_input["sources"]
    assert prepared["engineering_qualification"] == "NOT_EVALUATED"
    assert riser_input == before
    assert not (tmp_path / "results").exists()


@pytest.mark.parametrize("contribution", ["wave", "viv_cases"])
def test_single_contribution_is_explicit(riser_input, tmp_path, contribution):
    del riser_input["segments"][0][contribution]
    result = prepare_riser_config(riser_input, tmp_path)
    assert contribution not in result["workflow_config"]["riser_fatigue"]["segments"][0]


@pytest.mark.parametrize("key", ["design_life_years", "dff", "sn_curve", "segments"])
def test_missing_top_level_inputs_and_sources_fail(riser_input, tmp_path, key):
    del riser_input[key]
    with pytest.raises(ValueError, match=key):
        prepare_riser_config(riser_input, tmp_path)


@pytest.mark.parametrize("key", ["design_life_years", "dff", "sn_curve", "segments"])
def test_each_source_is_required(riser_input, tmp_path, key):
    riser_input["sources"][key] = " "
    with pytest.raises(ValueError, match="sources"):
        prepare_riser_config(riser_input, tmp_path)


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True, "20"])
def test_nonpositive_nonfinite_and_coerced_numbers_fail(riser_input, tmp_path, value):
    riser_input["design_life_years"] = value
    with pytest.raises((TypeError, ValueError), match="design_life_years"):
        prepare_riser_config(riser_input, tmp_path)


@pytest.mark.parametrize(
    "field", ["material", "outer_diameter_mm", "wall_thickness_mm", "id"]
)
def test_segment_defaults_are_not_used(riser_input, tmp_path, field):
    del riser_input["segments"][0][field]
    with pytest.raises(ValueError, match=field):
        prepare_riser_config(riser_input, tmp_path)


def test_wall_cannot_close_the_bore(riser_input, tmp_path):
    """Hand check: 100 - 2 * 50 = 0 mm bore, so the section is rejected."""
    riser_input["segments"][0]["wall_thickness_mm"] = 50
    with pytest.raises(ValueError, match="bore"):
        prepare_riser_config(riser_input, tmp_path)


@pytest.mark.parametrize("field", ["scf", "histogram_period_years"])
def test_wave_defaults_are_not_used(riser_input, tmp_path, field):
    del riser_input["segments"][0]["wave"][field]
    with pytest.raises(ValueError, match=field):
        prepare_riser_config(riser_input, tmp_path)


@pytest.mark.parametrize("values", [[], [100], [-1, 200], [True, 200]])
def test_invalid_histogram_cycles_fail(riser_input, tmp_path, values):
    riser_input["segments"][0]["wave"]["cycles"] = values
    with pytest.raises((TypeError, ValueError), match="cycles"):
        prepare_riser_config(riser_input, tmp_path)


@pytest.mark.parametrize("value", [0, -0.1, 1.1, float("nan"), True])
def test_invalid_exposure_fails(riser_input, tmp_path, value):
    riser_input["segments"][0]["viv_cases"][0]["exposure_fraction"] = value
    with pytest.raises((TypeError, ValueError), match="exposure_fraction"):
        prepare_riser_config(riser_input, tmp_path)


def test_full_year_exposure_and_zero_cycle_bin_are_allowed(riser_input, tmp_path):
    """Fraction 1 is one whole year; zero cycles contributes no cycles."""
    riser_input["segments"][0]["viv_cases"][0]["exposure_fraction"] = 1
    riser_input["segments"][0]["wave"]["cycles"][0] = 0
    prepare_riser_config(riser_input, tmp_path)


@pytest.mark.parametrize("value", [[], None, {}])
def test_empty_or_nonlist_segments_fail(riser_input, tmp_path, value):
    riser_input["segments"] = value
    with pytest.raises(ValueError, match="segments"):
        prepare_riser_config(riser_input, tmp_path)


def test_duplicate_segments_fail(riser_input, tmp_path):
    riser_input["segments"].append(copy.deepcopy(riser_input["segments"][0]))
    with pytest.raises(ValueError, match="duplicate"):
        prepare_riser_config(riser_input, tmp_path)


def test_missing_loading_fails(riser_input, tmp_path):
    del riser_input["segments"][0]["wave"]
    del riser_input["segments"][0]["viv_cases"]
    with pytest.raises(ValueError, match="wave or viv_cases"):
        prepare_riser_config(riser_input, tmp_path)


@pytest.mark.parametrize(
    "section", ["top", "segment", "wave", "viv", "curve", "sources"]
)
def test_unknown_fields_fail(riser_input, tmp_path, section):
    target = {
        "top": riser_input,
        "segment": riser_input["segments"][0],
        "wave": riser_input["segments"][0]["wave"],
        "viv": riser_input["segments"][0]["viv_cases"][0],
        "curve": riser_input["sn_curve"],
        "sources": riser_input["sources"],
    }[section]
    target["unexpected"] = "unreviewed"
    with pytest.raises(ValueError, match="unexpected"):
        prepare_riser_config(riser_input, tmp_path)


def test_cli_writes_digest_bound_preflight_without_solver(riser_input, tmp_path):
    input_file = tmp_path / "input.json"
    output_file = tmp_path / "prepared.json"
    raw = json.dumps(riser_input).encode()
    input_file.write_bytes(raw)
    assert (
        main([str(input_file), "--out", str(output_file), "--results-dir", "results"])
        == 0
    )
    prepared = json.loads(output_file.read_text())
    assert prepared["input_sha256"] == hashlib.sha256(raw).hexdigest()
    assert prepared["workflow_config"]["riser_fatigue"]["output_dir"] == "results"
    assert input_file.read_bytes() == raw


@pytest.mark.parametrize("raw", ['{"dff": 3, "dff": 4}', '{"dff": NaN}', "[]", "{"])
def test_cli_rejects_ambiguous_json(raw, tmp_path):
    input_file = tmp_path / "input.json"
    output_file = tmp_path / "prepared.json"
    input_file.write_text(raw)
    with pytest.raises(SystemExit) as exc:
        main([str(input_file), "--out", str(output_file), "--results-dir", "results"])
    assert exc.value.code == 2
    assert not output_file.exists()


def test_cli_never_overwrites_existing_output(riser_input, tmp_path):
    input_file = tmp_path / "input.json"
    output_file = tmp_path / "prepared.json"
    input_file.write_text(json.dumps(riser_input))
    output_file.write_text("preserved")
    with pytest.raises(SystemExit):
        main([str(input_file), "--out", str(output_file), "--results-dir", "results"])
    assert output_file.read_text() == "preserved"


def test_cli_starts_without_engineering_packages(tmp_path):
    result = subprocess.run(
        [sys.executable, "-I", str(DEMO / "_riser_config.py"), "--help"],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.returncode == 0
    assert "--results-dir" in result.stdout
