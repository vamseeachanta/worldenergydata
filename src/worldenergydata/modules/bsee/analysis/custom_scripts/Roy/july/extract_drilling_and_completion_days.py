# Filename: extract_drilling_and_completion_days.py (enhanced with depth and mud weight)

import pandas as pd
import re
from datetime import datetime

# Load lease list: Column A = LEASE_NAME, B = LEASE_NUM, C = WATER_DEPTH
lease_df = pd.read_csv("leases.csv", header=None, encoding="utf-8-sig", dtype=str)
lease_df.columns = ['LEASE_NUM', 'LEASE_NAME', 'WATER_DEPTH']
lease_df['LEASE_NUM'] = lease_df['LEASE_NUM'].str.upper().str.strip()
lease_df = lease_df.dropna(subset=['LEASE_NUM'])
leases = lease_df['LEASE_NUM'].str.replace('^G', '', regex=True).tolist()
print("🔍 Lease Numbers from leases.csv (stripped of 'G'):", leases)

# Build lease lookup dictionary
lease_info = (
    lease_df.drop_duplicates(subset=['LEASE_NUM'])
    .assign(LEASE_NUM=lambda df: df['LEASE_NUM'].str.upper().str.replace('^G', '', regex=True).str.strip())
    .set_index('LEASE_NUM')[['LEASE_NAME', 'WATER_DEPTH']]
    .to_dict(orient='index')
)

# Load WAR main
main_war = pd.read_csv("mv_war_main.txt", encoding="ISO-8859-1", dtype=str)
print("🔍 Sample SURF_LEASE_NUMs from WAR file:", main_war['SURF_LEASE_NUM'].dropna().unique()[:10])
main_war['SURF_LEASE_NUM'] = main_war['SURF_LEASE_NUM'].astype(str).str.upper().str.replace('^G', '', regex=True).str.strip()
main_war['API_WELL_NUMBER'] = main_war['API_WELL_NUMBER'].astype(str).str.zfill(10)
main_war['SN_WAR'] = main_war['SN_WAR'].astype(str).str.strip()
main_war['WELL_NAME'] = main_war['WELL_NAME'].fillna("")
main_war['WAR_START_DT'] = pd.to_datetime(main_war['WAR_START_DT'], errors='coerce')
main_war['WAR_END_DT'] = pd.to_datetime(main_war['WAR_END_DT'], errors='coerce')

# Filter by lease
main_war_filtered = main_war[main_war['SURF_LEASE_NUM'].isin(leases)].copy()
print(f"✅ Filtered WAR records: {len(main_war_filtered)} out of {len(main_war)}")

# Load boreholes
boreholes = pd.read_csv("mv_war_boreholes_view.txt", encoding="ISO-8859-1", dtype=str)
boreholes['API_WELL_NUMBER'] = boreholes['API_WELL_NUMBER'].astype(str).str.zfill(10)
boreholes['WELL_SPUD_DATE'] = pd.to_datetime(boreholes['WELL_SPUD_DATE'], errors='coerce')
boreholes['TOTAL_DEPTH_DATE'] = pd.to_datetime(boreholes['TOTAL_DEPTH_DATE'], errors='coerce')
boreholes['BH_TOTAL_MD'] = pd.to_numeric(boreholes['BH_TOTAL_MD'], errors='coerce')
boreholes['WELL_BORE_TVD'] = pd.to_numeric(boreholes['WELL_BORE_TVD'], errors='coerce')

# Extract TD from boreholes
td_from_boreholes = (
    boreholes.dropna(subset=['TOTAL_DEPTH_DATE'])
    .groupby('API_WELL_NUMBER')['TOTAL_DEPTH_DATE']
    .max()
    .reset_index()
)

# Add depth info
depth_summary = boreholes.groupby('API_WELL_NUMBER')[['BH_TOTAL_MD', 'WELL_BORE_TVD']].max().reset_index()
depth_summary.columns = ['API_WELL_NUMBER', 'MAX_BH_TOTAL_MD', 'MAX_WELL_BORE_TVD']

