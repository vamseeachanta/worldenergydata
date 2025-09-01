# generate_financial_summary.py
# Builds per-DEV monthly schedules and a project summary workbook.
# Assumes chronological_lease_analysis.xlsx contains monthly rows from earliest spud onward.

import pandas as pd
import numpy as np
import math

# ----------------------------- Helpers -----------------------------
def month_floor(ts):
    if pd.isna(ts):
        return ts
    return pd.Timestamp(ts).normalize().replace(day=1)

def month_str(ts):
    return pd.Timestamp(ts).strftime("%b-%Y") if pd.notna(ts) else ""

def safe_num(x, default=0.0):
    try:
        v = float(x)
        if np.isnan(v):
            return default
        return v
    except Exception:
        return default

# ----------------------------- Load monthly dataset -----------------------------
final_df = pd.read_excel("chronological_lease_analysis.xlsx")

# Normalize D&C column names
final_df.rename(columns={
    "ALLOCATED_DRILLING_DAYS": "DRILLING_DAYS",
    "ALLOCATED_COMPLETION_DAYS": "COMPLETION_DAYS"
}, inplace=True)

# DEV mapping
dev_map = pd.read_excel("leases.xlsx")[["LEASE_NAME", "DEV_NAME", "DEV_SYSTEM"]].drop_duplicates()

# Merge DEV onto monthly
final_df = final_df.merge(dev_map, on="LEASE_NAME", how="left")

# Types
final_df["MONTH"] = pd.to_datetime(final_df["MONTH"], errors="coerce").dt.to_period("M").dt.to_timestamp()
for col in ["MONTHLY_OIL_VOLUME", "DRILLING_DAYS", "COMPLETION_DAYS", "WTI_USD"]:
    if col in final_df.columns:
        final_df[col] = pd.to_numeric(final_df[col], errors="coerce").fillna(0.0)
final_df["API_WELL_NUMBER"] = pd.to_numeric(final_df.get("API_WELL_NUMBER", np.nan), errors="coerce")

# Global schedule bounds from already-anchored monthly file
global_start = month_floor(final_df["MONTH"].min())
global_end = month_floor(final_df["MONTH"].max())

# ----------------------------- Load assumptions -----------------------------
assumptions_raw = pd.read_csv("lease_assumptions.csv", index_col=0)
assumptions = assumptions_raw.transpose()
assumptions.index.name = "DEV_SYSTEM"
assumptions.reset_index(inplace=True)
assumptions["DEV_SYSTEM"] = assumptions["DEV_SYSTEM"].astype(str)
for col in assumptions.columns:
    if col != "DEV_SYSTEM":
        assumptions[col] = pd.to_numeric(assumptions[col], errors="coerce")

# ----------------------------- FO month and counts -----------------------------
# FO by DEV: first month with production
fo_months = (
    final_df[final_df["MONTHLY_OIL_VOLUME"] > 0]
    .groupby("DEV_NAME")["MONTH"]
    .min()
    .reset_index()
    .rename(columns={"MONTH": "FO_Month"})
)

# Well counts
total_wells = final_df.groupby("DEV_NAME")["API_WELL_NUMBER"].nunique().reset_index(name="TOTAL_WELLS")
producer_wells = (
    final_df[final_df["MONTHLY_OIL_VOLUME"] > 0]
    .groupby("DEV_NAME")["API_WELL_NUMBER"]
    .nunique()
    .reset_index(name="PRODUCER_WELLS")
)

# Summary base
oil_volume = final_df.groupby("DEV_NAME")["MONTHLY_OIL_VOLUME"].sum().reset_index(name="TOTAL OIL BBL")
summary_df = oil_volume.merge(total_wells, on="DEV_NAME", how="left")
summary_df = summary_df.merge(producer_wells, on="DEV_NAME", how="left").fillna({"PRODUCER_WELLS": 0})
summary_df = summary_df.merge(final_df[["DEV_NAME", "DEV_SYSTEM"]].drop_duplicates("DEV_NAME"), on="DEV_NAME", how="left")
summary_df = summary_df.merge(fo_months, on="DEV_NAME", how="left")

summary_df["DEV_SYSTEM"] = summary_df["DEV_SYSTEM"].astype(str)
assumptions["DEV_SYSTEM"] = assumptions["DEV_SYSTEM"].astype(str)
summary_df = summary_df.merge(assumptions, on="DEV_SYSTEM", how="left")

