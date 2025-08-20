# extract_drilling_and_completion_days.py
# Preserves original D&C logic; reads NEW leases.xlsx format; labels by LEASE_NAME.
import pandas as pd
import numpy as np
import re
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

# === Parameters ===
DRILL_GAP_DAYS = 20   # merge drill segments gaps <= 20 days
COMP_GAP_DAYS  = 8    # merge completion activity gaps <= 8 days

# ---------- helpers ----------
def std_cols(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(c).strip() for c in df.columns]
    return df

def normalize_lease_num(val: str) -> str:
    """Return SURF_LEASE_NUM style: 'G#####' if numeric, else uppercase as-is."""
    if pd.isna(val):
        return None
    s = str(val).strip().upper()
    m = re.fullmatch(r"G?(\d+)", s)
    if m:
        return "G" + m.group(1)
    return s

def to_dt(series: pd.Series) -> pd.Series:
    """Quietly parse heterogenous dates."""
    a = pd.to_datetime(series, errors='coerce', format='%m/%d/%Y')
    m = a.isna()
    if m.any():
        a.loc[m] = pd.to_datetime(series[m], errors='coerce', format='%Y-%m-%d')
    m = a.isna()
    if m.any():
        a.loc[m] = pd.to_datetime(series[m], errors='coerce')
    return a

# ---------- load leases (NEW FORMAT tolerant) ----------
lease_df = std_cols(pd.read_excel("leases.xlsx", dtype=str))

# Find a lease-number column and normalize to SURF_LEASE_NUM style
lease_num_col = None
for cand in ["LEASE_NUM", "Lease_Num", "LEASE NUMBER", "SURF_LEASE_NUM", "Lease_Numeric", "LEASE_NUMERIC", "LEASE#"]:
    if cand in lease_df.columns:
        lease_num_col = cand
        break
if lease_num_col is None:
    # fallback: any column containing values that look like G#### or digits
    for c in lease_df.columns:
        if lease_df[c].astype(str).str.contains(r"^[Gg]?\d+$", na=False).any():
            lease_num_col = c
            break
if lease_num_col is None:
    raise KeyError(f"leases.xlsx: could not find a lease number column. Have: {list(lease_df.columns)}")

lease_df["LEASE_NUM"] = lease_df[lease_num_col].apply(normalize_lease_num)

# Try to pick up names and water depth for metadata mapping
lease_name_col = None
for cand in ["LEASE_NAME", "Lease_Name", "LEASE NAME"]:
    if cand in lease_df.columns: lease_name_col = cand; break
water_depth_col = None
for cand in ["WATER_DEPTH", "Water_Depth", "WATER DEPTH", "WD"]:
    if cand in lease_df.columns: water_depth_col = cand; break

# Build mapping dicts for metadata
lease_df["LEASE_NAME_META"] = lease_df[lease_name_col] if lease_name_col else ""
lease_df["WATER_DEPTH_META"] = lease_df[water_depth_col] if water_depth_col else np.nan
lease_info = lease_df.set_index("LEASE_NUM")[["LEASE_NAME_META", "WATER_DEPTH_META"]].to_dict("index")
leases = lease_df["LEASE_NUM"].dropna().astype(str).str.upper().unique().tolist()

# ---------- load WAR main ----------
main_war = std_cols(pd.read_csv("mv_war_main.txt", encoding="ISO-8859-1", dtype=str, low_memory=False))
main_war["SURF_LEASE_NUM"] = main_war["SURF_LEASE_NUM"].astype(str).map(normalize_lease_num)
main_war["API_WELL_NUMBER"] = main_war["API_WELL_NUMBER"].astype(str).str.zfill(10)
main_war["SN_WAR"] = main_war["SN_WAR"].astype(str).str.strip()
main_war["WELL_NAME"] = main_war["WELL_NAME"].fillna("")

# Use WAR_START_DT / WAR_END_DT as in your original flow
if "WAR_START_DT" in main_war.columns:
    main_war["WAR_START_DT"] = to_dt(main_war["WAR_START_DT"])
else:
    main_war["WAR_START_DT"] = pd.NaT
if "WAR_END_DT" in main_war.columns:
    main_war["WAR_END_DT"] = to_dt(main_war["WAR_END_DT"])
else:
    main_war["WAR_END_DT"] = pd.NaT
print("Using SPUD source column: WAR_START_DT")

# Keep only selected leases
main_war_filtered = main_war[main_war["SURF_LEASE_NUM"].isin(leases)].copy()

# ---------- load boreholes ----------
boreholes = std_cols(pd.read_csv("mv_war_boreholes_view.txt", encoding="ISO-8859-1", dtype=str, low_memory=False))
boreholes["API_WELL_NUMBER"] = boreholes["API_WELL_NUMBER"].astype(str).str.zfill(10)
boreholes["TOTAL_DEPTH_DATE"] = to_dt(boreholes["TOTAL_DEPTH_DATE"])
# optional depth fields
if "BH_TOTAL_MD" in boreholes.columns:
    boreholes["BH_TOTAL_MD"] = pd.to_numeric(boreholes["BH_TOTAL_MD"], errors="coerce")