# Add mud weight from mv_war_main_prop.txt (merge via SN_WAR -> API_WELL_NUMBER)
main_prop = pd.read_csv("mv_war_main_prop.txt", encoding="ISO-8859-1", dtype=str)
main_prop['SN_WAR'] = main_prop['SN_WAR'].astype(str).str.strip()
main_prop['DRILL_FLUID_WGT'] = pd.to_numeric(main_prop['DRILL_FLUID_WGT'], errors='coerce')

# Merge API_WELL_NUMBER from main_war
main_merge = main_war[['SN_WAR', 'API_WELL_NUMBER']].dropna().drop_duplicates()
main_merge['API_WELL_NUMBER'] = main_merge['API_WELL_NUMBER'].astype(str).str.zfill(10)
main_prop = main_prop.merge(main_merge, on='SN_WAR', how='left')

# Group to get max mud weight per API
mud_summary = (
    main_prop.dropna(subset=['DRILL_FLUID_WGT'])
    .groupby('API_WELL_NUMBER')['DRILL_FLUID_WGT']
    .max()
    .reset_index()
    .rename(columns={'DRILL_FLUID_WGT': 'MAX_DRILL_FLUID_WGT'})
)

# Build drilling timeline
GAP_THRESHOLD = 300

def adjust_spud(api, td):
    war_dates = main_war_filtered[main_war_filtered['API_WELL_NUMBER'] == api][['WAR_START_DT', 'WAR_END_DT']].dropna()
    war_dates = war_dates[war_dates['WAR_START_DT'] <= td]
    if war_dates.empty or pd.isna(td):
        return td, 0

    war_dates = war_dates.sort_values(by='WAR_START_DT').reset_index(drop=True)
    war_dates['GAP'] = war_dates['WAR_START_DT'].diff().dt.days

    if (td - war_dates.loc[0, 'WAR_START_DT']).days <= GAP_THRESHOLD:
        return war_dates.loc[0, 'WAR_START_DT'], 0

    gap_idx = war_dates.index[war_dates['GAP'] > GAP_THRESHOLD].tolist()
    if gap_idx:
        last_gap_idx = gap_idx[-1]
        if last_gap_idx + 1 < len(war_dates):
            spud_after_gap = war_dates.loc[last_gap_idx + 1, 'WAR_START_DT']
            early_days = (war_dates.loc[:last_gap_idx, 'WAR_END_DT'] - war_dates.loc[:last_gap_idx, 'WAR_START_DT']).dt.days.sum()
            return spud_after_gap, int(early_days)

    return war_dates.loc[0, 'WAR_START_DT'], 0

rows = []
for _, row in td_from_boreholes.iterrows():
    api = row['API_WELL_NUMBER']
    td = row['TOTAL_DEPTH_DATE']
    spud, early_days = adjust_spud(api, td)
    if pd.notna(spud) and pd.notna(td) and td > spud:
        rows.append((api, spud, td, (td - spud).days - early_days))

spud_td = pd.DataFrame(rows, columns=['API_WELL_NUMBER', 'WELL_SPUD_DATE', 'TOTAL_DEPTH_DATE', 'DRILLING_DAYS'])

# Completion estimation from WAR timeline after TD
COMPLETION_GAP_THRESHOLD = 8

completion_segments = []
for _, row in spud_td.iterrows():
    api = row['API_WELL_NUMBER']
    td = row['TOTAL_DEPTH_DATE']
    completions = main_war_filtered[
        (main_war_filtered['API_WELL_NUMBER'] == api) &
        (main_war_filtered['WAR_START_DT'] > td)
    ][['WAR_START_DT', 'WAR_END_DT']].dropna().sort_values(by='WAR_START_DT')

    if completions.empty:
        completion_segments.append((api, 0))
        continue

    completions = completions.reset_index(drop=True)
    completions['GAP'] = completions['WAR_START_DT'].diff().dt.days.fillna(0)

    segment_days = 0
    start_idx = 0
    for i in range(1, len(completions)):
        if completions.loc[i, 'GAP'] > COMPLETION_GAP_THRESHOLD:
            segment = completions.loc[start_idx:i-1]
            segment_days += (segment['WAR_END_DT'] - segment['WAR_START_DT']).dt.days.sum()
            start_idx = i
    # Add final segment
    segment = completions.loc[start_idx:]
    segment_days += (segment['WAR_END_DT'] - segment['WAR_START_DT']).dt.days.sum()

    completion_segments.append((api, max(segment_days, 0)))

