# ABOUTME: Reproduces V30 financial metrics (D&C costs, facilities, revenue, opex, NPV, MIRR)
# ABOUTME: Ports logic from generate_financial_summary_V30.py into testable functions
from __future__ import annotations

import math
import re

import numpy as np
import pandas as pd

from worldenergydata.analysis.lower_tertiary.v30_reproducer import (
    _build_first_oil_map,
    load_golden_baseline,
    load_ogor_production,
    load_v30_assumptions,
    load_v30_drilling,
    load_v30_leases,
    load_v30_wti_prices,
    reproduce_v30_production,
)


def _get_assumption(
    assumptions: pd.DataFrame, dev_system: str, metric: str, default: float = 0.0
) -> float:
    """Read a single assumption value for a dev_system."""
    metric_upper = metric.upper()
    if metric_upper not in assumptions.columns:
        return default
    row = assumptions[assumptions["DEV_SYSTEM"] == dev_system]
    if row.empty:
        row = assumptions[assumptions["DEV_SYSTEM"] == "default"]
    if row.empty:
        return default
    val = row[metric_upper].iloc[0]
    try:
        return float(val) if pd.notna(val) else default
    except (ValueError, TypeError):
        return default


def _load_assumptions_wide() -> pd.DataFrame:
    """Load assumptions pivoted with DEV_SYSTEM as rows and metrics as columns."""
    raw = load_v30_assumptions()
    if (
        "DEV_SYSTEM" in raw.columns
        and len(set(raw.columns) - {"DEV_SYSTEM", "Notes"}) >= 2
    ):
        raw = raw.rename(columns={"DEV_SYSTEM": "METRIC"})
        systems = [c for c in raw.columns if c not in {"METRIC", "Notes"}]
        long = raw.melt(
            id_vars=["METRIC"],
            var_name="DEV_SYSTEM",
            value_name="VAL",
            value_vars=systems,
        )
        long["DEV_SYSTEM"] = (
            long["DEV_SYSTEM"].str.lower().str.replace(" ", "", regex=False)
        )
        long["METRIC"] = long["METRIC"].str.upper()
        wide = long.pivot_table(
            index="DEV_SYSTEM", columns="METRIC", values="VAL", aggfunc="last"
        ).reset_index()
        for c in wide.columns:
            if c != "DEV_SYSTEM":
                wide[c] = pd.to_numeric(wide[c], errors="coerce")
        return wide
    return raw


def reproduce_dnc_costs(
    dev_name: str,
    dev_system: str,
    first_oil: pd.Timestamp | None = None,
) -> dict[str, float]:
    """Reproduce D&C total cost for a development.

    Uses the V30 methodology: drilling days × MODU rate + completion days × comp rate.
    Rate selection depends on dev_system and first_oil status.
    """
    dnc_df = load_v30_drilling()
    leases_df = load_v30_leases()
    assumptions = _load_assumptions_wide()

    # Map D&C wells to developments via SURF_LEASE_NUM
    lease_to_dev = dict(zip(leases_df["LEASE_NUM"], leases_df["DEV_NAME"]))
    dnc_df["_lease_clean"] = (
        dnc_df["SURF_LEASE_NUM"]
        .astype(str)
        .str.strip()
        .str.upper()
        .str.replace('"', "", regex=False)
        .str.replace(" ", "", regex=False)
    )
    dnc_df["development"] = dnc_df["_lease_clean"].map(lease_to_dev)
    dev_wells = dnc_df[dnc_df["development"] == dev_name]

    total_drill_days = float(
        pd.to_numeric(dev_wells["DRILLING_DAYS"], errors="coerce").sum()
    )
    total_comp_days = float(
        pd.to_numeric(dev_wells["COMPLETION_DAYS"], errors="coerce").sum()
    )

    sys_norm = dev_system.lower().replace(" ", "")
    is_dry = sys_norm == "dry"
    is_sub20 = sys_norm == "subsea20"
    has_fo = first_oil is not None and pd.notna(first_oil)

    modu_sub15 = _get_assumption(assumptions, "subsea15", "MODU_LOADED_DAYRATE_MM", 0.8)
    modu_sys = _get_assumption(assumptions, sys_norm, "MODU_LOADED_DAYRATE_MM", 0.8)
    dry_comp_rate = _get_assumption(assumptions, "dry", "DRY_TREE_RIG_RATE_MM", 0.45)

    # Drill rate: dry → subsea15; subsea20 with FO → subsea15 (pre-FO); subsea20 no FO → own rate
    if is_dry or (is_sub20 and has_fo):
        drill_rate = modu_sub15
    else:
        drill_rate = modu_sys

    # Completion rate: dry → DRY_TREE_RIG_RATE; others → own MODU rate
    comp_rate = dry_comp_rate if is_dry else modu_sys

    drilling_cost = total_drill_days * drill_rate * 1_000_000.0
    completion_cost = total_comp_days * comp_rate * 1_000_000.0

    return {
        "drilling_days": total_drill_days,
        "completion_days": total_comp_days,
        "drilling_cost_usd": drilling_cost,
        "completion_cost_usd": completion_cost,
        "dnc_total_usd": drilling_cost + completion_cost,
        "wellbores": len(dev_wells),
    }