else:
    boreholes["BH_TOTAL_MD"] = np.nan
if "WELL_BORE_TVD" in boreholes.columns:
    boreholes["WELL_BORE_TVD"] = pd.to_numeric(boreholes["WELL_BORE_TVD"], errors="coerce")
else:
    boreholes["WELL_BORE_TVD"] = np.nan

# ---------- build DRILL segments (unchanged logic) ----------
drilling_segments = []
# drive off boreholes TD list
for api_num, td in boreholes.dropna(subset=["TOTAL_DEPTH_DATE"])[["API_WELL_NUMBER", "TOTAL_DEPTH_DATE"]].values:
    spud = main_war_filtered[main_war_filtered["API_WELL_NUMBER"] == api_num]["WAR_START_DT"].min()
    if pd.isna(spud) or pd.isna(td):
        continue
    war_rows = main_war_filtered[
        (main_war_filtered["API_WELL_NUMBER"] == api_num) &
        (main_war_filtered["WAR_START_DT"] >= spud) &
        (main_war_filtered["WAR_END_DT"]   <= td)
    ].sort_values("WAR_START_DT")
    seg_start = None
    prev_end = None
    for _, row in war_rows.iterrows():
        start, end = row["WAR_START_DT"], row["WAR_END_DT"]
        if seg_start is None:
            seg_start = start
        elif (start - prev_end).days > DRILL_GAP_DAYS:
            drilling_segments.append((api_num, seg_start, prev_end))
            seg_start = start
        prev_end = max(prev_end or end, end)
    if seg_start is not None and prev_end is not None:
        drilling_segments.append((api_num, seg_start, prev_end))

drill_df = pd.DataFrame(drilling_segments, columns=["API_WELL_NUMBER", "WELL_SPUD_DATE", "TOTAL_DEPTH_DATE"])
# enforce datetime dtype before dt math
drill_df["WELL_SPUD_DATE"]   = pd.to_datetime(drill_df["WELL_SPUD_DATE"], errors="coerce")
drill_df["TOTAL_DEPTH_DATE"] = pd.to_datetime(drill_df["TOTAL_DEPTH_DATE"], errors="coerce")
# match your original: drilling days without +1
drill_df["DRILLING_DAYS"] = (drill_df["TOTAL_DEPTH_DATE"] - drill_df["WELL_SPUD_DATE"]).dt.days
drill_df.to_excel("drill_segments_debug.xlsx", index=False)

# ---------- mud weights ----------
main_prop = std_cols(pd.read_csv("mv_war_main_prop.txt", encoding="ISO-8859-1", dtype=str, low_memory=False))
main_prop["SN_WAR"] = main_prop["SN_WAR"].astype(str).str.strip()
if "DRILL_FLUID_WGT" in main_prop.columns:
    main_prop["DRILL_FLUID_WGT"] = pd.to_numeric(main_prop["DRILL_FLUID_WGT"], errors="coerce")
merge_sn_api = main_war[["SN_WAR", "API_WELL_NUMBER"]].dropna().drop_duplicates()
merge_sn_api["API_WELL_NUMBER"] = merge_sn_api["API_WELL_NUMBER"].astype(str).str.zfill(10)
main_prop = main_prop.merge(merge_sn_api, on="SN_WAR", how="left")
mud_summary = (main_prop.dropna(subset=["DRILL_FLUID_WGT"])
               .groupby("API_WELL_NUMBER")["DRILL_FLUID_WGT"].max()
               .rename("MAX_DRILL_FLUID_WGT").reset_index())

# ---------- remarks ----------
remarks = std_cols(pd.read_csv("mv_war_main_prop_remark.txt", encoding="ISO-8859-1", dtype=str, low_memory=False))
# need SN_WAR + TEXT_REMARK (tolerate variant column names)
if "SN_WAR" not in remarks.columns:
    raise KeyError(f"mv_war_main_prop_remark.txt missing SN_WAR; have {list(remarks.columns)}")
text_col = "TEXT_REMARK"
if text_col not in remarks.columns:
    # fallback heuristic: first text-ish column
    for c in remarks.columns:
        if "REMARK" in c.upper() or "TEXT" in c.upper():
            text_col = c; break
remarks = remarks[["SN_WAR", text_col]].dropna()
remarks["SN_WAR"] = remarks["SN_WAR"].astype(str).str.strip()
remarks = remarks.merge(main_war_filtered[["SN_WAR", "API_WELL_NUMBER"]], on="SN_WAR", how="left").dropna(subset=["API_WELL_NUMBER"])
# pull first date-like token from remark text
remarks["DATE"] = remarks[text_col].astype(str).str.extract(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})")[0]
remarks["DATE"] = to_dt(remarks["DATE"])
remarks = remarks.dropna(subset=["DATE"])