# Injector wells based on policy
summary_df["Injectors_Per_Producer"] = pd.to_numeric(summary_df.get("Injectors_Per_Producer", 0.0), errors="coerce").fillna(0.0)
summary_df["INJECTOR_WELLS"] = (summary_df["PRODUCER_WELLS"] * summary_df["Injectors_Per_Producer"]).astype(float).apply(math.floor)

# ----------------------------- Rig rate logic -----------------------------
def get_rate(sys_name, col):
    m = assumptions["DEV_SYSTEM"] == sys_name
    if m.any() and col in assumptions.columns:
        v = assumptions.loc[m, col].iloc[0]
        return float(v) if pd.notna(v) else 0.0
    return 0.0

rate_subsea15 = get_rate("subsea15", "MODU_LOADED_DAYRATE_MM")
rate_subsea20 = get_rate("subsea20", "MODU_LOADED_DAYRATE_MM")
rate_dry      = get_rate("dry",      "DRY_TREE_RIG_RATE_MM")

def rig_rate_for(dev_system, month, fo_date, is_completion):
    post = pd.notna(fo_date) and (month >= month_floor(fo_date))
    ds = str(dev_system or "")
    if ds == "subsea15":
        return rate_subsea15
    if ds == "subsea20":
        return rate_subsea20 if (post or is_completion) else rate_subsea15
    if ds == "dry":
        return rate_dry if post else rate_subsea15
    if ds.startswith("tieback"):
        return rate_subsea20 if is_completion else rate_subsea15
    return rate_subsea15

# ----------------------------- Rollup prep -----------------------------
rollup_cols = [
    "Host_CAPEX_USD","SURF_USD","Dry_Well_System_USD","Pump_Package_USD","Water_Injection_Facility_USD",
    "DRILLING_COST_USD","COMPLETION_COST_USD","DnC_Total_USD","DnC_PreFO_USD","DnC_PostFO_USD",
    "DnC_Intangible_USD","DnC_Tangible_USD","Tax_Shield_DnC_USD","After_Tax_DnC_USD",
    "Revenue_USD","Royalty_USD","Variable_OPEX_USD","Fixed_OPEX_USD","Facilities_USD",
    "Net_CashFlow_USD","PV_CashFlow_USD"
]
for col in rollup_cols + ["NPV_USD","MIRR_monthly","MIRR_annual","Final_Pump_Count"]:
    summary_df[col] = 0.0

# Pre-aggregates for speed
prod_monthly = final_df.groupby(["DEV_NAME", "MONTH"])["MONTHLY_OIL_VOLUME"].sum().reset_index()
dnc_monthly = final_df.groupby(["DEV_NAME", "MONTH"])[["DRILLING_DAYS","COMPLETION_DAYS"]].sum().reset_index()

dev_sheets = {}

