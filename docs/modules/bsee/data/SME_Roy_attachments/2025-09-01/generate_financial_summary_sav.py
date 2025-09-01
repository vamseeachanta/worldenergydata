import pandas as pd
import numpy as np
import math

# ---------- Load and clean data ----------
final_df = pd.read_excel("chronological_lease_analysis.xlsx")

# Rename columns to match expected names
final_df.rename(columns={
    "ALLOCATED_DRILLING_DAYS": "DRILLING_DAYS",
    "ALLOCATED_COMPLETION_DAYS": "COMPLETION_DAYS"
}, inplace=True)

dev_map = pd.read_excel("leases.xlsx")[["LEASE_NAME", "DEV_NAME", "DEV_SYSTEM"]].drop_duplicates()
assumptions_raw = pd.read_csv("lease_assumptions.csv", index_col=0)

# Merge DEV_NAME and DEV_SYSTEM
final_df = final_df.merge(dev_map, on="LEASE_NAME", how="left")

# Standardize types
final_df["MONTH"] = pd.to_datetime(final_df["MONTH"], errors="coerce")
for col in ["MONTHLY_OIL_VOLUME", "DRILLING_DAYS", "COMPLETION_DAYS"]:
    final_df[col] = pd.to_numeric(final_df[col], errors="coerce").fillna(0.0)
# ---------- FO month per DEV_NAME ----------
fo_months = (
    final_df[final_df["MONTHLY_OIL_VOLUME"] > 0]
    .groupby("DEV_NAME")["MONTH"]
    .min()
    .reset_index()
    .rename(columns={"MONTH": "FO_Month"})
)

# ---------- Well counts ----------
total_wells = final_df.groupby("DEV_NAME")["API_WELL_NUMBER"].nunique().reset_index(name="TOTAL_WELLS")
producer_wells = (
    final_df[final_df["MONTHLY_OIL_VOLUME"] > 0]
    .groupby("DEV_NAME")["API_WELL_NUMBER"].nunique()
    .reset_index(name="PRODUCER_WELLS")
)
well_counts = pd.merge(total_wells, producer_wells, on="DEV_NAME", how="left").fillna({"PRODUCER_WELLS": 0})
well_counts["PRODUCER_WELLS"] = well_counts["PRODUCER_WELLS"].astype(int)
well_counts["TOTAL_WELLS"] = well_counts["TOTAL_WELLS"].astype(int)

# ---------- Aggregate production for summary ----------
oil_volume = final_df.groupby("DEV_NAME")["MONTHLY_OIL_VOLUME"].sum().reset_index(name="TOTAL OIL BBL")
oil_volume["TOTAL OIL BBL"] = pd.to_numeric(oil_volume["TOTAL OIL BBL"], errors="coerce").fillna(0.0)

# ---------- Build summary base ----------
summary_df = oil_volume.merge(well_counts, on="DEV_NAME", how="left")
summary_df = summary_df.merge(
    final_df[["DEV_NAME", "DEV_SYSTEM"]].drop_duplicates("DEV_NAME"),
    on="DEV_NAME", how="left"
)
summary_df = summary_df.merge(fo_months, on="DEV_NAME", how="left")

# ---------- Transpose and clean assumptions ----------
assumptions = assumptions_raw.transpose()
assumptions.index.name = "DEV_SYSTEM"
assumptions.reset_index(inplace=True)

# Ensure DEV_SYSTEM is a string on both sides before merging
summary_df["DEV_SYSTEM"] = summary_df["DEV_SYSTEM"].astype(str)
assumptions["DEV_SYSTEM"] = assumptions["DEV_SYSTEM"].astype(str)

# Coerce only numeric assumption fields (exclude DEV_SYSTEM)
numeric_cols = [c for c in assumptions.columns if c != "DEV_SYSTEM"]
for c in numeric_cols:
    assumptions[c] = pd.to_numeric(assumptions[c], errors="coerce")

# Merge assumptions into summary
summary_df = summary_df.merge(assumptions, on="DEV_SYSTEM", how="left")

# ---------- Helper: safe bool ----------
def to_bool(x):
    s = str(x).strip().upper()
    return True if s == "TRUE" else False

# ---------- Helper: cross-system rate lookup ----------
def get_rate(sys_name, col):
    mask = assumptions["DEV_SYSTEM"] == sys_name
    if mask.any() and col in assumptions.columns:
        v = assumptions.loc[mask, col].iloc[0]
        return float(v) if pd.notna(v) else 0.0
    return 0.0

