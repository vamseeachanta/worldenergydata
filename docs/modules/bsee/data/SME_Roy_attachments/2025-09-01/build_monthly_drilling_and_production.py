import pandas as pd
import numpy as np
from collections import defaultdict

# ---------- Load Drilling and Completion Data ----------
drill_df = pd.read_excel("drilling_and_completion_days.xlsx")
drill_df.columns = drill_df.columns.str.strip().str.upper().str.replace(" ", "_")
drill_df["WELL_SPUD_DATE"] = pd.to_datetime(drill_df["WELL_SPUD_DATE"], errors="coerce")
drill_df["TOTAL_DEPTH_DATE"] = pd.to_datetime(drill_df["TOTAL_DEPTH_DATE"], errors="coerce")

if "LAST_COMPLETION_ACTIVITY" not in drill_df.columns:
    drill_df["LAST_COMPLETION_ACTIVITY"] = drill_df["TOTAL_DEPTH_DATE"] + pd.to_timedelta(drill_df["COMPLETION_DAYS"], unit="D")
else:
    drill_df["LAST_COMPLETION_ACTIVITY"] = pd.to_datetime(drill_df["LAST_COMPLETION_ACTIVITY"], errors="coerce")

# ---------- Allocate Drilling and Completion Days ----------
def allocate_days_by_month(start_date, end_date, total_days):
    day_counts = defaultdict(int)
    date_range = pd.date_range(start=start_date, end=end_date)
    for date in date_range:
        key = pd.Timestamp(date.year, date.month, 1)
        day_counts[key] += 1
    total_counted = sum(day_counts.values())
    for key in day_counts:
        day_counts[key] = round(day_counts[key] * total_days / total_counted)
    return day_counts

alloc_rows = []
for _, row in drill_df.iterrows():
    api = row["API_WELL_NUMBER"]
    if pd.isna(row["WELL_SPUD_DATE"]) or pd.isna(row["TOTAL_DEPTH_DATE"]) or pd.isna(row["LAST_COMPLETION_ACTIVITY"]):
        continue
    drill_alloc = allocate_days_by_month(row["WELL_SPUD_DATE"], row["TOTAL_DEPTH_DATE"], row["DRILLING_DAYS"])
    comp_alloc = allocate_days_by_month(row["TOTAL_DEPTH_DATE"], row["LAST_COMPLETION_ACTIVITY"], row["COMPLETION_DAYS"])
    months = set(drill_alloc.keys()).union(comp_alloc.keys())
    for month in months:
        alloc_rows.append({
            "API_WELL_NUMBER": api,
            "MONTH": month,
            "ALLOCATED_DRILLING_DAYS": drill_alloc.get(month, 0),
            "ALLOCATED_COMPLETION_DAYS": comp_alloc.get(month, 0)
        })

drill_alloc_df = pd.DataFrame(alloc_rows)
drill_alloc_df["MONTH"] = pd.to_datetime(drill_alloc_df["MONTH"], errors="coerce")
earliest_spud_month = drill_alloc_df["MONTH"].min()

# ---------- Load WTI Prices ----------
wti_df = pd.read_csv("wti_monthly.csv")
wti_df["MONTH"] = pd.to_datetime(wti_df["Month"], errors="coerce").dt.to_period("M").dt.to_timestamp()
wti_df = wti_df[["MONTH", "WTI_USD"]]

# ---------- Process Lease Sheets ----------
xls = pd.ExcelFile("multi_year_lease_matrix_with_charts.xlsx")
sheet_names = xls.sheet_names
leases = set(name.replace("__days", "").replace("__bbl", "") for name in sheet_names if "__days" in name)

final_rows = []
for lease in leases:
    try:
        avg_df = pd.read_excel(xls, sheet_name=lease)
        days_df = pd.read_excel(xls, sheet_name=f"{lease}__days")
        bbl_df = pd.read_excel(xls, sheet_name=f"{lease}__bbl")
    except Exception as e:
        continue

    avg_long = avg_df.melt(id_vars=["WELL_NAME", "API_WELL_NUMBER"], var_name="MONTH", value_name="AVG_BBLS_PER_DAY")
    days_long = days_df.melt(id_vars=["WELL_NAME", "API_WELL_NUMBER"], var_name="MONTH", value_name="DAYS_ON_PROD")
    bbl_long = bbl_df.melt(id_vars=["WELL_NAME", "API_WELL_NUMBER"], var_name="MONTH", value_name="MONTHLY_OIL_VOLUME")

    for df in [avg_long, days_long, bbl_long]:
        df["API_WELL_NUMBER"] = pd.to_numeric(df["API_WELL_NUMBER"], errors="coerce")
        df["MONTH"] = pd.to_datetime(df["MONTH"], errors="coerce").dt.to_period("M").dt.to_timestamp()

    merged = avg_long.merge(days_long, on=["API_WELL_NUMBER", "MONTH"])
    merged = merged.merge(bbl_long, on=["API_WELL_NUMBER", "MONTH"])
    merged["LEASE_NAME"] = lease
    final_rows.append(merged)

prod_df = pd.concat(final_rows, ignore_index=True)
prod_df["MONTH"] = pd.to_datetime(prod_df["MONTH"], errors="coerce")

# ---------- Expand Production to Global Timeline ----------
all_months = pd.date_range(start=earliest_spud_month, end=prod_df["MONTH"].max(), freq="MS")
all_apis = prod_df["API_WELL_NUMBER"].dropna().unique()

grid = pd.MultiIndex.from_product([all_apis, all_months], names=["API_WELL_NUMBER","MONTH"]).to_frame(index=False)
prod_core = prod_df[["API_WELL_NUMBER","MONTH","AVG_BBLS_PER_DAY","DAYS_ON_PROD","MONTHLY_OIL_VOLUME"]]
final_df = grid.merge(prod_core, on=["API_WELL_NUMBER","MONTH"], how="left")

static_cols = prod_df[["API_WELL_NUMBER","WELL_NAME","LEASE_NAME"]].drop_duplicates("API_WELL_NUMBER")
final_df = final_df.merge(static_cols, on="API_WELL_NUMBER", how="left")
final_df = final_df.merge(drill_alloc_df, on=["API_WELL_NUMBER", "MONTH"], how="left")
final_df = final_df.merge(wti_df, on="MONTH", how="left")

final_df["MONTHLY_REVENUE_USD"] = final_df["MONTHLY_OIL_VOLUME"].fillna(0.0) * final_df["WTI_USD"].fillna(0.0)

final_df = final_df[[
    "LEASE_NAME", "WELL_NAME", "API_WELL_NUMBER", "MONTH",
    "ALLOCATED_DRILLING_DAYS", "ALLOCATED_COMPLETION_DAYS",
    "AVG_BBLS_PER_DAY", "DAYS_ON_PROD", "MONTHLY_OIL_VOLUME",
    "WTI_USD", "MONTHLY_REVENUE_USD"
]]

final_df.to_excel("chronological_lease_analysis.xlsx", index=False)
print("✅ Output saved to 'chronological_lease_analysis.xlsx'")
print(f"Global start: {earliest_spud_month.date()} | Rows: {len(final_df):,}")