def reproduce_facilities_cost(
    dev_system: str,
    producers: int,
    injectors: int,
    has_first_oil: bool,
) -> float:
    """Reproduce V30 facilities cost for a development."""
    assumptions = _load_assumptions_wide()
    sys_norm = dev_system.lower().replace(" ", "")
    is_dry = sys_norm == "dry"

    if not has_first_oil:
        return 0.0

    host_mm = _get_assumption(assumptions, sys_norm, "HOST_CAPEX_MM", 0.0)
    surf_per_well_mm = _get_assumption(assumptions, sys_norm, "SURF_PER_WELL_MM", 0.0)
    if is_dry:
        surf_per_well_mm = 0.0

    booster_mm = _get_assumption(
        assumptions,
        sys_norm,
        "BOOSTER_PUMP_20K_MM" if sys_norm == "subsea20" else "BOOSTER_PUMP_15K_MM",
        0.0,
    )
    booster_trig = int(
        max(
            1,
            _get_assumption(
                assumptions, sys_norm, "BOOSTER_PUMP_TRIGGER_PRODUCERS", 99
            ),
        )
    )
    wi_pump_mm = _get_assumption(assumptions, sys_norm, "WATER_INJECTION_PUMP_MM", 0.0)
    wi_trig = int(
        max(
            1,
            _get_assumption(
                assumptions, sys_norm, "WATER_INJECTION_TRIGGER_PRODUCERS", 99
            ),
        )
    )
    wi_fac_mm = _get_assumption(
        assumptions, sys_norm, "WATER_INJECTION_FACILITY_COST_MM", 0.0
    )
    dry_per_prod_mm = _get_assumption(
        assumptions, sys_norm, "DRY_WELL_SYSTEM_PER_PRODUCER_USD", 0.0
    )

    booster_count = 0
    wi_pump_count = 0
    if not is_dry:
        booster_count = (
            int(min(2, math.floor(producers / booster_trig))) if booster_trig > 0 else 0
        )
        wi_pump_count = (
            int(min(2, math.floor(producers / wi_trig)))
            if wi_trig > 0 and injectors > 0
            else 0
        )

    dry_well_usd = (dry_per_prod_mm * producers * 1_000_000.0) if is_dry else 0.0

    return (
        host_mm * 1_000_000.0
        + surf_per_well_mm * (producers + injectors) * 1_000_000.0
        + booster_count * booster_mm * 1_000_000.0
        + wi_pump_count * wi_pump_mm * 1_000_000.0
        + wi_fac_mm * 1_000_000.0
        + dry_well_usd
    )