rate_subsea15_modu = get_rate("subsea15", "MODU_LOADED_DAYRATE_MM")
rate_subsea20_modu = get_rate("subsea20", "MODU_LOADED_DAYRATE_MM")
rate_dry_tree = get_rate("dry", "DRY_TREE_RIG_RATE_MM")

# ---------- Rig rate selection per month ----------
def rig_rate_for(dev_system, month, fo_date, is_completion):
    post = (pd.notna(fo_date) and month >= fo_date)
    pre = (pd.notna(fo_date) and month < fo_date)
    ds = str(dev_system or "")
    if ds == "subsea15":
        return rate_subsea15_modu
    if ds == "subsea20":
        if pre:
            return rate_subsea20_modu if is_completion else rate_subsea15_modu
        if post:
            return rate_subsea20_modu
        return rate_subsea15_modu
    if ds == "dry":
        return rate_dry_tree if post else rate_subsea15_modu
    if ds == "tieback15":
        return rate_subsea15_modu
    if ds == "tieback20":
        return rate_subsea20_modu if is_completion else rate_subsea15_modu
    return rate_subsea15_modu

# ---------- Initialize rollup columns ----------
rollup_cols = [
    "Host_CAPEX_USD","SURF_USD","Dry_Well_System_USD","Pump_Package_USD","Water_Injection_Facility_USD",
    "DRILLING_COST_USD","COMPLETION_COST_USD","DnC_Total_USD","DnC_PreFO_USD","DnC_PostFO_USD",
    "DnC_Intangible_USD","DnC_Tangible_USD","DnC_Tangible_Dep_Expense_USD","Tax_Shield_DnC_USD","After_Tax_DnC_USD",
    "Revenue_USD","Royalty_USD","Variable_OPEX_USD","Fixed_OPEX_USD","Facilities_USD",
    "Net_CashFlow_USD","PV_CashFlow_USD"
]
for c in rollup_cols + ["NPV_USD","MIRR_monthly","MIRR_annual","Final_Pump_Count"]:
    summary_df[c] = 0.0