# ----------------------------- Per-DEV monthly engine -----------------------------
for dev in summary_df["DEV_NAME"].dropna().unique():
    # Gather DEV-specific assumptions
    dev_system_series = summary_df.loc[summary_df["DEV_NAME"] == dev, "DEV_SYSTEM"].dropna()
    if dev_system_series.empty:
        print(f"⚠️ Skipping {dev} — missing DEV_SYSTEM")
        continue
    dev_system = dev_system_series.iloc[0]

    arow = assumptions[assumptions["DEV_SYSTEM"] == dev_system]
    if arow.empty:
        print(f"⚠️ Skipping {dev} — no assumptions for DEV_SYSTEM={dev_system}")
        continue
    arow = arow.iloc[0]

    host_capex_mm        = safe_num(arow.get("Host_CAPEX_MM", 0.0))
    host_prefo_months    = int(safe_num(arow.get("Host_PreFO_Months", 0.0)))
    surf_per_well_mm     = safe_num(arow.get("SURF_per_well_MM", 0.0))
    surf_prefo_months    = int(safe_num(arow.get("SURF_PreFO_Months", 0.0)))
    dry_well_sys_mm_each = safe_num(arow.get("Dry_Well_System_Per_Producer_USD", 0.0))  # values in file look like MM by note -> treat as MM
    dry_prefo_months     = int(safe_num(arow.get("DRY_Well_Systems_PreFO_Months", 0.0)))
    pump_pkg_per7_mm     = safe_num(arow.get("Pump_pkg_per_7_wells_MM", 0.0))
    pump_policy          = int(safe_num(arow.get("Pump_Policy per Producer Capped at a Total of 2", 7)))
    pump_pre_well_months = int(safe_num(arow.get("PUMP_Months_Pre_Well", 0.0)))
    water_inj_fac_mm     = safe_num(arow.get("Water_Injection_Facility_Cost_MM", 0.0))

    wti                  = safe_num(arow.get("WTI_base_$/bbl", 0.0))
    var_opex_per_bbl     = safe_num(arow.get("Variable_OPEX_$/bbl", 0.0))
    fixed_opex_mm_per_year = safe_num(arow.get("Fixed_OPEX_MM_per_year", 0.0))
    royalty_rate         = safe_num(arow.get("Royalty_Rate", 0.0))
    royalty_basis_mm_bbl = safe_num(arow.get("Royalty_Basis", 0.0))

    discount_rate_annual = safe_num(arow.get("Discount_rate_annual", 0.0))
    mirr_reinvest_annual = safe_num(arow.get("MIRR_Reinvest_Rate_annual", 0.0))
    mirr_finance_annual  = safe_num(arow.get("MIRR_Finance_Rate_annual", 0.0))
    corp_tax_rate        = safe_num(arow.get("Corporate_Tax_Rate", 0.0))
    dnc_int_frac         = safe_num(arow.get("DnC_Intangible_Fraction", 0.7))
    dnc_tang_years       = int(safe_num(arow.get("DnC_Tangible_Depreciation_Years", 7)))
    dep_months           = max(1, dnc_tang_years * 12)

    # Monthly index for this DEV from global_start to global_end
    idx = pd.DataFrame({"MONTH": pd.date_range(global_start, global_end, freq="MS")})

    # Merge production and D&C
    pm = prod_monthly[prod_monthly["DEV_NAME"] == dev][["MONTH","MONTHLY_OIL_VOLUME"]]
    dn = dnc_monthly[dnc_monthly["DEV_NAME"] == dev][["MONTH","DRILLING_DAYS","COMPLETION_DAYS"]]
    monthly = idx.merge(pm, on="MONTH", how="left").merge(dn, on="MONTH", how="left")
    monthly[["MONTHLY_OIL_VOLUME","DRILLING_DAYS","COMPLETION_DAYS"]] = monthly[["MONTHLY_OIL_VOLUME","DRILLING_DAYS","COMPLETION_DAYS"]].fillna(0.0)

    if monthly.empty:
        print(f"⚠️ Skipping {dev} — no monthly data after merge")
        continue

    # FO date
    fo_row = fo_months[fo_months["DEV_NAME"] == dev]
    fo_date = fo_row["FO_Month"].iloc[0] if not fo_row.empty else pd.NaT

    # New producers per month (first oil by API)
    dev_data = final_df[final_df["DEV_NAME"] == dev].copy()
    fopw = (
        dev_data[dev_data["MONTHLY_OIL_VOLUME"] > 0]
        .sort_values(["API_WELL_NUMBER", "MONTH"])
        .groupby("API_WELL_NUMBER")["MONTH"].min()
        .reset_index().rename(columns={"MONTH": "FIRST_OIL_MONTH"})
    )
    new_prod_counts = fopw.groupby("FIRST_OIL_MONTH").size().rename("NEW_PRODUCERS").reset_index()
    monthly = monthly.merge(new_prod_counts, left_on="MONTH", right_on="FIRST_OIL_MONTH", how="left").drop(columns=["FIRST_OIL_MONTH"])
    monthly["NEW_PRODUCERS"] = monthly["NEW_PRODUCERS"].fillna(0).astype(int)
    monthly["CUM_PRODUCERS"] = monthly["NEW_PRODUCERS"].cumsum()

    # Rig rates (MM USD/day)
    monthly["DRILL_RATE_MM"] = monthly["MONTH"].apply(lambda m: rig_rate_for(dev_system, m, fo_date, False))
    monthly["COMP_RATE_MM"]  = monthly["MONTH"].apply(lambda m: rig_rate_for(dev_system, m, fo_date, True))

    # D&C costs
    monthly["DRILLING_COST_USD"]   = monthly["DRILLING_DAYS"]   * monthly["DRILL_RATE_MM"] * 1_000_000.0
    monthly["COMPLETION_COST_USD"] = monthly["COMPLETION_DAYS"] * monthly["COMP_RATE_MM"]  * 1_000_000.0
    monthly["DnC_Total_USD"]       = monthly["DRILLING_COST_USD"] + monthly["COMPLETION_COST_USD"]

    # Pre/Post FO split
    monthly["IS_PRE_FO"] = pd.notna(fo_date) & (monthly["MONTH"] < month_floor(fo_date))
    monthly["DnC_PreFO_USD"]  = monthly["DnC_Total_USD"].where(monthly["IS_PRE_FO"], 0.0)
    monthly["DnC_PostFO_USD"] = monthly["DnC_Total_USD"].where(~monthly["IS_PRE_FO"], 0.0)

    # D&C tax shields (approximate straight-line on tangible)
    monthly["DnC_Intangible_USD"] = monthly["DnC_Total_USD"] * dnc_int_frac
    monthly["DnC_Tangible_USD"]   = monthly["DnC_Total_USD"] * (1.0 - dnc_int_frac)
    # Approximate monthly tangible depreciation with rolling equal spread
    monthly["DnC_Tangible_Dep_Expense_USD"] = (
        monthly["DnC_Tangible_USD"].rolling(window=dep_months, min_periods=1).sum() / dep_months
    )
    monthly["Tax_Shield_Intangible_USD"] = monthly["DnC_Intangible_USD"] * corp_tax_rate
    monthly["Tax_Shield_Tangible_USD"]   = monthly["DnC_Tangible_Dep_Expense_USD"] * corp_tax_rate
    monthly["Tax_Shield_DnC_USD"]        = monthly["Tax_Shield_Intangible_USD"] + monthly["Tax_Shield_Tangible_USD"]
    monthly["After_Tax_DnC_USD"]         = monthly["DnC_Total_USD"] - monthly["Tax_Shield_DnC_USD"]

    # Facilities phasing
    ds = str(dev_system or "")

    # Host CAPEX: spread evenly over last N months before FO (tiebacks => 0)
    monthly["Host_CAPEX_USD"] = 0.0
    hc_mm = 0.0 if ds.startswith("tieback") else host_capex_mm
    if pd.notna(fo_date) and host_prefo_months > 0 and hc_mm > 0:
        start_m = month_floor(fo_date) - pd.DateOffset(months=int(host_prefo_months))
        mask = (monthly["MONTH"] >= start_m) & (monthly["MONTH"] < month_floor(fo_date))
        monthly.loc[mask, "Host_CAPEX_USD"] = (hc_mm * 1_000_000.0) / host_prefo_months

    # SURF: spread total SURF (per new producer) across pre-FO months (dry => 0)
    monthly["SURF_USD"] = 0.0
    if ds != "dry" and surf_prefo_months > 0 and surf_per_well_mm > 0 and pd.notna(fo_date):
        total_surf = monthly["NEW_PRODUCERS"].sum() * surf_per_well_mm * 1_000_000.0
        start_m = month_floor(fo_date) - pd.DateOffset(months=int(surf_prefo_months))
        mask = (monthly["MONTH"] >= start_m) & (monthly["MONTH"] < month_floor(fo_date))
        monthly.loc[mask, "SURF_USD"] = total_surf / surf_prefo_months

    # Dry Well Systems: spread per-producer system cost across pre-FO (dry only)
    monthly["Dry_Well_System_USD"] = 0.0
    if ds == "dry" and dry_prefo_months > 0 and dry_well_sys_mm_each > 0 and pd.notna(fo_date):
        total_dry = monthly["NEW_PRODUCERS"].sum() * dry_well_sys_mm_each * 1_000_000.0
        start_m = month_floor(fo_date) - pd.DateOffset(months=int(dry_prefo_months))
        mask = (monthly["MONTH"] >= start_m) & (monthly["MONTH"] < month_floor(fo_date))
        monthly.loc[mask, "Dry_Well_System_USD"] = total_dry / dry_prefo_months

    # Pumps: policy-based requirement and pre-well phasing of each package
    # Requirement — tiebacks => 1 from FO; else floor(CUM_PRODUCERS / policy) capped at 2
    if ds.startswith("tieback"):
        monthly["PUMP_COUNT_REQUIRED"] = np.where(pd.notna(fo_date) & (monthly["MONTH"] >= month_floor(fo_date)), 1, 0)
    else:
        pol = max(1, pump_policy)
        monthly["PUMP_COUNT_REQUIRED"] = (monthly["CUM_PRODUCERS"] // pol).clip(upper=2)

    monthly["PUMP_COUNT_DELTA"] = monthly["PUMP_COUNT_REQUIRED"].diff().fillna(monthly["PUMP_COUNT_REQUIRED"]).clip(lower=0).astype(int)

    monthly["Pump_Package_USD"] = 0.0
    if pump_pkg_per7_mm > 0 and pump_pre_well_months > 0:
        pump_cost = pump_pkg_per7_mm * 1_000_000.0
        for i, row in monthly.iterrows():
            delta = int(row.get("PUMP_COUNT_DELTA", 0))
            if delta > 0:
                trigger_m = row["MONTH"]
                start_m = trigger_m - pd.DateOffset(months=int(pump_pre_well_months))
                mask = (monthly["MONTH"] >= start_m) & (monthly["MONTH"] < trigger_m)
                # phase equally over pre-well months
                monthly.loc[mask, "Pump_Package_USD"] += (pump_cost * delta) / pump_pre_well_months

    # Water injection facility at FO
    monthly["Water_Injection_Facility_USD"] = 0.0
    if pd.notna(fo_date) and water_inj_fac_mm > 0:
        monthly.loc[monthly["MONTH"] == month_floor(fo_date), "Water_Injection_Facility_USD"] = water_inj_fac_mm * 1_000_000.0

    # Revenue, royalty, OPEX
    monthly["Revenue_USD"] = monthly["MONTHLY_OIL_VOLUME"] * wti
    monthly["CUM_OIL_BBL"] = monthly["MONTHLY_OIL_VOLUME"].cumsum()
    royalty_threshold_bbl = royalty_basis_mm_bbl * 1_000_000.0
    monthly["Royalty_USD"] = np.where(monthly["CUM_OIL_BBL"] > royalty_threshold_bbl, monthly["Revenue_USD"] * royalty_rate, 0.0)
    monthly["Variable_OPEX_USD"] = monthly["MONTHLY_OIL_VOLUME"] * var_opex_per_bbl

    # Fixed OPEX from FO onward (if FO unknown, none)
    monthly["Fixed_OPEX_USD"] = 0.0
    if fixed_opex_mm_per_year > 0 and pd.notna(fo_date):
        mask = monthly["MONTH"] >= month_floor(fo_date)
        monthly.loc[mask, "Fixed_OPEX_USD"] = (fixed_opex_mm_per_year * 1_000_000.0) / 12.0

    # Facilities rollup
    monthly["Facilities_USD"] = (
        monthly["Host_CAPEX_USD"] + monthly["SURF_USD"] +
        monthly["Pump_Package_USD"] + monthly["Dry_Well_System_USD"] +
        monthly["Water_Injection_Facility_USD"]
    )

    # Net cash flow (apply D&C tax shields)
    monthly["Net_CashFlow_USD"] = (
        monthly["Revenue_USD"]
        - monthly["Royalty_USD"]
        - monthly["Variable_OPEX_USD"]
        - monthly["Fixed_OPEX_USD"]
        - monthly["Facilities_USD"]
        - monthly["DnC_Total_USD"]
        + monthly["Tax_Shield_DnC_USD"]
    )

    # Discounting and PV
    r_m = (1.0 + discount_rate_annual) ** (1.0 / 12.0) - 1.0
    monthly = monthly.reset_index(drop=True)
    monthly["t"] = monthly.index.astype(float)
    monthly["Disc_Factor"] = (1.0 + r_m) ** monthly["t"]
    monthly["PV_CashFlow_USD"] = np.where(monthly["Disc_Factor"] != 0, monthly["Net_CashFlow_USD"] / monthly["Disc_Factor"], 0.0)

    # MIRR (monthly)
    n = len(monthly)
    mirr_m = 0.0
    if n > 0:
        fin_m = (1.0 + mirr_finance_annual) ** (1.0 / 12.0) - 1.0
        reinv_m = (1.0 + mirr_reinvest_annual) ** (1.0 / 12.0) - 1.0
        cf = monthly["Net_CashFlow_USD"].values.astype(float)
        pv_neg = 0.0
        fv_pos = 0.0
        for i, c in enumerate(cf):
            if c < 0:
                pv_neg += c / ((1.0 + fin_m) ** i)
            elif c > 0:
                fv_pos += c * ((1.0 + reinv_m) ** (n - i - 1))
        if pv_neg < 0 and fv_pos > 0:
            mirr_m = (fv_pos / (-pv_neg)) ** (1.0 / n) - 1.0

    # Roll-up to summary
    sums = monthly[[
        "Host_CAPEX_USD","SURF_USD","Dry_Well_System_USD","Pump_Package_USD","Water_Injection_Facility_USD",
        "DRILLING_COST_USD","COMPLETION_COST_USD","DnC_Total_USD","DnC_PreFO_USD","DnC_PostFO_USD",
        "DnC_Intangible_USD","DnC_Tangible_USD","Tax_Shield_DnC_USD","After_Tax_DnC_USD",
        "Revenue_USD","Royalty_USD","Variable_OPEX_USD","Fixed_OPEX_USD","Facilities_USD",
        "Net_CashFlow_USD","PV_CashFlow_USD"
    ]].sum(numeric_only=True)

    for col in rollup_cols:
        summary_df.loc[summary_df["DEV_NAME"] == dev, col] = float(sums.get(col, 0.0))

    summary_df.loc[summary_df["DEV_NAME"] == dev, "NPV_USD"] = monthly["PV_CashFlow_USD"].sum()
    summary_df.loc[summary_df["DEV_NAME"] == dev, "MIRR_monthly"] = mirr_m
    summary_df.loc[summary_df["DEV_NAME"] == dev, "MIRR_annual"] = ((1.0 + mirr_m) ** 12.0) - 1.0
    summary_df.loc[summary_df["DEV_NAME"] == dev, "Final_Pump_Count"] = monthly["PUMP_COUNT_REQUIRED"].max() if "PUMP_COUNT_REQUIRED" in monthly.columns else 0

    # Build monthly output sheet
    monthly_out = monthly[[
        "MONTH","MONTHLY_OIL_VOLUME",
        "DRILLING_DAYS","DRILL_RATE_MM","DRILLING_COST_USD",
        "COMPLETION_DAYS","COMP_RATE_MM","COMPLETION_COST_USD",
        "DnC_Total_USD","DnC_PreFO_USD","DnC_PostFO_USD",
        "DnC_Intangible_USD","DnC_Tangible_USD","Tax_Shield_DnC_USD","After_Tax_DnC_USD",
        "NEW_PRODUCERS","CUM_PRODUCERS",
        "Host_CAPEX_USD","SURF_USD","Dry_Well_System_USD","Pump_Package_USD","Water_Injection_Facility_USD","Facilities_USD",
        "Revenue_USD","Royalty_USD","Variable_OPEX_USD","Fixed_OPEX_USD",
        "Net_CashFlow_USD","Disc_Factor","PV_CashFlow_USD"
    ]].copy()

    dev_sheets[str(dev)] = monthly_out

# ----------------------------- Finalize summary and Excel output -----------------------------
summary_df["FO Month"] = summary_df["FO_Month"].apply(month_str)

summary_df["Facilities Cost USD"] = (
    summary_df["Host_CAPEX_USD"] + summary_df["SURF_USD"] +
    summary_df["Pump_Package_USD"] + summary_df["Dry_Well_System_USD"]
)

summary_cols = [
    "DEV_NAME","DEV_SYSTEM","FO Month","TOTAL OIL BBL",
    "Host_CAPEX_USD","SURF_USD","Pump_Package_USD","Dry_Well_System_USD","Facilities Cost USD",
    "DRILLING_COST_USD","COMPLETION_COST_USD","DnC_Total_USD","DnC_PreFO_USD","DnC_PostFO_USD",
    "DnC_Intangible_USD","DnC_Tangible_USD","Tax_Shield_DnC_USD","After_Tax_DnC_USD",
    "Revenue_USD","Royalty_USD","Variable_OPEX_USD","Fixed_OPEX_USD",
    "Net_CashFlow_USD","NPV_USD","MIRR_monthly","MIRR_annual",
    "PRODUCER_WELLS","INJECTOR_WELLS","TOTAL_WELLS","Final_Pump_Count"
]

summary_out = summary_df[summary_cols].copy()
summary_out.rename(columns={"DEV_NAME": "Project Name"}, inplace=True)

with pd.ExcelWriter("financial_project_summary.xlsx", engine="xlsxwriter") as writer:
    summary_out.to_excel(writer, sheet_name="Project_Summary", index=False)
    # Write DEV_NAME sheets
    sheet_names = []
    for dev_name, df_monthly in dev_sheets.items():
        sname = str(dev_name)[:31] if dev_name else "DEV"
        sheet_names.append(sname)
        df_monthly.to_excel(writer, sheet_name=sname, index=False)

print(f"✅ Financial workbook created: financial_project_summary.xlsx")
print(f"✅ DEV_NAME sheets generated: {len(dev_sheets)} -> {list(dev_sheets.keys())}")
