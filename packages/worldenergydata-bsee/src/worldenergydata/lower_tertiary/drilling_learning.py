"""ABOUTME: Learning-vs-step-out analytic for the GoM Lower-Tertiary drilling insight.
ABOUTME: Splits each field's wells (ordered by spud) into first/last half and compares
ABOUTME: depth-normalized drilling intensity (rig-days per 1,000 ft TVD) to tell real
ABOUTME: repetition-driven learning apart from wells simply getting shallower (#775).

Public surface:
    compute_learning(df) -> dict   # side-effect free; df is the cleaned wells frame

The input frame is the output of ``build_drilling_insights.load_wells``: columns
``LEASE_NAME``, ``WELL_SPUD_DATE`` (datetime), ``drill_days`` (0 -> NaN),
``MAX_WELL_BORE_TVD``. Only wells with a derivable drill_days and a spud date are
used; only fields with n>=4 such wells get a verdict. Verdict is on the
depth-normalized (dpk) first-half -> last-half median change, threshold +/-10%.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

VERDICT_THRESHOLD_PCT = 10.0


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """Keep wells with a derivable drill_days + spud date; add dpk column."""
    d = df.loc[df["drill_days"].notna() & df["WELL_SPUD_DATE"].notna()].copy()
    d["MAX_WELL_BORE_TVD"] = pd.to_numeric(d["MAX_WELL_BORE_TVD"], errors="coerce")
    d["drill_days"] = pd.to_numeric(d["drill_days"], errors="coerce")
    d["dpk"] = d["drill_days"] / (d["MAX_WELL_BORE_TVD"] / 1000.0)
    return d


def _verdict(dpk_delta_pct: float) -> str:
    if dpk_delta_pct < -VERDICT_THRESHOLD_PCT:
        return "learn"
    if dpk_delta_pct > VERDICT_THRESHOLD_PCT:
        return "stepout"
    return "flat"


def compute_learning(df: pd.DataFrame) -> dict:
    """Return per-field learning-vs-step-out verdicts + a pooled slope + St Malo.

    See module docstring. All medians are first-half vs last-half of the
    spud-ordered wells; the verdict is on the depth-normalized (dpk) change so a
    field that merely drilled shallower wells does not read as "learning".
    """
    d = _clean(df)

    per_field: list[dict] = []
    seqs: list[float] = []
    days: list[float] = []
    for field, g in d.groupby("LEASE_NAME"):
        g = g.sort_values("WELL_SPUD_DATE")
        n = len(g)
        if n < 4:
            continue
        half = n // 2
        h1, h2 = g.iloc[:half], g.iloc[half:]
        h1_median = float(h1["drill_days"].median())
        h2_median = float(h2["drill_days"].median())
        dpk_h1 = float(h1["dpk"].median())
        dpk_h2 = float(h2["dpk"].median())
        dpk_delta_pct = (dpk_h2 - dpk_h1) / dpk_h1 * 100.0 if dpk_h1 else float("nan")
        tvd_drift = float(
            h2["MAX_WELL_BORE_TVD"].median() - h1["MAX_WELL_BORE_TVD"].median()
        )
        per_field.append(
            {
                "field": str(field),
                "n": int(n),
                "h1_median": h1_median,
                "h2_median": h2_median,
                "dpk_h1": dpk_h1,
                "dpk_h2": dpk_h2,
                "dpk_delta_pct": dpk_delta_pct,
                "tvd_drift": tvd_drift,
                "verdict": _verdict(dpk_delta_pct),
            }
        )
        for i, val in enumerate(g["drill_days"].to_numpy(float)):
            seqs.append(i + 1)
            days.append(val)

    per_field.sort(key=lambda r: r["dpk_delta_pct"])
    counts = {
        "learn": sum(1 for r in per_field if r["verdict"] == "learn"),
        "stepout": sum(1 for r in per_field if r["verdict"] == "stepout"),
        "flat": sum(1 for r in per_field if r["verdict"] == "flat"),
    }

    if len(seqs) >= 2:
        sa, da = np.array(seqs, float), np.array(days, float)
        slope = float(np.polyfit(sa, da, 1)[0])
        r = float(np.corrcoef(sa, da)[0, 1])
    else:
        slope, r = float("nan"), float("nan")
    pooled = {"slope_per_well": slope, "r": r, "n": len(seqs)}

    stmalo = next((r for r in per_field if r["field"] == "St Malo"), None)

    return {
        "per_field": per_field,
        "counts": counts,
        "pooled": pooled,
        "stmalo": stmalo,
    }