# ---------- Container for per-DEV sheets ----------
dev_sheets = {}
# ---------- Per-DEV monthly scheduling and rollups ----------
for dev in summary_df["DEV_NAME"]:
    dev_data = final_df[final_df["DEV_NAME"] == dev].copy()
    if dev_data.empty:
        continue

    dev_system = dev_data["DEV_SYSTEM"].dropna().iloc[0] if not dev_data["DEV_SYSTEM"].dropna().empty else None

    # Assumptions row for this system
    arow = assumptions[assumptions["DEV_SYSTEM"] == str(dev_system)]
    arow = arow.iloc[0] if not arow.empty else pd.Series()

    host_capex_mm = float(arow.get("Host_CAPEX_MM", 0) or 0.0)
    host_prefo_months = int(float(arow.get("Host_PreFO_Months", 0) or 0.0))
    surf_per_well_mm = float(arow.get("SURF_per_well_MM", 0) or 0.0)
    dry_well_sys_mm = float(arow.get("Dry_Well_System_Per_Producer_USD", 0) or 0.0)
    pump_pkg_per7_mm = float(arow.get("Pump_pkg_per_7_wells_MM", 0) or 0.0)
    pump_policy = int(float(arow.get("Pump_Policy per Producer Capped at a Total of 2", 7) or 7))
    water_inj_fac_mm = float(arow.get("Water_Injection_Facility_Cost_MM", 0) or 0.0)

    wti = float(arow.get("WTI_base_$/bbl", 0) or 0.0)
    var_opex_per_bbl = float(arow.get("Variable_OPEX_$/bbl", 0) or 0.0)
    fixed_opex_mm_per_year = float(arow.get("Fixed_OPEX_MM_per_year", 0) or 0.0)
    royalty_rate = float(arow.get("Royalty_Rate", 0) or 0.0)
    royalty_basis_mm_bbl = float(arow.get("Royalty_Basis", 0) or 0.0)
    discount_rate_annual = float(arow.get("Discount_rate_annual", 0) or 0.0)
    mirr_reinvest_annual = float(arow.get("MIRR_Reinvest_Rate_annual", 0) or 0.0)
    mirr_finance_annual = float(arow.get("MIRR_Finance_Rate_annual", 0) or 0.0)
    corp_tax_rate = float(arow.get("Corporate_Tax_Rate", 0.0) or 0.0)
    dnc_int_frac = float(arow.get("DnC_Intangible_Fraction", 0.7) if pd.notna(arow.get("DnC_Intangible_Fraction", np.nan)) else 0.7)
    dnc_tang_years = int(float(arow.get("DnC_Tangible_Depreciation_Years", 7) if pd.notna(arow.get("DnC_Tangible_Depreciation_Years", np.nan)) else 7))
    dep_months = max(1, dnc_tang_years * 12)

    # FO month for this dev
    fo_row = fo_months[fo_months["DEV_NAME"] == dev]
    fo_date = fo_row["FO_Month"].iloc[0] if not fo_row.empty else pd.NaT

    # First oil per well to count new producers
    first_oil_per_well = (
        dev_data[dev_data["MONTHLY_OIL_VOLUME"] > 0]
        .sort_values(["API_WELL_NUMBER", "MONTH"])
        .groupby("API_WELL_NUMBER")["MONTH"]
        .min()
        .reset_index()
        .rename(columns={"MONTH": "FIRST_OIL_MONTH"})
    )
    dev_data = dev_data.merge(first_oil_per_well, on="API_WELL_NUMBER", how="left")

    # Monthly aggregate across all wells
    monthly = (
        dev_data.groupby("MONTH")
        .agg({
            "MONTHLY_OIL_VOLUME": "sum",
            "DRILLING_DAYS": "sum",
            "COMPLETION_DAYS": "sum"
        })
        .reset_index()
        .sort_values("MONTH")
    )

    # New producers per month
    new_prod_counts = first_oil_per_well.groupby("FIRST_OIL_MONTH").size().rename("NEW_PRODUCERS").reset_index()
    monthly = monthly.merge(new_prod_counts, left_on="MONTH", right_on="FIRST_OIL_MONTH", how="left")
    monthly.drop(columns=["FIRST_OIL_MONTH"], inplace=True)
    monthly["NEW_PRODUCERS"] = monthly["NEW_PRODUCERS"].fillna(0).astype(int)
    monthly["CUM_PRODUCERS"] = monthly["NEW_PRODUCERS"].cumsum()

    # Rig rates (MM USD/day)
    monthly["DRILL_RATE_MM"] = monthly["MONTH"].apply(lambda m: rig_rate_for(dev_system, m, fo_date, is_completion=False))
    monthly["COMP_RATE_MM"] = monthly["MONTH"].apply(lambda m: rig_rate_for(dev_system, m, fo_date, is_completion=True))

    # D&C costs (USD)
    monthly["DRILLING_COST_USD"] = monthly["DRILLING_DAYS"] * monthly["DRILL_RATE_MM"] * 1_000_000.0
    monthly["COMPLETION_COST_USD"] = monthly["COMPLETION_DAYS"] * monthly["COMP_RATE_MM"] * 1_000_000.0
    monthly["DnC_Total_USD"] = monthly["DRILLING_COST_USD"] + monthly["COMPLETION_COST_USD"]

    # Pre/Post FO split for QA
    monthly["IS_PRE_FO"] = pd.notna(fo_date) & (monthly["MONTH"] < fo_date)
    monthly["DnC_PreFO_USD"] = monthly["DnC_Total_USD"].where(monthly["IS_PRE_FO"], 0.0)
    monthly["DnC_PostFO_USD"] = monthly["DnC_Total_USD"].where(~monthly["IS_PRE_FO"], 0.0)

    # DnC tax treatment (70% intangible immediate, 30% tangible straight-line)
    monthly["DnC_Intangible_USD"] = monthly["DnC_Total_USD"] * dnc_int_frac
    monthly["DnC_Tangible_USD"] = monthly["DnC_Total_USD"] * (1.0 - dnc_int_frac)
    monthly["DnC_Tangible_Dep_Expense_USD"] = (
        monthly["DnC_Tangible_USD"].rolling(window=dep_months, min_periods=1).sum() / dep_months
    )
    monthly["Tax_Shield_Intangible_USD"] = monthly["DnC_Intangible_USD"] * corp_tax_rate
    monthly["Tax_Shield_Tangible_USD"] = monthly["DnC_Tangible_Dep_Expense_USD"] * corp_tax_rate
    monthly["Tax_Shield_DnC_USD"] = monthly["Tax_Shield_Intangible_USD"] + monthly["Tax_Shield_Tangible_USD"]
    monthly["After_Tax_DnC_USD"] = monthly["DnC_Total_USD"] - monthly["Tax_Shield_DnC_USD"]

    # Host CAPEX: spread evenly over last N months before FO (tiebacks => 0)
    monthly["Host_CAPEX_USD"] = 0.0
    if isinstance(dev_system, str) and dev_system.startswith("tieback"):
        host_capex_mm = 0.0
    if pd.notna(fo_date) and host_prefo_months > 0 and host_capex_mm > 0:
        start_month = fo_date - pd.DateOffset(months=host_prefo_months)
        mask = (monthly["MONTH"] >= start_month) & (monthly["MONTH"] < fo_date)
        mcount = int(mask.sum())
        allocation = (host_capex_mm * 1_000_000.0) / mcount if mcount > 0 else 0.0
        monthly.loc[mask, "Host_CAPEX_USD"] = allocation

    # SURF per new producer (dry => 0)
    monthly["SURF_USD"] = monthly["NEW_PRODUCERS"] * (surf_per_well_mm * 1_000_000.0)
    if dev_system == "dry":
        monthly["SURF_USD"] = 0.0

    # Dry well system per new producer (only for dry if assumptions specify)
    monthly["Dry_Well_System_USD"] = monthly["NEW_PRODUCERS"] * (dry_well_sys_mm * 1_000_000.0)

    # Pump packages
    monthly["PUMP_COUNT_REQUIRED"] = 0
    ds = str(dev_system or "")
    if ds.startswith("tieback"):
        monthly["PUMP_COUNT_REQUIRED"] = np.where(pd.notna(fo_date) & (monthly["MONTH"] >= fo_date), 1, 0)
    else:
        pol = pump_policy if pump_policy and pump_policy > 0 else 7
        monthly["PUMP_COUNT_REQUIRED"] = (monthly["CUM_PRODUCERS"] // pol).clip(upper=2)
    monthly["PUMP_COUNT_DELTA"] = monthly["PUMP_COUNT_REQUIRED"].diff().fillna(monthly["PUMP_COUNT_REQUIRED"])
    monthly["PUMP_COUNT_DELTA"] = monthly["PUMP_COUNT_DELTA"].clip(lower=0).astype(int)
    monthly["Pump_Package_USD"] = monthly["PUMP_COUNT_DELTA"] * (pump_pkg_per7_mm * 1_000_000.0)
    if dev_system == "dry":
        monthly["Pump_Package_USD"] = 0.0

    # Water injection facility at FO
    monthly["Water_Injection_Facility_USD"] = 0.0
    if pd.notna(fo_date) and water_inj_fac_mm > 0:
        monthly.loc[monthly["MONTH"] == fo_date, "Water_Injection_Facility_USD"] = water_inj_fac_mm * 1_000_000.0

    # Revenue, royalty, OPEX
    monthly["Revenue_USD"] = monthly["MONTHLY_OIL_VOLUME"] * wti
    monthly["CUM_OIL_BBL"] = monthly["MONTHLY_OIL_VOLUME"].cumsum()
    royalty_threshold_bbl = royalty_basis_mm_bbl * 1_000_000.0
    monthly["Royalty_USD"] = np.where(
        monthly["CUM_OIL_BBL"] > royalty_threshold_bbl,
        monthly["Revenue_USD"] * royalty_rate,
        0.0
    )
    monthly["Variable_OPEX_USD"] = monthly["MONTHLY_OIL_VOLUME"] * var_opex_per_bbl

    monthly["Fixed_OPEX_USD"] = 0.0
    if fixed_opex_mm_per_year > 0:
        start = fo_date if pd.notna(fo_date) else (monthly["MONTH"].min() if not monthly.empty else pd.NaT)
        monthly.loc[monthly["MONTH"] >= start, "Fixed_OPEX_USD"] = (fixed_opex_mm_per_year * 1_000_000.0) / 12.0

    # Facilities rollup
    monthly["Facilities_USD"] = (
        monthly["Host_CAPEX_USD"] + monthly["SURF_USD"] + monthly["Pump_Package_USD"] + monthly["Dry_Well_System_USD"]
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
    monthly["PV_CashFlow_USD"] = np.where(
        monthly["Disc_Factor"] != 0, monthly["Net_CashFlow_USD"] / monthly["Disc_Factor"], 0.0
    )

    # MIRR (monthly)
    n = len(monthly)
    mirr_m = np.nan
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

    # Roll-up
    sums = monthly[[
        "Host_CAPEX_USD","SURF_USD","Dry_Well_System_USD","Pump_Package_USD","Water_Injection_Facility_USD",
        "DRILLING_COST_USD","COMPLETION_COST_USD","DnC_Total_USD","DnC_PreFO_USD","DnC_PostFO_USD",
        "DnC_Intangible_USD","DnC_Tangible_USD","DnC_Tangible_Dep_Expense_USD","Tax_Shield_DnC_USD","After_Tax_DnC_USD",
        "Revenue_USD","Royalty_USD","Variable_OPEX_USD","Fixed_OPEX_USD","Facilities_USD",
        "Net_CashFlow_USD","PV_CashFlow_USD"
    ]].sum(numeric_only=True)

    for col in rollup_cols:
        summary_df.loc[summary_df["DEV_NAME"] == dev, col] = float(sums.get(col, 0.0))

    summary_df.loc[summary_df["DEV_NAME"] == dev, "Final_Pump_Count"] = (
        monthly["PUMP_COUNT_REQUIRED"].max() if "PUMP_COUNT_REQUIRED" in monthly.columns and not monthly.empty else 0
    )
    summary_df.loc[summary_df["DEV_NAME"] == dev, "NPV_USD"] = monthly["PV_CashFlow_USD"].sum() if not monthly.empty else 0.0
    summary_df.loc[summary_df["DEV_NAME"] == dev, "MIRR_monthly"] = mirr_m if not np.isnan(mirr_m) else 0.0
    summary_df.loc[summary_df["DEV_NAME"] == dev, "MIRR_annual"] = ((1.0 + (mirr_m if not np.isnan(mirr_m) else 0.0)) ** 12.0) - 1.0

    # Monthly output sheet
    monthly_out = monthly[[
        "MONTH","MONTHLY_OIL_VOLUME",
        "DRILLING_DAYS","DRILL_RATE_MM","DRILLING_COST_USD",
        "COMPLETION_DAYS","COMP_RATE_MM","COMPLETION_COST_USD",
        "DnC_Total_USD","DnC_PreFO_USD","DnC_PostFO_USD",
        "DnC_Intangible_USD","DnC_Tangible_USD","DnC_Tangible_Dep_Expense_USD","Tax_Shield_DnC_USD","After_Tax_DnC_USD",
        "NEW_PRODUCERS","CUM_PRODUCERS",
        "Host_CAPEX_USD","SURF_USD","Dry_Well_System_USD","Pump_Package_USD","Water_Injection_Facility_USD","Facilities_USD",
        "Revenue_USD","Royalty_USD","Variable_OPEX_USD","Fixed_OPEX_USD",
        "Net_CashFlow_USD","Disc_Factor","PV_CashFlow_USD",
    ]].copy()
    dev_sheets[str(dev)] = monthly_out
# ---------- FO Month formatting ----------
summary_df["FO Month"] = summary_df["FO_Month"].dt.strftime("%b-%y").fillna("")

# ---------- Facilities Cost total ----------
summary_df["Facilities Cost USD"] = (
    summary_df["Host_CAPEX_USD"] + summary_df["SURF_USD"] + summary_df["Pump_Package_USD"] + summary_df["Dry_Well_System_USD"]
)

# ---------- Project summary output ----------
summary_cols = [
    "DEV_NAME","DEV_SYSTEM","FO Month","TOTAL OIL BBL",
    "Host_CAPEX_USD","SURF_USD","Pump_Package_USD","Dry_Well_System_USD","Facilities Cost USD",
    "DRILLING_COST_USD","COMPLETION_COST_USD","DnC_Total_USD","DnC_PreFO_USD","DnC_PostFO_USD",
    "DnC_Intangible_USD","DnC_Tangible_USD","Tax_Shield_DnC_USD","After_Tax_DnC_USD",
    "Revenue_USD","Royalty_USD","Variable_OPEX_USD","Fixed_OPEX_USD",
    "Net_CashFlow_USD","NPV_USD","MIRR_monthly","MIRR_annual",
    "PRODUCER_WELLS","TOTAL_WELLS","Final_Pump_Count"
]
summary_out = summary_df[summary_cols].copy()
summary_out.rename(columns={"DEV_NAME": "Project Name"}, inplace=True)

# ---------- Write Excel with summary first ----------
with pd.ExcelWriter("financial_project_summary.xlsx", engine="xlsxwriter") as writer:
    summary_out.to_excel(writer, sheet_name="Project_Summary", index=False)
    for dev_name, df_monthly in dev_sheets.items():
        df_monthly.to_excel(writer, sheet_name=dev_name[:31], index=False)

print("✅ Financial workbook created: financial_project_summary.xlsx")
