"""Tests for the empirical well-access calibration adapter (#510).

Deterministic, network-free. Imports the package by file path so the suite runs
even when the heavy ``worldenergydata.common`` __init__ is unavailable
(--noconftest, no pydantic).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

# --- import the package under test by file path (import-light) ---------------
_SRC = Path(__file__).resolve().parents[5] / "src"
_PKG = (
    _SRC
    / "worldenergydata"
    / "bsee"
    / "analysis"
    / "well_access_calibration"
    / "calibrator.py"
)


def _load_calibrator():
    import sys

    name = "_wac_calibrator"
    spec = importlib.util.spec_from_file_location(name, _PKG)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    # Register before exec so dataclass annotation resolution can find the module.
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


wac = _load_calibrator()


# ---------------------------------------------------------------------------
# Synthetic fixtures with a HAND-COMPUTED expectation
# ---------------------------------------------------------------------------
def _synthetic_war() -> pd.DataFrame:
    # 4 WO over 2 wells; 2 REC; 0 ST. Durations chosen for exact means.
    return pd.DataFrame(
        {
            "API_WELL_NUMBER": [
                "608114077400",
                "608114077400",
                "608124012300",
                "608124012300",
                "608114077400",
                "608124012300",
            ],
            "WELL_ACTIVITY_CD": ["WO", "WO", "WO", "WO", "REC", "REC"],
            # rig_days = (end-start).days + 1
            "WAR_START_DT": [
                "2020-01-01",
                "2020-02-01",
                "2020-03-01",
                "2020-04-01",
                "2020-05-01",
                "2020-06-01",
            ],
            "WAR_END_DT": [
                "2020-01-07",  # 7 days -> rig_days 7
                "2020-02-04",  # 4 -> 4
                "2020-03-07",  # 7
                "2020-04-02",  # 2
                "2020-05-05",  # 5
                "2020-06-02",  # 2
            ],
        }
    )


def _synthetic_well_data(asof="2020-06-01") -> pd.DataFrame:
    # spud dates exactly 2 and 4 years before asof -> exposure 2.0 + 4.0 = 6.0 yr.
    # Use 365.25-day years so days/365.25 lands cleanly.
    asof_ts = pd.Timestamp(asof)
    spud_a = asof_ts - pd.Timedelta(days=round(2 * 365.25))
    spud_b = asof_ts - pd.Timedelta(days=round(4 * 365.25))
    return pd.DataFrame(
        {
            "API_WELL_NUMBER": ["608114077400", "608124012300"],
            "WELL_SPUD_DATE": [
                spud_a.strftime("%m/%d/%Y"),
                spud_b.strftime("%m/%d/%Y"),
            ],
        }
    )


def test_measured_rates_and_durations_hand_computed():
    war = _synthetic_war()
    wd = _synthetic_well_data()
    res = wac.calibrate_from_frames(war, well_data=wd, data_label="synthetic")

    rates = {p.name: p for p in res.intervention_rates}
    durs = {p.name: p for p in res.intervention_durations}

    # exposure = 2.0 + 4.0 = 6.0 well-years (asof = max WAR start = 2020-06-01)
    assert res.provenance["war_exposure_well_years"] == pytest.approx(6.0, abs=0.05)

    # lambda_WO = 4 events / 6.0 well-yr = 0.6667; measured
    assert rates["lambda_WO"].source == "measured"
    assert rates["lambda_WO"].sample_size == 4
    assert rates["lambda_WO"].value == pytest.approx(4 / 6.0, abs=1e-3)
    # lambda_REC = 2 / 6.0
    assert rates["lambda_REC"].value == pytest.approx(2 / 6.0, abs=1e-3)
    # lambda_ST = 0 / 6.0 = 0.0 (still measured: grounded exposure, zero events)
    assert rates["lambda_ST"].source == "measured"
    assert rates["lambda_ST"].value == pytest.approx(0.0)

    # duration means: WO mean of [7,4,7,2] = 5.0 ; REC mean of [5,2] = 3.5
    assert durs["duration_mean_WO"].source == "measured"
    assert durs["duration_mean_WO"].value == pytest.approx(5.0)
    assert durs["duration_mean_REC"].value == pytest.approx(3.5)
    # ST has no events -> needs_full_dataset (no fabricated duration)
    assert durs["duration_mean_ST"].source == "needs_full_dataset"
    assert durs["duration_mean_ST"].value is None


def test_uptime_measured_from_days_on_prod():
    war = _synthetic_war()
    prod = pd.DataFrame({"DAYS_ON_PROD": [30.4, 15.2]})  # fractions 1.0, 0.5 -> 0.75
    res = wac.calibrate_from_frames(war, production=prod)
    up = {p.name: p for p in res.uptime}["A_facility"]
    assert up.source == "measured"
    assert up.sample_size == 2
    assert up.value == pytest.approx(0.75, abs=1e-6)


def test_no_days_on_prod_is_needs_full_dataset_not_fabricated():
    war = _synthetic_war()
    prod = pd.DataFrame({"API_WELL_NUMBER": ["1"], "PRODUCTION_DATE": ["2020-01-01"]})
    res = wac.calibrate_from_frames(war, production=prod)
    up = {p.name: p for p in res.uptime}["A_facility"]
    assert up.source == "needs_full_dataset"
    assert up.value is None


def test_exposure_ungroundable_rates_scope_down_not_fabricated():
    # WAR wells that do NOT map to any spud date -> exposure ungroundable.
    war = _synthetic_war()
    wd = pd.DataFrame(
        {"API_WELL_NUMBER": ["999999999999"], "WELL_SPUD_DATE": ["01/01/2000"]}
    )
    res = wac.calibrate_from_frames(war, well_data=wd)
    rates = {p.name: p for p in res.intervention_rates}
    # counts still measured (sample_size carries the real event count) but the
    # RATE is scoped down honestly with value=None.
    assert rates["lambda_WO"].source == "needs_full_dataset"
    assert rates["lambda_WO"].value is None
    assert rates["lambda_WO"].sample_size == 4
    assert res.provenance["war_exposure_well_years"] is None


def test_empty_war_no_div_by_zero():
    res = wac.calibrate_from_frames(pd.DataFrame())
    # every parameter present, none fabricated, no exception
    assert len(res.intervention_rates) == 3
    assert all(p.source == "needs_full_dataset" for p in res.intervention_rates)
    assert all(p.value is None for p in res.intervention_rates)
    assert res.provenance["war_events_total"] == 0


def test_paramsource_invariants_enforced():
    with pytest.raises(ValueError):
        wac.ParamSource("x", 1.0, "u", "needs_full_dataset")  # value must be None
    with pytest.raises(ValueError):
        wac.ParamSource("x", None, "u", "measured")  # measured needs a value
    with pytest.raises(ValueError):
        wac.ParamSource("x", 1.0, "u", "bogus")


def test_yaml_structure_and_determinism(tmp_path):
    import yaml

    war = _synthetic_war()
    wd = _synthetic_well_data()
    prod = pd.DataFrame({"DAYS_ON_PROD": [30.4, 15.2]})
    res = wac.calibrate_from_frames(war, production=prod, well_data=wd)

    p1 = wac.write_calibration_yaml(
        res, tmp_path / "calibration.yml", timestamp="2026-06-19T00:00:00Z"
    )
    p2 = wac.write_calibration_yaml(
        res, tmp_path / "calibration2.yml", timestamp="2026-06-19T00:00:00Z"
    )
    # deterministic given a fixed timestamp
    assert p1.read_text() == p2.read_text()

    doc = yaml.safe_load(p1.read_text())
    assert doc["schema_version"] == 1
    assert set(doc) >= {
        "provenance",
        "intervention_rates",
        "intervention_durations",
        "uptime",
    }
    assert doc["provenance"]["issue"] == 510
    assert doc["provenance"]["generated_utc"] == "2026-06-19T00:00:00Z"
    # every param row carries an explicit source tag
    for section in ("intervention_rates", "intervention_durations", "uptime"):
        for row in doc[section]:
            assert row["source"] in ("measured", "needs_full_dataset")
            if row["source"] == "needs_full_dataset":
                assert row["value"] is None
