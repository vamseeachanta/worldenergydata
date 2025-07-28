# Filename: filter_war_files_by_lease.py (multi-lease support with explicit file tags)

import pandas as pd
import os

# Load leases.csv
leases = pd.read_csv("leases.csv", header=None, encoding="ISO-8859-1", dtype=str)[0].dropna().str.upper().str.strip().tolist()

# Tag for output filenames (use only lease numbers, cleaned)
lease_tag = "_".join([l.replace("/", "-").replace("OCS-G", "G") for l in leases])

# Load mv_war_main
main = pd.read_csv("mv_war_main.txt", encoding="ISO-8859-1", dtype=str)
main['SURF_LEASE_NUM'] = main['SURF_LEASE_NUM'].astype(str).str.upper().str.strip()
main['SN_WAR'] = main['SN_WAR'].astype(str).str.strip()
main['API_WELL_NUMBER'] = main['API_WELL_NUMBER'].astype(str).str.zfill(10)

# Filter mv_war_main by lease
main_filtered = main[main['SURF_LEASE_NUM'].isin(leases)]
main_main_out = f"mv_war_main.{lease_tag}.txt"
main_filtered.to_csv(main_main_out, index=False, encoding="ISO-8859-1")

# Extract relevant APIs for borehole filtering
relevant_apis = main_filtered['API_WELL_NUMBER'].unique().tolist()

# Load and filter mv_war_boreholes_view by API
try:
    bore = pd.read_csv("mv_war_boreholes_view.txt", encoding="ISO-8859-1", dtype=str)
    bore['API_WELL_NUMBER'] = bore['API_WELL_NUMBER'].astype(str).str.zfill(10)
    bore_filtered = bore[bore['API_WELL_NUMBER'].isin(relevant_apis)]
    bore_out = f"mv_war_boreholes_view.{lease_tag}.txt"
    bore_filtered.to_csv(bore_out, index=False, encoding="ISO-8859-1")
except Exception as e:
    print("⚠️ Could not process boreholes file:", e)

# Load and filter mv_war_main_prop_remark by SN_WAR
try:
    remarks = pd.read_csv("mv_war_main_prop_remark.txt", encoding="ISO-8859-1", dtype=str)
    remarks['SN_WAR'] = remarks['SN_WAR'].astype(str).str.strip()
    remarks_filtered = remarks[remarks['SN_WAR'].isin(main_filtered['SN_WAR'].unique())]
    remarks_out = f"mv_war_main_prop_remark.{lease_tag}.txt"
    remarks_filtered.to_csv(remarks_out, index=False, encoding="ISO-8859-1")
except Exception as e:
    print("⚠️ Could not process remarks file:", e)

print(f"✅ Lease-specific WAR files written:\n- {main_main_out}\n- {bore_out}\n- {remarks_out}")