completion_summary = pd.DataFrame(completion_segments, columns=['API_WELL_NUMBER', 'COMPLETION_DAYS'])
final = spud_td.merge(completion_summary, on='API_WELL_NUMBER', how='left')
final['COMPLETION_DAYS'] = final['COMPLETION_DAYS'].fillna(0).astype(int)

# Add WELL_NAME, LEASE info
final['WELL_NAME'] = final['API_WELL_NUMBER'].map(
    main_war_filtered.dropna(subset=['WELL_NAME']).drop_duplicates('API_WELL_NUMBER').set_index('API_WELL_NUMBER')['WELL_NAME']
)
api_to_lease = (
    main_war_filtered.drop_duplicates('API_WELL_NUMBER')
    .assign(SURF_LEASE_NUM=lambda df: df['SURF_LEASE_NUM'].str.upper().str.replace('^G', '', regex=True).str.strip())
    .set_index('API_WELL_NUMBER')['SURF_LEASE_NUM']
    .to_dict()
)
final['SURF_LEASE_NUM'] = final['API_WELL_NUMBER'].map(api_to_lease)

# Debug: print mapping sample
print("🔎 Sample API to Lease Mapping:")
for api in list(final['API_WELL_NUMBER'].unique())[:5]:
    lease_num = api_to_lease.get(api, 'N/A')
    lease_meta = lease_info.get(lease_num, {})
    print(f"API: {api} → Lease#: {lease_num} → Name: {lease_meta.get('LEASE_NAME', '')}, Depth: {lease_meta.get('WATER_DEPTH', '')}")

final['LEASE_NAME'] = final['SURF_LEASE_NUM'].map(lambda x: lease_info.get(x, {}).get('LEASE_NAME', ''))
final['WATER_DEPTH'] = final['SURF_LEASE_NUM'].map(lambda x: lease_info.get(x, {}).get('WATER_DEPTH', ''))

# Merge depths and mud
final = final.merge(depth_summary, on='API_WELL_NUMBER', how='left')
final = final.merge(mud_summary, on='API_WELL_NUMBER', how='left')

# Format and export
final['WELL_SPUD_DATE'] = pd.to_datetime(final['WELL_SPUD_DATE']).dt.strftime('%m/%d/%Y')
final['TOTAL_DEPTH_DATE'] = pd.to_datetime(final['TOTAL_DEPTH_DATE']).dt.strftime('%m/%d/%Y')
final = final[['LEASE_NAME', 'SURF_LEASE_NUM', 'WATER_DEPTH', 'API_WELL_NUMBER', 'WELL_NAME', 'WELL_SPUD_DATE',
               'TOTAL_DEPTH_DATE', 'DRILLING_DAYS', 'COMPLETION_DAYS',
               'MAX_BH_TOTAL_MD', 'MAX_WELL_BORE_TVD', 'MAX_DRILL_FLUID_WGT']]
final = final.dropna(subset=['WELL_SPUD_DATE', 'TOTAL_DEPTH_DATE'])
final['SPUD_DATE_SORT'] = pd.to_datetime(final['WELL_SPUD_DATE'], errors='coerce')
final = final.sort_values(by=['LEASE_NAME', 'SPUD_DATE_SORT']).drop(columns=['SPUD_DATE_SORT'])
final.to_excel("drilling_and_completion_days_by_api_latest.xlsx", index=False)
print("✅ drilling_and_completion_days_by_api.xlsx written.")