def reproduce_producer_counts(
    dev_name: str, first_oil: pd.Timestamp | None
) -> dict[str, int]:
    """Count producers and injectors from OGOR well-level data."""
    from worldenergydata.analysis.lower_tertiary.v30_reproducer import (
        load_ogor_production,
    )

    leases_df = load_v30_leases()
    ogor = load_ogor_production(start_year=2000, end_year=2025)
    ogor = ogor[(ogor["date"] >= "2000-09-01") & (ogor["date"] <= "2025-05-31")]

    lease_to_dev = dict(zip(leases_df["LEASE_NUM"], leases_df["DEV_NAME"]))
    v30_leases = set(lease_to_dev.keys())
    ogor_v30 = ogor[ogor["LEASE_NUMBER"].isin(v30_leases)].copy()
    ogor_v30["development"] = ogor_v30["LEASE_NUMBER"].map(lease_to_dev)
    ogor_v30["API_WELL_NUMBER"] = pd.to_numeric(
        ogor_v30["API_WELL_NUMBER"], errors="coerce"
    )

    dev_ogor = ogor_v30[ogor_v30["development"] == dev_name]
    if first_oil is not None and pd.notna(first_oil):
        dev_ogor = dev_ogor[dev_ogor["date"] >= first_oil]
    producing = dev_ogor[dev_ogor["MON_O_PROD_VOL"] > 0]
    producers = (
        int(producing["API_WELL_NUMBER"].nunique()) if not producing.empty else 0
    )
    injectors = int(math.floor(producers * 0.2))

    return {"producers": producers, "injectors": injectors}


def _excel_like_mirr(cashflows: np.ndarray, discount_rate_annual: float) -> float:
    """Excel-compatible MIRR using monthly compounding."""
    nz = np.where(np.abs(cashflows) > 1e-6)[0]
    if nz.size == 0:
        return float("nan")
    cf = cashflows[nz[0] : nz[-1] + 1]
    if not (np.any(cf > 0) and np.any(cf < 0)):
        return float("nan")
    n = cf.size - 1
    r = (1.0 + discount_rate_annual) ** (1 / 12) - 1.0
    fv_pos = sum(cf[t] * ((1.0 + r) ** (n - t)) for t in range(cf.size) if cf[t] > 0)
    pv_neg = sum(cf[t] / ((1.0 + r) ** t) for t in range(cf.size) if cf[t] < 0)
    if pv_neg >= 0 or fv_pos <= 0:
        return float("nan")
    return (fv_pos / -pv_neg) ** (1.0 / n) - 1.0


def _month_floor(ts: pd.Timestamp) -> pd.Timestamp:
    """Floor a timestamp to the first day of its month."""
    if pd.isna(ts):
        return ts
    return pd.Timestamp(ts).to_period("M").to_timestamp()


def _norm_name(s: str) -> str:
    """Normalize a development/lease name (mirrors V30 generator norm_name)."""
    if pd.isna(s):
        return s
    s = str(s).strip()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("St. Malo", "St Malo")
    return s


def _build_fopw_map() -> dict[float, pd.Timestamp]:
    """Build first-oil-per-well mapping from OGOR data."""
    leases_df = load_v30_leases()
    ogor = load_ogor_production(start_year=2000, end_year=2025)
    ogor = ogor[(ogor["date"] >= "2000-09-01") & (ogor["date"] <= "2025-05-31")]
    lease_to_dev = dict(zip(leases_df["LEASE_NUM"], leases_df["DEV_NAME"]))
    v30_leases = set(lease_to_dev.keys())
    ogor_v30 = ogor[ogor["LEASE_NUMBER"].isin(v30_leases)].copy()
    ogor_v30["API_WELL_NUMBER"] = pd.to_numeric(
        ogor_v30["API_WELL_NUMBER"], errors="coerce"
    )
    fopw = (
        ogor_v30[ogor_v30["MON_O_PROD_VOL"] > 0]
        .sort_values(["API_WELL_NUMBER", "date"])
        .groupby("API_WELL_NUMBER")["date"]
        .min()
        .to_dict()
    )
    return fopw


