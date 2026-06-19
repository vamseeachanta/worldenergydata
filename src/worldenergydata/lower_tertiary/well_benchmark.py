"""ABOUTME: Well-grained Lower-Tertiary benchmarking aggregator (worldenergydata#499).
ABOUTME: Per-well drilling/completion/first-oil/decline/uptime/cum-oil/revenue/interventions.

A saved, parameterized analytic: for a play + spud-year range, emit one row per
well with the metrics a benchmarking client asks for. It is the **well-grained**
sibling of the field-grained ``all_fields_runner`` and reuses the existing
primitives rather than re-deriving them:

* drilling/completion timing + spud  -> ops_timeline (WAR + V30 drilling)
* first oil + cumulative oil + uptime -> OGOR-A monthly production
* decline (D, b, EUR)                 -> forecasting.DeclineAnalysis
* per-well revenue                    -> monthly oil x historical WTI deck
* intervention history                -> ops_timeline WAR operations

Everything runs on **actual BSEE data** (resolved via the repo data resolver /
``WED_DATA_ROOT``). When a metric cannot be derived for a well from the real
data, it is left null / flagged — never fabricated (flag-don't-fake).

Determinism: every step is a pure function of the input config + the on-disk
BSEE data; no clocks, no RNG in the row values. Same inputs -> same table.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from worldenergydata.bsee.analysis.uptime import compute_uptime
from worldenergydata.lower_tertiary import ops_timeline
from worldenergydata.lower_tertiary.wti_prices import load_extended_wti_prices

# Operations that count as a post-completion intervention (workover /
# recompletion / sidetrack / re-entry). Mirrors ops_timeline labels.
_INTERVENTION_OPS = {
    "Workover",
    "Recompletion",
    "Sidetrack",
    "Re-entry / recompletion",
}


@dataclass
class BenchmarkConfig:
    """Parameters for a well-benchmark run (mirrors the saved YAML block)."""

    play: str = "lower_tertiary"
    spud_year_min: Optional[int] = 2010
    spud_year_max: Optional[int] = None
    fields: Optional[list[str]] = None  # None -> all producing LT fields
    end_date: Optional[str] = None  # None -> auto-latest OGOR-A month
    metrics: list[str] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, m: dict) -> "BenchmarkConfig":
        return cls(
            play=m.get("play", "lower_tertiary"),
            spud_year_min=m.get("spud_year_min", 2010),
            spud_year_max=m.get("spud_year_max"),
            fields=m.get("fields"),
            end_date=m.get("end_date"),
            metrics=m.get("metrics", []) or [],
        )


# Producing Lower-Tertiary (Wilcox) fields, display names as in the golden
# baseline. Pre-production fields (no first oil) are intentionally excluded; the
# play roster is derived from the V30 lease->development map, not hardcoded APIs.
_PRODUCING_LT_FIELDS = [
    "Jack St Malo",
    "Stones",
    "Julia",
    "Big Foot",
    "Cascade Chinook",
    "Anchor",
    "Shenandoah",
]


def _lt_field_leases(fields: Optional[list[str]]) -> dict[str, list[str]]:
    """Map each requested LT field to its V30 lease numbers (deterministic)."""
    target = fields if fields else _PRODUCING_LT_FIELDS
    out: dict[str, list[str]] = {}
    for dev in target:
        leases = ops_timeline.leases_for_dev(dev)
        if leases:
            out[dev] = leases
    return out


def select_play_wells(
    play: str = "lower_tertiary",
    spud_year_min: Optional[int] = None,
    spud_year_max: Optional[int] = None,
    fields: Optional[list[str]] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """Roster of wells for a play, filtered by spud year.

    Returns one row per OGOR-A producing API well in the play's leases, with
    its field, lease, spud date (from V30 drilling data when available) and
    first-production date. The spud-year filter is applied on the spud date;
    wells with no resolvable spud date are kept (spud null) unless a min/max
    bound excludes them — we never drop a real producing well for missing
    drilling metadata silently (they are marked spud=NaT).
    """
    if play != "lower_tertiary":
        raise ValueError(f"Unsupported play {play!r}; only 'lower_tertiary' is wired")

    field_leases = _lt_field_leases(fields)
    all_leases = sorted({lz for leases in field_leases.values() for lz in leases})
    lease_to_field = {
        lz: dev for dev, leases in field_leases.items() for lz in leases
    }
    if not all_leases:
        return pd.DataFrame(
            columns=["API_WELL_NUMBER", "field", "lease", "spud", "first_oil"]
        )

    eff_end = end_date or ops_timeline.month_end_str(
        ops_timeline.detect_latest_ogor_month()
    )
    end_year = max(2025, int(str(eff_end)[:4]))
    ogor = ops_timeline.v30_reproducer.load_ogor_production(
        start_year=2000, end_year=end_year
    )
    ogor = ogor[(ogor["date"] >= "2000-09-01") & (ogor["date"] <= eff_end)].copy()
    ogor["LEASE_NUMBER"] = ogor["LEASE_NUMBER"].astype(str).str.strip().str.upper()
    ogor = ogor[ogor["LEASE_NUMBER"].isin(all_leases)]
    ogor["MON_O_PROD_VOL"] = pd.to_numeric(ogor["MON_O_PROD_VOL"], errors="coerce").fillna(0.0)
    ogor = ogor[ogor["MON_O_PROD_VOL"] > 0]
    ogor["API_WELL_NUMBER"] = ogor["API_WELL_NUMBER"].astype(str).str.strip()
    if ogor.empty:
        return pd.DataFrame(
            columns=["API_WELL_NUMBER", "field", "lease", "spud", "first_oil"]
        )

    # First production per API + the lease it first produced on (for field map).
    first = (
        ogor.sort_values("date")
        .groupby("API_WELL_NUMBER", as_index=False)
        .agg(first_oil=("date", "min"), lease=("LEASE_NUMBER", "first"))
    )
    first["field"] = first["lease"].map(lease_to_field)

    # Spud dates from V30 drilling data per field (cost-aligned, complete to
    # first appraisal). Keyed by API; missing -> NaT.
    spud_rows: list[pd.DataFrame] = []
    for dev in field_leases:
        sp = ops_timeline.derive_spud_milestones(dev, eff_end)
        if not sp.empty:
            spud_rows.append(sp[["API_WELL_NUMBER", "date"]].rename(columns={"date": "spud"}))
    if spud_rows:
        spud = pd.concat(spud_rows, ignore_index=True)
        spud["API_WELL_NUMBER"] = spud["API_WELL_NUMBER"].astype(str).str.strip()
        # earliest spud per producing API12 (match on 12-digit wellbore prefix).
        spud["wellbore"] = spud["API_WELL_NUMBER"].str[:12]
        spud = spud.groupby("wellbore", as_index=False)["spud"].min()
        first["wellbore"] = first["API_WELL_NUMBER"].str[:12]
        first = first.merge(spud, on="wellbore", how="left").drop(columns="wellbore")
    else:
        first["spud"] = pd.NaT

    # Spud-year filter (keep wells with unknown spud unless a bound excludes).
    spud_year = first["spud"].dt.year
    if spud_year_min is not None:
        first = first[(spud_year >= spud_year_min) | spud_year.isna()]
        spud_year = first["spud"].dt.year
    if spud_year_max is not None:
        first = first[(spud_year <= spud_year_max) | spud_year.isna()]

    return first[["API_WELL_NUMBER", "field", "lease", "spud", "first_oil"]].sort_values(
        "API_WELL_NUMBER"
    ).reset_index(drop=True)


def _well_monthly_oil(ogor_well: pd.DataFrame) -> pd.DataFrame:
    """Monthly oil volume for one well, indexed by month-start ``date``."""
    g = (
        ogor_well.groupby(ogor_well["date"].dt.to_period("M").dt.to_timestamp())[
            "MON_O_PROD_VOL"
        ]
        .sum()
        .rename("oil_bbl")
    )
    return g.to_frame()


def _decline_for_well(ogor_well: pd.DataFrame) -> dict:
    """Best decline fit for one well (D annualized, b, EUR). Flag if unreliable."""
    from worldenergydata.bsee.analysis.forecasting.bsee_decline_adapter import (
        BseeDeclineAdapter,
    )
    from worldenergydata.bsee.analysis.forecasting.decline_analysis import (
        DeclineAnalysis,
    )

    out = {"decline_annual": np.nan, "b_factor": np.nan, "eur_mmbbl": np.nan,
           "decline_model": None, "decline_r2": np.nan, "decline_flag": None}
    # Need a minimum of monthly points for a meaningful fit.
    monthly = _well_monthly_oil(ogor_well).reset_index()
    monthly = monthly[monthly["oil_bbl"] > 0]
    if len(monthly) < 6:
        out["decline_flag"] = "insufficient_history"
        return out
    try:
        ts = BseeDeclineAdapter().extract_from_dataframe(
            ogor_well, product="oil", label="well"
        )
        cmp = DeclineAnalysis().fit_all_models(ts)
        curve = cmp.best_fit.curve
        d_month = float(curve.decline_rate)
        # Monthly nominal -> effective annual decline.
        out["decline_annual"] = 1.0 - (1.0 - min(d_month, 0.999)) ** 12 if d_month < 1 else float("nan")
        out["b_factor"] = float(curve.b_factor) if curve.b_factor is not None else np.nan
        out["decline_model"] = cmp.best_model
        out["decline_r2"] = float(curve.r_squared)
        eur = DeclineAnalysis().calculate_eur(cmp).get(cmp.best_model)
        # EUR from calculate_eur is in rate-units * periods; rate here is
        # bbl/day so multiply by ~30.44 days/month to express cumulative bbl.
        if eur is not None and np.isfinite(eur):
            out["eur_mmbbl"] = eur * 30.44 / 1e6
        if cmp.best_fit.curve.r_squared < 0.3:
            out["decline_flag"] = "low_fit_quality"
    except Exception as exc:  # noqa: BLE001 - fit failures flagged, not faked
        out["decline_flag"] = f"fit_failed: {type(exc).__name__}"
    return out


def _wti_lookup(wti_df: pd.DataFrame) -> pd.Series:
    """Monthly WTI ($/bbl) indexed by month-start, from the extended deck."""
    df = wti_df.copy()
    df["Month"] = pd.to_datetime(df["Month"]).dt.to_period("M").dt.to_timestamp()
    return df.groupby("Month")["WTI_USD"].last()


def benchmark_well(
    api12: str,
    field_name: str,
    lease: str,
    spud,
    first_oil,
    ogor_well: pd.DataFrame,
    ops: pd.DataFrame,
    wti: pd.Series,
    uptime_row: Optional[dict],
) -> dict:
    """Assemble one benchmark row for a single well from real BSEE data."""
    wellbore = str(api12)[:12]
    monthly = _well_monthly_oil(ogor_well)
    cum_oil = float(monthly["oil_bbl"].sum())

    # Drilling / completion days from the ops timeline (spud -> completion).
    well_ops = ops[ops["API_WELL_NUMBER"].astype(str).str[:12] == wellbore]
    spud_dt = pd.to_datetime(spud) if spud is not None and pd.notna(spud) else pd.NaT
    comp_dt = pd.NaT
    comp = well_ops[well_ops["operation"] == "Completion"]
    if not comp.empty:
        comp_dt = pd.to_datetime(comp["date"]).min()
    drilling_days = (
        int((comp_dt - spud_dt).days)
        if pd.notna(spud_dt) and pd.notna(comp_dt) and comp_dt >= spud_dt
        else None
    )
    completion_days = (
        int((pd.to_datetime(first_oil) - comp_dt).days)
        if pd.notna(comp_dt) and first_oil is not None and pd.notna(first_oil)
        and pd.to_datetime(first_oil) >= comp_dt
        else None
    )

    # Per-well revenue: monthly oil x same-month WTI (historical realized deck).
    rev = 0.0
    matched_months = 0
    for m, vol in monthly["oil_bbl"].items():
        price = wti.get(m)
        if price is not None and np.isfinite(price):
            rev += float(vol) * float(price)
            matched_months += 1
    revenue_flag = (
        "partial_wti_coverage"
        if matched_months < len(monthly)
        else None
    )

    # Interventions (post-completion workover/recompletion/sidetrack/re-entry).
    intr = well_ops[well_ops["operation"].isin(_INTERVENTION_OPS)]
    interventions = int(len(intr))
    intr_history = "; ".join(
        f"{r['operation']} {pd.to_datetime(r['date']).date()}"
        for _, r in intr.sort_values("date").iterrows()
    )

    upt = uptime_row or {}
    return {
        "api12": api12,
        "well": wellbore,
        "field": field_name,
        "lease": lease,
        "spud": spud_dt.date() if pd.notna(spud_dt) else None,
        "drilling_days": drilling_days,
        "completion_days": completion_days,
        "first_oil": pd.to_datetime(first_oil).date() if first_oil is not None and pd.notna(first_oil) else None,
        "cum_oil_mmbbl": round(cum_oil / 1e6, 4),
        "uptime_pct": round(upt.get("uptime_pct"), 1) if upt.get("uptime_pct") is not None and np.isfinite(upt.get("uptime_pct", np.nan)) else None,
        "uptime_flag": "low_confidence" if upt.get("low_confidence") else None,
        "est_revenue_mm": round(rev / 1e6, 1),
        "revenue_flag": revenue_flag,
        "interventions": interventions,
        "intervention_history": intr_history,
    }


def run_well_benchmark(cfg: BenchmarkConfig) -> pd.DataFrame:
    """Per-well benchmark table for the configured play/year-range.

    One row per well, sorted by cumulative oil (descending). Pure function of
    the config + on-disk BSEE data -> deterministic.
    """
    ops_timeline.ensure_ogor_loader()
    eff_end = cfg.end_date or ops_timeline.month_end_str(
        ops_timeline.detect_latest_ogor_month()
    )

    wells = select_play_wells(
        cfg.play, cfg.spud_year_min, cfg.spud_year_max, cfg.fields, eff_end
    )
    if wells.empty:
        return pd.DataFrame()

    field_leases = _lt_field_leases(cfg.fields)
    all_leases = sorted({lz for leases in field_leases.values() for lz in leases})

    end_year = max(2025, int(str(eff_end)[:4]))
    ogor = ops_timeline.v30_reproducer.load_ogor_production(
        start_year=2000, end_year=end_year
    )
    ogor = ogor[(ogor["date"] >= "2000-09-01") & (ogor["date"] <= eff_end)].copy()
    ogor["LEASE_NUMBER"] = ogor["LEASE_NUMBER"].astype(str).str.strip().str.upper()
    ogor = ogor[ogor["LEASE_NUMBER"].isin(all_leases)]
    ogor["API_WELL_NUMBER"] = ogor["API_WELL_NUMBER"].astype(str).str.strip()
    ogor["MON_O_PROD_VOL"] = pd.to_numeric(ogor["MON_O_PROD_VOL"], errors="coerce").fillna(0.0)

    # Uptime for every well in one pass (DAYS_ON_PROD-based).
    uptime_df = compute_uptime(ogor)
    uptime_map = {r["API_WELL_NUMBER"]: r for r in uptime_df.to_dict("records")}

    # Operations timeline once per field (covers all leases for that field).
    ops_all: list[pd.DataFrame] = []
    for dev, leases in field_leases.items():
        t = ops_timeline.build_operations_timeline(leases, eff_end, dev_name=dev)
        if not t.empty:
            ops_all.append(t)
    ops = pd.concat(ops_all, ignore_index=True) if ops_all else pd.DataFrame(
        columns=["API_WELL_NUMBER", "date", "operation", "detail"]
    )

    wti = _wti_lookup(load_extended_wti_prices(through_date=eff_end))

    rows: list[dict] = []
    for _, w in wells.iterrows():
        api = w["API_WELL_NUMBER"]
        ogor_well = ogor[ogor["API_WELL_NUMBER"] == api]
        if ogor_well.empty:
            continue
        row = benchmark_well(
            api12=api,
            field_name=w["field"],
            lease=w["lease"],
            spud=w["spud"],
            first_oil=w["first_oil"],
            ogor_well=ogor_well,
            ops=ops,
            wti=wti,
            uptime_row=uptime_map.get(api),
        )
        decl = _decline_for_well(ogor_well)
        row.update(
            {
                "decline_annual_pct": round(decl["decline_annual"] * 100, 1)
                if decl["decline_annual"] == decl["decline_annual"]
                else None,
                "decline_model": decl["decline_model"],
                "eur_mmbbl": round(decl["eur_mmbbl"], 3)
                if decl["eur_mmbbl"] == decl["eur_mmbbl"]
                else None,
                "decline_flag": decl["decline_flag"],
            }
        )
        rows.append(row)

    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    return out.sort_values("cum_oil_mmbbl", ascending=False).reset_index(drop=True)
