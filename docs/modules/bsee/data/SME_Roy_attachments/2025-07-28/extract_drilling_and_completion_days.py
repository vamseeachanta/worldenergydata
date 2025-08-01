# Filename: extract_drilling_and_completion_days.py (corrected)

import pandas as pd
import re
from datetime import datetime

# Load lease list
leases = pd.read_csv("leases.csv", header=None, encoding="ISO-8859-1", dtype=str)[0].dropna().str.upper().tolist()

# Load WAR main
main_war = pd.read_csv("mv_war_main.txt", encoding="ISO-8859-1", dtype=str)
main_war['SURF_LEASE_NUM'] = main_war['SURF_LEASE_NUM'].astype(str).str.upper().str.strip()
main_war['API_WELL_NUMBER'] = main_war['API_WELL_NUMBER'].astype(str).str.zfill(10)
main_war['SN_WAR'] = main_war['SN_WAR'].astype(str).str.strip()
main_war['WELL_NAME'] = main_war['WELL_NAME'].fillna("")
main_war['WAR_START_DT'] = pd.to_datetime(main_war['WAR_START_DT'], errors='coerce')
main_war['WAR_END_DT'] = pd.to_datetime(main_war['WAR_END_DT'], errors='coerce')

# Filter by lease
main_war_filtered = main_war[main_war['SURF_LEASE_NUM'].isin(leases)].copy()

# Load boreholes
boreholes = pd.read_csv("mv_war_boreholes_view.txt", encoding="ISO-8859-1", dtype=str)
boreholes['API_WELL_NUMBER'] = boreholes['API_WELL_NUMBER'].astype(str).str.zfill(10)
boreholes['WELL_SPUD_DATE'] = pd.to_datetime(boreholes['WELL_SPUD_DATE'], errors='coerce')
boreholes['TOTAL_DEPTH_DATE'] = pd.to_datetime(boreholes['TOTAL_DEPTH_DATE'], errors='coerce')

# Extract TD from boreholes
td_from_boreholes = (
    boreholes.dropna(subset=['TOTAL_DEPTH_DATE'])
    .groupby('API_WELL_NUMBER')['TOTAL_DEPTH_DATE']
    .max()
    .reset_index()
)

# ---------- Fallback spud logic ----------
def detect_resume_from_remarks(api_number, td_date):
    remarks = pd.read_csv("mv_war_main_prop_remark.txt", encoding="ISO-8859-1", dtype=str)
    war_index = pd.read_csv("mv_war_main.txt", encoding="ISO-8859-1", dtype=str)

    remarks['SN_WAR'] = remarks['SN_WAR'].astype(str)
    war_index['SN_WAR'] = war_index['SN_WAR'].astype(str)
    war_index['API_WELL_NUMBER'] = war_index['API_WELL_NUMBER'].astype(str).str.zfill(10)
    war_index['WAR_START_DT'] = pd.to_datetime(war_index['WAR_START_DT'], errors='coerce')

    merged = remarks.merge(
        war_index[['SN_WAR', 'API_WELL_NUMBER', 'WAR_START_DT']],
        on='SN_WAR', how='left'
    )
    merged = merged.dropna(subset=['WAR_START_DT', 'TEXT_REMARK'])
    subset = merged[(merged['API_WELL_NUMBER'] == api_number)]
    subset = subset[subset['WAR_START_DT'] <= td_date]
    subset = subset[subset['TEXT_REMARK'].str.contains('drill', case=False, na=False)]

    if subset.empty:
        return None
    return subset.sort_values('WAR_START_DT').iloc[0]['WAR_START_DT']

# Adjust spud logic
GAP_THRESHOLD = 300

def adjust_spud(api, td_date):
    war_dates = main_war_filtered[main_war_filtered['API_WELL_NUMBER'] == api][['WAR_START_DT', 'WAR_END_DT']].dropna()
    war_dates = war_dates[war_dates['WAR_START_DT'] <= td_date]  # ✅ Filter WARs before TD

    if war_dates.empty or pd.isna(td_date):
        resume = detect_resume_from_remarks(api, td_date)
        return (resume if resume else td_date - pd.Timedelta(days=30)), 0

    war_dates = war_dates.sort_values(by='WAR_START_DT').reset_index(drop=True)
    war_dates['GAP'] = war_dates['WAR_START_DT'].diff().dt.days

    if (td_date - war_dates.loc[0, 'WAR_START_DT']).days <= GAP_THRESHOLD:
        return war_dates.loc[0, 'WAR_START_DT'], 0

    gap_idx = war_dates.index[war_dates['GAP'] > GAP_THRESHOLD].tolist()
    if gap_idx:
        last_gap_idx = gap_idx[-1]
        if last_gap_idx + 1 < len(war_dates):
            spud_after_gap = war_dates.loc[last_gap_idx + 1, 'WAR_START_DT']
            early_days = (war_dates.loc[:last_gap_idx, 'WAR_END_DT'] - war_dates.loc[:last_gap_idx, 'WAR_START_DT']).dt.days.sum()
            return spud_after_gap, int(early_days)

    return war_dates.loc[0, 'WAR_START_DT'], 0