def _build_monthly_dnc(
    dev_name: str,
    dev_system: str,
    first_oil: pd.Timestamp | None,
    date_range: pd.DatetimeIndex,
    assumptions: pd.DataFrame,
    fopw: dict[float, pd.Timestamp],
) -> pd.Series:
    """Build monthly D&C cost series allocated by well spud/TD dates.

    Mirrors the V30 generator logic: drilling days allocated forward from
    spud_date, completion days allocated backward from FO/TD date.
    Rate selection uses subsea15 rate for dry and subsea20 pre-FO drilling.
    """
    dnc_df = load_v30_drilling()
    leases_df = load_v30_leases()

    # Join DnC to developments via LEASE_NAME (matching V30 generator)
    lease_name_to_dev = dict(
        zip(
            leases_df["LEASE_NAME"].apply(_norm_name),
            leases_df["DEV_NAME"],
        )
    )
    dnc_df["_lease_norm"] = dnc_df["LEASE_NAME"].apply(_norm_name)
    dnc_df["development"] = dnc_df["_lease_norm"].map(lease_name_to_dev)
    dev_wells = dnc_df[dnc_df["development"] == dev_name]

    sys_norm = dev_system.lower().replace(" ", "")
    is_dry = sys_norm == "dry"
    is_sub20 = sys_norm == "subsea20"

    r_modu_sub15 = _get_assumption(
        assumptions, "subsea15", "MODU_LOADED_DAYRATE_MM", 0.0
    )
    r_modu_sys = _get_assumption(assumptions, sys_norm, "MODU_LOADED_DAYRATE_MM", 0.0)
    r_dry_comp = _get_assumption(assumptions, "dry", "DRY_TREE_RIG_RATE_MM", 0.0)

    fo = first_oil
    has_fo = fo is not None and pd.notna(fo)

    drill_rows: list[tuple[pd.Timestamp, float]] = []
    comp_rows: list[tuple[pd.Timestamp, float]] = []

    for _, r in dev_wells.iterrows():
        dd = float(pd.to_numeric(r["DRILLING_DAYS"], errors="coerce") or 0.0)
        cd = float(pd.to_numeric(r["COMPLETION_DAYS"], errors="coerce") or 0.0)
        sp = pd.to_datetime(r["WELL_SPUD_DATE"], errors="coerce")
        td = pd.to_datetime(r.get("TOTAL_DEPTH_DATE", pd.NaT), errors="coerce")
        api = pd.to_numeric(r["API_WELL_NUMBER"], errors="coerce")
        fow = fopw.get(api, pd.NaT) if pd.notna(api) else pd.NaT

        # --- Drilling: forward from spud_date ---
        if pd.notna(sp) and dd > 0:
            cur = pd.Timestamp(sp).normalize()
            left = int(round(dd))
            while left > 0:
                m0 = pd.Timestamp(cur.year, cur.month, 1)
                m1 = m0 + pd.offsets.MonthBegin(1)
                alloc = min(left, (m1 - cur).days)
                # Drill rate depends on month
                if is_dry or (is_sub20 and has_fo and m0 < _month_floor(fo)):
                    drill_rate = r_modu_sub15
                else:
                    drill_rate = r_modu_sys
                drill_rows.append(
                    (m0.to_period("M").to_timestamp(), alloc * drill_rate * 1_000_000.0)
                )
                left -= alloc
                cur = m1

        # --- Completion: backward from FOPW / dev-FO / TD ---
        end_month = fow if pd.notna(fow) else fo if has_fo else pd.NaT
        if pd.notna(end_month) and cd > 0:
            cur_m0 = pd.Timestamp(end_month).to_period("M").to_timestamp()
            cur = cur_m0 + pd.offsets.MonthEnd(0)
            left = int(round(cd))
            while left > 0:
                m0 = pd.Timestamp(cur.year, cur.month, 1)
                days_in_month = (
                    m0 + pd.offsets.MonthBegin(1) - pd.Timedelta(days=1)
                ).day
                alloc = min(left, days_in_month)
                comp_rate = r_dry_comp if is_dry else r_modu_sys
                comp_rows.append(
                    (
                        m0.to_period("M").to_timestamp(),
                        alloc * comp_rate * 1_000_000.0,
                    )
                )
                left -= alloc
                cur = m0 - pd.Timedelta(days=1)
        elif pd.notna(td) and cd > 0:
            # Fallback: allocate forward from TD if no FOPW and no dev FO
            cur = pd.Timestamp(td).normalize()
            left = int(round(cd))
            while left > 0:
                m0 = pd.Timestamp(cur.year, cur.month, 1)
                m1 = m0 + pd.offsets.MonthBegin(1)
                alloc = min(left, (m1 - cur).days)
                comp_rate = r_dry_comp if is_dry else r_modu_sys
                comp_rows.append(
                    (
                        m0.to_period("M").to_timestamp(),
                        alloc * comp_rate * 1_000_000.0,
                    )
                )
                left -= alloc
                cur = m1

    # Aggregate monthly
    result = pd.Series(0.0, index=date_range)
    if drill_rows:
        drill_df = pd.DataFrame(drill_rows, columns=["MONTH", "COST"])
        drill_agg = drill_df.groupby("MONTH")["COST"].sum()
        for m, v in drill_agg.items():
            if m in result.index:
                result[m] += v
            else:
                # Extend if needed (pre-production drilling)
                result[m] = result.get(m, 0.0) + v
    if comp_rows:
        comp_df = pd.DataFrame(comp_rows, columns=["MONTH", "COST"])
        comp_agg = comp_df.groupby("MONTH")["COST"].sum()
        for m, v in comp_agg.items():
            if m in result.index:
                result[m] += v
            else:
                result[m] = result.get(m, 0.0) + v

    return result