# ---------- build COMPLETION segments post-TD (unchanged logic) ----------
completion_segments = []
td_map = (boreholes.dropna(subset=["TOTAL_DEPTH_DATE"])
          .set_index("API_WELL_NUMBER")["TOTAL_DEPTH_DATE"].to_dict())

for api_num, grp in remarks.groupby("API_WELL_NUMBER"):
    td = td_map.get(api_num)
    if pd.isna(td):
        continue
    post_td = grp.loc[grp["DATE"] > td].sort_values("DATE")["DATE"].tolist()
    if not post_td:
        continue
    seg_start = seg_end = None
    for d in post_td:
        if seg_start is None:
            seg_start = d
        elif (d - seg_end).days > COMP_GAP_DAYS:
            completion_segments.append((api_num, seg_start, seg_end))
            seg_start = d
        seg_end = d
    if seg_start is not None and seg_end is not None:
        completion_segments.append((api_num, seg_start, seg_end))

comp_df = pd.DataFrame(completion_segments, columns=["API_WELL_NUMBER", "COMP_START", "COMP_END"])
# enforce datetime dtype before dt math (fixes your crash)
comp_df["COMP_START"] = pd.to_datetime(comp_df["COMP_START"], errors="coerce")
comp_df["COMP_END"]   = pd.to_datetime(comp_df["COMP_END"],   errors="coerce")
comp_df = comp_df.dropna(subset=["COMP_START","COMP_END"])
# your original: completion +1 day
comp_df["COMPLETION_DAYS"] = (comp_df["COMP_END"] - comp_df["COMP_START"]).dt.days + 1
comp_df.to_excel("completion_segments_debug.xlsx", index=False)

# ---------- merge summaries ----------
drill_summary = drill_df.groupby("API_WELL_NUMBER").agg({
    "WELL_SPUD_DATE": "min",
    "TOTAL_DEPTH_DATE": "max",
    "DRILLING_DAYS": "sum"
}).reset_index()

comp_summary = comp_df.groupby("API_WELL_NUMBER")["COMPLETION_DAYS"].sum().reset_index()

final = drill_summary.merge(comp_summary, on="API_WELL_NUMBER", how="left")
final["COMPLETION_DAYS"] = final["COMPLETION_DAYS"].fillna(0).astype(int)

# ---------- metadata ----------
# well name from main
well_name_map = (main_war_filtered.dropna(subset=["WELL_NAME"])
                 .drop_duplicates("API_WELL_NUMBER")
                 .set_index("API_WELL_NUMBER")["WELL_NAME"].to_dict())
final["WELL_NAME"] = final["API_WELL_NUMBER"].map(well_name_map)

# depths from boreholes
depth_summary = (boreholes.groupby("API_WELL_NUMBER")[["BH_TOTAL_MD", "WELL_BORE_TVD"]]
                 .max().reset_index())
depth_summary.columns = ["API_WELL_NUMBER", "MAX_BH_TOTAL_MD", "MAX_WELL_BORE_TVD"]
final = final.merge(depth_summary, on="API_WELL_NUMBER", how="left")
final = final.merge(mud_summary, on="API_WELL_NUMBER", how="left")

# lease id and human name/depth from leases.xlsx (normalized)
api_to_lease = (main_war_filtered.drop_duplicates("API_WELL_NUMBER")
                .set_index("API_WELL_NUMBER")["SURF_LEASE_NUM"].to_dict())
final["SURF_LEASE_NUM"] = final["API_WELL_NUMBER"].map(api_to_lease)

final["LEASE_NAME"] = final["SURF_LEASE_NUM"].map(lambda x: lease_info.get(x, {}).get("LEASE_NAME_META", ""))
final["WATER_DEPTH"] = final["SURF_LEASE_NUM"].map(lambda x: lease_info.get(x, {}).get("WATER_DEPTH_META", ""))

# ---------- output ----------
# Format dates as mm/dd/YYYY like your prior file
final["WELL_SPUD_DATE"]   = pd.to_datetime(final["WELL_SPUD_DATE"]).dt.strftime("%m/%d/%Y")
final["TOTAL_DEPTH_DATE"] = pd.to_datetime(final["TOTAL_DEPTH_DATE"]).dt.strftime("%m/%d/%Y")

final = final[[
    "LEASE_NAME", "SURF_LEASE_NUM", "WATER_DEPTH",
    "API_WELL_NUMBER", "WELL_NAME",
    "WELL_SPUD_DATE", "TOTAL_DEPTH_DATE",
    "DRILLING_DAYS", "COMPLETION_DAYS",
    "MAX_BH_TOTAL_MD", "MAX_WELL_BORE_TVD", "MAX_DRILL_FLUID_WGT"
]]
final = final.dropna(subset=["WELL_SPUD_DATE", "TOTAL_DEPTH_DATE"])

final.to_excel("drilling_and_completion_days_by_api.xlsx", index=False)
print("\n✅ drilling_and_completion_days_by_api.xlsx written with original D&C logic (leases normalized only).")
