"""Tests for lower_tertiary.drilling_learning verdict logic (#775).

Exercises the PURE learning-vs-step-out verdict on a small synthetic frame,
not the real V30 workbook: a field whose later wells have lower depth-normalized
drilling intensity reads 'learn'; higher reads 'stepout'; within +/-10% is 'flat'.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from worldenergydata.lower_tertiary.drilling_learning import compute_learning  # noqa: E402


def _field(name, days, tvds, start="2010-01-01"):
    """Build n rows for one field with ascending spud dates (constant TVD)."""
    dates = pd.date_range(start, periods=len(days), freq="90D")
    return pd.DataFrame(
        {
            "LEASE_NAME": name,
            "WELL_SPUD_DATE": dates,
            "drill_days": days,
            "MAX_WELL_BORE_TVD": tvds,
        }
    )


def _verdict_for(res, field):
    return next(r["verdict"] for r in res["per_field"] if r["field"] == field)


def test_learn_stepout_flat_verdicts():
    # Constant TVD (10,000 ft) so dpk change tracks drill-days change directly.
    tvd = [10000] * 4
    learn = _field("Learner", [40, 40, 20, 20], tvd)      # 40 -> 20 dpk => -50%
    stepout = _field("Stepout", [20, 20, 40, 40], tvd)    # 20 -> 40 dpk => +100%
    flat = _field("Flat", [40, 40, 41, 41], tvd)          # ~+2.5% => flat
    df = pd.concat([learn, stepout, flat], ignore_index=True)

    res = compute_learning(df)

    assert _verdict_for(res, "Learner") == "learn"
    assert _verdict_for(res, "Stepout") == "stepout"
    assert _verdict_for(res, "Flat") == "flat"
    assert res["counts"] == {"learn": 1, "stepout": 1, "flat": 1}


def test_depth_normalization_overrides_raw_days():
    # Raw drill-days FALL (40 -> 30) but wells get much shallower, so
    # depth-normalized intensity RISES => step-out, not learning.
    df = _field("Shallower", [40, 40, 30, 30], [20000, 20000, 6000, 6000])
    res = compute_learning(df)
    assert _verdict_for(res, "Shallower") == "stepout"


def test_fields_below_four_wells_are_dropped():
    df = _field("Tiny", [40, 20, 20], [10000, 10000, 10000])
    res = compute_learning(df)
    assert res["per_field"] == []
    assert res["counts"] == {"learn": 0, "stepout": 0, "flat": 0}


def test_per_field_sorted_by_dpk_delta():
    tvd = [10000] * 4
    df = pd.concat(
        [
            _field("A", [20, 20, 40, 40], tvd),   # +100%
            _field("B", [40, 40, 20, 20], tvd),   # -50%
        ],
        ignore_index=True,
    )
    res = compute_learning(df)
    deltas = [r["dpk_delta_pct"] for r in res["per_field"]]
    assert deltas == sorted(deltas)
    assert res["per_field"][0]["field"] == "B"