def _build_monthly_facilities(
    dev_system: str,
    producers: int,
    injectors: int,
    first_oil: pd.Timestamp | None,
    date_range: pd.DatetimeIndex,
    assumptions: pd.DataFrame,
) -> pd.Series:
    """Build monthly facilities cost series.

    Mirrors V30 generator: host CAPEX spread over HOST_PREFO_MONTHS before
    first oil; SURF + pumps + WI + dry well systems as lump sum at first oil.
    """
    result = pd.Series(0.0, index=date_range)
    has_fo = first_oil is not None and pd.notna(first_oil)
    if not has_fo:
        return result

    sys_norm = dev_system.lower().replace(" ", "")
    is_dry = sys_norm == "dry"
    is_sub20 = sys_norm == "subsea20"

    host_mm = _get_assumption(assumptions, sys_norm, "HOST_CAPEX_MM", 0.0)
    host_pre_m = int(_get_assumption(assumptions, sys_norm, "HOST_PREFO_MONTHS", 0))

    # Host CAPEX spread over pre-FO months
    if host_mm > 0 and host_pre_m > 0:
        start = _month_floor(first_oil) - pd.DateOffset(months=host_pre_m)
        fo_floor = _month_floor(first_oil)
        monthly_host = host_mm * 1_000_000.0 / host_pre_m
        for m in result.index:
            if m >= start and m < fo_floor:
                result[m] += monthly_host

    # Lump sums at first oil month
    fo_month = _month_floor(first_oil)
    surf_per_well_mm = (
        _get_assumption(assumptions, sys_norm, "SURF_PER_WELL_MM", 0.0)
        if not is_dry
        else 0.0
    )
    surf_usd = surf_per_well_mm * (producers + injectors) * 1_000_000.0

    booster_mm = _get_assumption(
        assumptions,
        sys_norm,
        "BOOSTER_PUMP_20K_MM" if is_sub20 else "BOOSTER_PUMP_15K_MM",
        0.0,
    )
    booster_trig = int(
        max(
            1,
            _get_assumption(
                assumptions, sys_norm, "BOOSTER_PUMP_TRIGGER_PRODUCERS", 99
            ),
        )
    )
    wi_pump_mm = _get_assumption(assumptions, sys_norm, "WATER_INJECTION_PUMP_MM", 0.0)
    wi_trig = int(
        max(
            1,
            _get_assumption(
                assumptions, sys_norm, "WATER_INJECTION_TRIGGER_PRODUCERS", 99
            ),
        )
    )
    wi_fac_mm = _get_assumption(
        assumptions, sys_norm, "WATER_INJECTION_FACILITY_COST_MM", 0.0
    )
    dry_per_prod_mm = _get_assumption(
        assumptions, sys_norm, "DRY_WELL_SYSTEM_PER_PRODUCER_USD", 0.0
    )

    booster_count = 0
    wi_pump_count = 0
    if not is_dry:
        booster_count = (
            int(min(2, math.floor(producers / booster_trig))) if booster_trig > 0 else 0
        )
        wi_pump_count = (
            int(min(2, math.floor(producers / wi_trig)))
            if wi_trig > 0 and injectors > 0
            else 0
        )

    pump_usd = booster_count * booster_mm * 1_000_000.0
    wi_pump_usd = wi_pump_count * wi_pump_mm * 1_000_000.0
    dry_well_usd = (
        dry_per_prod_mm * producers * 1_000_000.0
        if is_dry and dry_per_prod_mm > 0
        else 0.0
    )

    lump_sum = (
        surf_usd + pump_usd + wi_pump_usd + dry_well_usd + wi_fac_mm * 1_000_000.0
    )

    if fo_month in result.index:
        result[fo_month] += lump_sum

    return result


