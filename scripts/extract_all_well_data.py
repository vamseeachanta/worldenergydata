"""Per-bore drilling data for ALL Lower Tertiary fields (generalizes extract_julia_well_data).

Reads FDAS V30 drilling_and_completion_days.xlsx, groups by field via lease, and marks
producing bores using the producing APIs from all_fields_economics.json. Writes
reports/lower_tertiary/data/all_fields_wells.json.
"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
MAIN = Path("/mnt/local-analysis/worldenergydata")
V30 = MAIN / "docs/modules/bsee/analysis/production/FDAS_V30"
MODU_RATE_MM = {"subsea15": 0.8, "subsea20": 1.1, "dry": 0.8, "tieback15": 0.8, "tieback20": 1.1}

registry = (REPO / "config/ong_field_development/fields_registry.yml")
import yaml
REG = yaml.safe_load(registry.read_text())["fields"]
ECON = json.loads((REPO / "reports/lower_tertiary/data/all_fields_economics.json").read_text())["by_field"]

dnc = pd.read_excel(V30 / "drilling_and_completion_days.xlsx")
dnc["_lease"] = dnc["SURF_LEASE_NUM"].astype(str).str.upper().str.replace('"', "", regex=False).str.replace(" ", "", regex=False)

out = {}
for fid, reg in REG.items():
    leases = set(str(x).upper() for x in reg["leases"])
    wd = float(reg.get("water_depth_ft") or 0)
    rate = MODU_RATE_MM.get((reg.get("dev_system") or "subsea15").lower().replace(" ", ""), 0.8)
    rows_df = dnc[dnc["_lease"].isin(leases)]
    if rows_df.empty:
        continue
    prod_apis = set(ECON.get(fid, {}).get("by_well", {}).keys())   # producing API strings
    wells = []
    for _, r in rows_df.iterrows():
        api = str(int(r["API_WELL_NUMBER"])) if pd.notna(r["API_WELL_NUMBER"]) else ""
        spud = pd.to_datetime(r["WELL_SPUD_DATE"], errors="coerce")
        td = pd.to_datetime(r["TOTAL_DEPTH_DATE"], errors="coerce")
        drill = float(pd.to_numeric(r["DRILLING_DAYS"], errors="coerce") or 0)
        comp = float(pd.to_numeric(r["COMPLETION_DAYS"], errors="coerce") or 0)
        md = float(pd.to_numeric(r["MAX_BH_TOTAL_MD"], errors="coerce") or 0)
        tvd = float(pd.to_numeric(r["MAX_WELL_BORE_TVD"], errors="coerce") or 0)
        footage = max(md - wd, 1.0)
        wells.append({
            "api": api, "well_name": str(r["WELL_NAME"]).strip(),
            "spud": spud.strftime("%Y-%m-%d") if pd.notna(spud) else None,
            "td": td.strftime("%Y-%m-%d") if pd.notna(td) else None,
            "drilling_days": drill, "completion_days": comp, "rig_days": drill + comp,
            "md_ft": md, "tvd_ft": tvd,
            "horiz_disp_ft": round((max(md ** 2 - tvd ** 2, 0.0)) ** 0.5, 0),
            "days_per_10k_ft": round(drill / footage * 10000, 2) if drill else None,
            "producing": api in prod_apis,
        })
    wells.sort(key=lambda w: (w["spud"] or "9999"))
    rig_days = sum(w["rig_days"] for w in wells)
    out[fid] = {
        "field": reg["field_nickname"], "dev_system": reg.get("dev_system"),
        "water_depth_ft": wd, "wellbores": len(wells),
        "producers": sum(w["producing"] for w in wells),
        "total_rig_days": rig_days, "dnc_cost_usd": rig_days * rate * 1e6,
        "campaign_start": min((w["spud"] for w in wells if w["spud"]), default=None),
        "campaign_end": max((w["td"] for w in wells if w["td"]), default=None),
        "wells": wells,
    }

(REPO / "reports/lower_tertiary/data/all_fields_wells.json").write_text(json.dumps(out, indent=2))
print(f"Wrote drilling data for {len(out)} fields")
for fid, d in out.items():
    print(f"  {d['field']:16} bores={d['wellbores']:3} prod={d['producers']:3} rig_days={d['total_rig_days']:6.0f} "
          f"campaign={d['campaign_start']}..{d['campaign_end']}")