# ---------- Apply to all APIs ----------
war_spuds = main_war_filtered.groupby('API_WELL_NUMBER')['WAR_START_DT'].min().reset_index()
spud_td = war_spuds.merge(td_from_boreholes, on='API_WELL_NUMBER', how='left')

adjusted_spuds = []
for _, row in spud_td.iterrows():
    api, td = row['API_WELL_NUMBER'], row['TOTAL_DEPTH_DATE']
    spud, early_days = adjust_spud(api, td)
    adjusted_spuds.append((api, spud, td, early_days))

spud_td = pd.DataFrame(adjusted_spuds, columns=['API_WELL_NUMBER', 'WELL_SPUD_DATE', 'TOTAL_DEPTH_DATE', 'EARLY_DAYS'])
spud_td['DRILLING_DAYS'] = (spud_td['TOTAL_DEPTH_DATE'] - spud_td['WELL_SPUD_DATE']).dt.days + spud_td['EARLY_DAYS']

# WELL_NAME lookup
well_name_lookup = (
    main_war_filtered[['API_WELL_NUMBER', 'WELL_NAME']]
    .dropna().drop_duplicates(subset=['API_WELL_NUMBER'])
    .set_index('API_WELL_NUMBER')['WELL_NAME'].to_dict()
)

# Load and filter remarks
remarks = pd.read_csv("mv_war_main_prop_remark.txt", encoding="ISO-8859-1", dtype=str)
remarks.columns = remarks.columns.str.strip()
remarks = remarks[['SN_WAR', 'TEXT_REMARK']]
remarks['SN_WAR'] = remarks['SN_WAR'].astype(str).str.strip()
remarks['TEXT_REMARK'] = remarks['TEXT_REMARK'].fillna("").astype(str)

sn_wars = main_war_filtered['SN_WAR'].unique()
remarks = remarks[remarks['SN_WAR'].isin(sn_wars)].copy()

# Merge API + TD date
remarks = remarks.merge(
    main_war_filtered[['SN_WAR', 'API_WELL_NUMBER', 'WELL_NAME']],
    on='SN_WAR', how='left'
)
remarks = remarks.merge(
    spud_td[['API_WELL_NUMBER', 'TOTAL_DEPTH_DATE']],
    on='API_WELL_NUMBER', how='left'
)

# Extract dates from TEXT_REMARK
def extract_dates(text):
    tokens = re.findall(r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}', text)
    tokens = [tok.replace('-', '/').replace('.', '/') for tok in tokens]
    dates = []
    for tok in tokens:
        try:
            parsed = pd.to_datetime(tok, errors='raise', dayfirst=False)
            if parsed.year > 2099:
                parsed = parsed.replace(year=parsed.year - 100)
            dates.append(parsed)
        except:
            continue
    return (min(dates), max(dates)) if dates else (pd.NaT, pd.NaT)

dates = remarks['TEXT_REMARK'].apply(extract_dates)
remarks['START_DATE'] = [d[0] for d in dates]
remarks['END_DATE'] = [d[1] for d in dates]
remarks['START_DATE'] = pd.to_datetime(remarks['START_DATE'], errors='coerce')
remarks['END_DATE'] = pd.to_datetime(remarks['END_DATE'], errors='coerce')

# Clean bad END_DATE
remarks.loc[
    (remarks['START_DATE'].dt.year != remarks['END_DATE'].dt.year) &
    ~((remarks['START_DATE'].dt.month == 12) & (remarks['END_DATE'].dt.month == 1) &
      (remarks['END_DATE'].dt.year == remarks['START_DATE'].dt.year + 1)),
    'END_DATE'
] = remarks['START_DATE']

remarks = remarks.dropna(subset=['TOTAL_DEPTH_DATE', 'END_DATE'])

# Filter completion remarks
completion_df = remarks[remarks['START_DATE'] > remarks['TOTAL_DEPTH_DATE']].copy()
completion_df['DURATION_DAYS'] = (completion_df['END_DATE'] - completion_df['START_DATE']).dt.days + 1

# Completion summary
completion_summary = (
    completion_df.groupby('API_WELL_NUMBER')['DURATION_DAYS']
    .sum()
    .reset_index()
    .rename(columns={'DURATION_DAYS': 'COMPLETION_DAYS'})
)

# Final merge
final = spud_td.merge(completion_summary, on='API_WELL_NUMBER', how='left')
final['COMPLETION_DAYS'] = final['COMPLETION_DAYS'].fillna(0).astype(int)
final['WELL_NAME'] = final['API_WELL_NUMBER'].map(well_name_lookup)

# Format and export
final['WELL_SPUD_DATE'] = pd.to_datetime(final['WELL_SPUD_DATE']).dt.strftime('%m/%d/%Y')
final['TOTAL_DEPTH_DATE'] = pd.to_datetime(final['TOTAL_DEPTH_DATE']).dt.strftime('%m/%d/%Y')
final = final[['API_WELL_NUMBER', 'WELL_NAME', 'WELL_SPUD_DATE', 'TOTAL_DEPTH_DATE', 'DRILLING_DAYS', 'COMPLETION_DAYS']]
final = final.sort_values(by='API_WELL_NUMBER')
final.to_excel("drilling_and_completion_days_by_api.xlsx", index=False)

print("✅ Completed: drilling_and_completion_days_by_api.xlsx written.")