def reproduce_v30_financials() -> dict[str, dict]:
    """Reproduce full V30 financial summary for all developments.

    Returns dict keyed by development display name with:
      dnc_total_usd, facilities_cost_usd, revenue_usd, royalty_usd,
      variable_opex_usd, fixed_opex_usd, net_cashflow_usd, npv_usd,
      mirr_monthly, mirr_annual, producers, injectors, wellbores
    """
    baseline = load_golden_baseline()
    first_oil_map = _build_first_oil_map(baseline)
    production = reproduce_v30_production(end_date="2025-05-31")
    wti_df = load_v30_wti_prices()
    assumptions = _load_assumptions_wide()
    fopw = _build_fopw_map()

    # Determine global timeline from D&C and production data
    dnc_all = load_v30_drilling()
    dnc_spud_min = pd.to_datetime(dnc_all["WELL_SPUD_DATE"], errors="coerce").min()
    g_end = pd.Timestamp("2025-05-01")  # V30 end date (month-start)

    results: dict[str, dict] = {}
    for _proj_id, proj_data in baseline["projects"].items():
        dev_name = proj_data["display_name"]
        dev_system = proj_data.get("dev_system", "")
        first_oil = first_oil_map.get(dev_name)
        has_fo = first_oil is not None and pd.notna(first_oil)
        sys_norm = dev_system.lower().replace(" ", "")

        # D&C costs (totals for reporting)
        dnc = reproduce_dnc_costs(dev_name, dev_system, first_oil)

        # Producer/injector counts from golden baseline
        producers = proj_data.get("producers", 0)
        injectors = proj_data.get("injectors", 0)

        # Facilities cost (total for reporting)
        facilities = reproduce_facilities_cost(dev_system, producers, injectors, has_fo)

        disc_ann = _get_assumption(assumptions, sys_norm, "DISCOUNT_RATE_ANNUAL", 0.10)

        # Revenue and operating costs for producing developments
        if dev_name in production:
            monthly = production[dev_name]["monthly_production"].copy()
            merged = monthly.merge(
                wti_df[["Month", "WTI_USD"]],
                left_on="date",
                right_on="Month",
                how="left",
            )
            wti_fallback = _get_assumption(
                assumptions, sys_norm, "WTI_BASE_$/BBL", 60.0
            )
            merged["WTI_USD"] = merged["WTI_USD"].fillna(wti_fallback)

            revenue = float((merged["oil_bbl"] * merged["WTI_USD"]).sum())
            royalty_rate = _get_assumption(
                assumptions, sys_norm, "ROYALTY_RATE", 0.1875
            )
            royalty = revenue * royalty_rate

            var_opex_rate = _get_assumption(
                assumptions, sys_norm, "VARIABLE_OPEX_$/BBL", 4.0
            )
            variable_opex = float(merged["oil_bbl"].sum()) * var_opex_rate

            fixed_opex_mm_yr = _get_assumption(
                assumptions, sys_norm, "FIXED_OPEX_MM_PER_YEAR", 0.0
            )
            producing_months = len(merged[merged["oil_bbl"] > 0])
            fixed_opex = (
                (fixed_opex_mm_yr * 1_000_000.0 / 12.0) * producing_months
                if has_fo
                else 0.0
            )

            # Build operating cashflow indexed by date (month-start)
            ops_cf = pd.Series(0.0, index=merged["date"].values)
            ops_cf.index = pd.DatetimeIndex(ops_cf.index)
            rev_monthly = (merged["oil_bbl"] * merged["WTI_USD"]).values
            roy_monthly = (merged["oil_bbl"] * merged["WTI_USD"] * royalty_rate).values
            var_monthly = (merged["oil_bbl"] * var_opex_rate).values
            fix_monthly = np.zeros(len(merged))
            if has_fo and fixed_opex_mm_yr > 0:
                fix_monthly[merged["oil_bbl"].values > 0] = (
                    fixed_opex_mm_yr * 1_000_000.0 / 12.0
                )
            ops_cf[:] = rev_monthly - roy_monthly - var_monthly - fix_monthly

            # Build full timeline covering D&C activity through production
            prod_start = merged["date"].min()
            # Get earliest DnC activity for this development
            dnc_df_dev = _get_dev_dnc_dates(dev_name)
            dev_start_candidates = [prod_start]
            if dnc_df_dev is not None:
                dev_start_candidates.append(dnc_df_dev)
            if has_fo:
                host_pre_m = int(
                    _get_assumption(assumptions, sys_norm, "HOST_PREFO_MONTHS", 0)
                )
                if host_pre_m > 0:
                    dev_start_candidates.append(
                        _month_floor(first_oil) - pd.DateOffset(months=host_pre_m)
                    )
            dev_start = min(
                x for x in dev_start_candidates if x is not None and pd.notna(x)
            )
            dev_start = _month_floor(dev_start)

            full_range = pd.date_range(dev_start, g_end, freq="MS")

            # Build monthly D&C and facilities on full range
            monthly_dnc = _build_monthly_dnc(
                dev_name, dev_system, first_oil, full_range, assumptions, fopw
            )
            monthly_fac = _build_monthly_facilities(
                dev_system,
                producers,
                injectors,
                first_oil,
                full_range,
                assumptions,
            )

            # Combine: full cashflow = operating - facilities - DnC
            full_cf = pd.Series(0.0, index=full_range)
            for m in ops_cf.index:
                if m in full_cf.index:
                    full_cf[m] += ops_cf[m]
            full_cf = full_cf - monthly_fac - monthly_dnc

            # NPV: trim to first..last non-zero, discount at annual rate
            cf_array = full_cf.values.astype(float)
            nz = np.where(np.abs(cf_array) > 1e-6)[0]
            if nz.size > 0:
                cf_trimmed = cf_array[nz[0] : nz[-1] + 1]
                r_m = (1.0 + disc_ann) ** (1.0 / 12.0) - 1.0
                disc_factors = np.array(
                    [(1.0 + r_m) ** t for t in range(len(cf_trimmed))]
                )
                npv = float(np.sum(cf_trimmed / disc_factors))
            else:
                npv = 0.0

            # MIRR
            mirr_m = _excel_like_mirr(cf_array, disc_ann)
            mirr_a = (
                (1.0 + mirr_m) ** 12 - 1.0 if not math.isnan(mirr_m) else float("nan")
            )

            net_cashflow = float(full_cf.sum())

        else:
            # Exploration-only projects (no production)
            revenue = 0.0
            royalty = 0.0
            variable_opex = 0.0
            fixed_opex = 0.0

            # Build timeline for DnC-only
            dnc_df_dev = _get_dev_dnc_dates(dev_name)
            dev_start = (
                dnc_df_dev
                if dnc_df_dev is not None and pd.notna(dnc_df_dev)
                else dnc_spud_min
            )
            dev_start = _month_floor(dev_start)
            full_range = pd.date_range(dev_start, g_end, freq="MS")

            monthly_dnc = _build_monthly_dnc(
                dev_name, dev_system, first_oil, full_range, assumptions, fopw
            )
            # No facilities for exploration-only (has_fo is False)
            monthly_fac = pd.Series(0.0, index=full_range)

            full_cf = -(monthly_fac + monthly_dnc)

            cf_array = full_cf.values.astype(float)
            nz = np.where(np.abs(cf_array) > 1e-6)[0]
            if nz.size > 0:
                cf_trimmed = cf_array[nz[0] : nz[-1] + 1]
                r_m = (1.0 + disc_ann) ** (1.0 / 12.0) - 1.0
                disc_factors = np.array(
                    [(1.0 + r_m) ** t for t in range(len(cf_trimmed))]
                )
                npv = float(np.sum(cf_trimmed / disc_factors))
            else:
                npv = 0.0

            mirr_m = _excel_like_mirr(cf_array, disc_ann)
            mirr_a = (
                (1.0 + mirr_m) ** 12 - 1.0 if not math.isnan(mirr_m) else float("nan")
            )
            net_cashflow = float(full_cf.sum())

        results[dev_name] = {
            "dnc_total_usd": dnc["dnc_total_usd"],
            "drilling_cost_usd": dnc["drilling_cost_usd"],
            "completion_cost_usd": dnc["completion_cost_usd"],
            "wellbores": dnc["wellbores"],
            "producers": producers,
            "injectors": injectors,
            "facilities_cost_usd": facilities,
            "revenue_usd": revenue,
            "royalty_usd": royalty,
            "variable_opex_usd": variable_opex,
            "fixed_opex_usd": fixed_opex,
            "net_cashflow_usd": net_cashflow,
            "npv_usd": npv,
            "mirr_monthly": mirr_m,
            "mirr_annual": mirr_a,
        }

    return results


def _get_dev_dnc_dates(dev_name: str) -> pd.Timestamp | None:
    """Get earliest D&C date for a development."""
    dnc_df = load_v30_drilling()
    leases_df = load_v30_leases()
    lease_name_to_dev = dict(
        zip(
            leases_df["LEASE_NAME"].apply(_norm_name),
            leases_df["DEV_NAME"],
        )
    )
    dnc_df["_lease_norm"] = dnc_df["LEASE_NAME"].apply(_norm_name)
    dnc_df["development"] = dnc_df["_lease_norm"].map(lease_name_to_dev)
    dev_wells = dnc_df[dnc_df["development"] == dev_name]
    if dev_wells.empty:
        return None
    spud_min = pd.to_datetime(dev_wells["WELL_SPUD_DATE"], errors="coerce").min()
    td_min = pd.to_datetime(
        dev_wells.get("TOTAL_DEPTH_DATE", pd.Series(dtype="object")),
        errors="coerce",
    ).min()
    candidates = [x for x in [spud_min, td_min] if pd.notna(x)]
    return min(candidates) if candidates else None
