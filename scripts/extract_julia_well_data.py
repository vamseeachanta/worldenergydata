"""Extract Julia per-wellbore drilling data for the well-engineering report sections.

Source: FDAS V30 drilling_and_completion_days.xlsx (real BSEE-derived D&C days,
spud/TD dates, MD/TVD) for lease G20351, plus the producing APIs from OGOR.
Emits reports/lower_tertiary/data/julia_wells.json.
"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
V30 = REPO / "docs/modules/bsee/analysis/production/FDAS_V30"
JULIA_LEASE = "G20351"
WATER_DEPTH_FT = 7335.0
# producing APIs (oil>0 in OGOR) — last 4-5 digits identify the bore
PRODUCING_API_TAILS = {"09400", "03301", "10800", "12701"}  # DC101, JU102, JU104, JU106

dnc = pd.read_excel(V30 / "drilling_and_completion_days.xlsx")
s = dnc["SURF_LEASE_NUM"].astype(str).str.upper().str.replace('"', "", regex=False).str.replace(" ", "", regex=False)
jd = dnc[s == JULIA_LEASE].copy()

wells = []
for _, r in jd.iterrows():
    api = str(int(r["API_WELL_NUMBER"])) if pd.notna(r["API_WELL_NUMBER"]) else ""
    spud = pd.to_datetime(r["WELL_SPUD_DATE"], errors="coerce")
    td = pd.to_datetime(r["TOTAL_DEPTH_DATE"], errors="coerce")
    drill = float(pd.to_numeric(r["DRILLING_DAYS"], errors="coerce") or 0)
    comp = float(pd.to_numeric(r["COMPLETION_DAYS"], errors="coerce") or 0)
    md = float(pd.to_numeric(r["MAX_BH_TOTAL_MD"], errors="coerce") or 0)
    tvd = float(pd.to_numeric(r["MAX_WELL_BORE_TVD"], errors="coerce") or 0)
    # drilled footage below mudline and normalized rate
    footage = max(md - WATER_DEPTH_FT, 1.0)
    days_per_10k = round(drill / footage * 10000, 2) if drill else None
    # horizontal displacement (indicative geometry from MD/TVD, no survey available)
    horiz = round((max(md ** 2 - tvd ** 2, 0.0)) ** 0.5, 0)
    wells.append({
        "api": api,
        "well_name": str(r["WELL_NAME"]).strip(),
        "spud": spud.strftime("%Y-%m-%d") if pd.notna(spud) else None,
        "td": td.strftime("%Y-%m-%d") if pd.notna(td) else None,
        "drilling_days": drill,
        "completion_days": comp,
        "rig_days": drill + comp,
        "md_ft": md,
        "tvd_ft": tvd,
        "horiz_disp_ft": horiz,
        "days_per_10k_ft": days_per_10k,
        "producing": api[-5:] in PRODUCING_API_TAILS,
    })

wells.sort(key=lambda w: (w["spud"] or "9999"))
summary = {
    "field": "Julia", "lease": JULIA_LEASE, "water_depth_ft": WATER_DEPTH_FT,
    "wellbores": len(wells), "producers": sum(w["producing"] for w in wells),
    "total_drilling_days": sum(w["drilling_days"] for w in wells),
    "total_completion_days": sum(w["completion_days"] for w in wells),
    "total_rig_days": sum(w["rig_days"] for w in wells),
    "dnc_cost_usd": (sum(w["rig_days"] for w in wells)) * 0.8e6,  # MODU $0.8M/day (tieback15)
    "campaign_start": min(w["spud"] for w in wells if w["spud"]),
    "campaign_end": max(w["td"] for w in wells if w["td"]),
}
out = {"summary": summary, "wells": wells}
(REPO / "reports/lower_tertiary/data/julia_wells.json").write_text(json.dumps(out, indent=2))
print("WELLS:", summary["wellbores"], "producers:", summary["producers"],
      "rig_days:", summary["total_rig_days"], "campaign:", summary["campaign_start"], "->", summary["campaign_end"])
for w in wells:
    print(f"  {w['well_name']:7} {w['spud']}->{w['td']} drill={w['drilling_days']:.0f} comp={w['completion_days']:.0f} "
          f"MD={w['md_ft']:.0f} TVD={w['tvd_ft']:.0f} d/10k={w['days_per_10k_ft']} prod={w['producing']}")
