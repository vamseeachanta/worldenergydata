"""Generate per-field input files for all Lower Tertiary fields.

Mirrors the aceengineercode `config/ong_field_development` pattern (field_nickname,
boem_fields, well_type) and enriches with worldenergydata data: BSEE leases
(lease_mapping_fdas.yml), dev_system / first_oil / status / validated economics
(golden_baseline_v30.yml). Writes:
  config/ong_field_development/<Field>.yml      (per-field input, one per field)
  config/ong_field_development/fields_registry.yml  (canonical combined registry)
"""
from __future__ import annotations
from pathlib import Path
import yaml

REPO = Path(__file__).resolve().parents[1]
LT = REPO / "config/analysis/lower_tertiary"
OUT = REPO / "config/ong_field_development"
OUT.mkdir(parents=True, exist_ok=True)

# BOEM area-block codes per field (source: aceengineercode config/ong_field_development)
BOEM = {
    "julia": ["WR627"],
    "jack_st_malo": ["WR758", "WR759", "WR678"],
    "stones": ["WR508"],
    "big_foot": ["WR029"],
    "cascade_chinook": ["WR205", "WR206", "WR469", "WR470"],
    "anchor": ["GC807"],
    "kaskida": ["KC292", "KC291"],
    "tiber": ["KC102"],
    "shenandoah": ["WR051"],
    "north_platte": ["GB915", "GB916", "GB958", "GB959"],
}
FILE_NAME = {  # tidy per-field filename
    "julia": "Julia", "jack_st_malo": "Jack_StMalo", "stones": "Stones",
    "big_foot": "BigFoot", "cascade_chinook": "Cascade_Chinook", "anchor": "Anchor",
    "kaskida": "Kaskida", "tiber": "Tiber", "shenandoah": "Shenandoah",
    "north_platte": "North_Platte",
}
ACE_REF = {  # source file in aceengineercode/config/ong_field_development
    "julia": "XOM_Julia.yml", "jack_st_malo": "Jack.yml + StMalo.yml", "stones": "RDS_Stones.yml",
    "big_foot": "BigFoot.yml", "cascade_chinook": "Cascade.yml + Chinook.yml", "anchor": "CVX_Anchor.yml",
    "kaskida": "Kaskida.yml", "tiber": "Tiber.yml", "shenandoah": "Shenandoah.yml",
    "north_platte": "TOT_North_Platte.yml",
}

# Public field metadata (operator press releases + offshore trade press; researched 2026-06-17).
# UNKNOWN where no reliable public figure exists — not guessed.
ENRICH = {
    "julia": {"operator": "ExxonMobil", "partners": "ExxonMobil 50% (op), Equinor 50%",
              "facility": "subsea tieback to Chevron Jack/St. Malo semi host (~15 mi)",
              "play": "Lower Tertiary (Wilcox neighborhood)", "reported_first_oil": "2016-04",
              "reported_capex_usd": 4.0e9, "plateau_bopd": 34000},
    "jack_st_malo": {"operator": "Chevron", "partners": "Jack: Chevron 50/Maersk 25/Statoil 25; St Malo: Chevron 51/Petrobras 25/Statoil 21.5/ExxonMobil 1.25/ENI 1.25",
              "facility": "deep-draft semisubmersible FPU + subsea tiebacks (up to ~15 mi)",
              "play": "Lower Tertiary Wilcox", "reported_first_oil": "2014-12",
              "reported_capex_usd": 7.5e9, "plateau_bopd": 170000},
    "stones": {"operator": "Shell", "partners": "Shell 100% field WI (Turritella FPSO is a separate vessel JV)",
              "facility": "FPSO Turritella (disconnectable turret-moored)", "play": "Lower Tertiary Wilcox",
              "reported_first_oil": "2016-09", "reported_capex_usd": None, "plateau_bopd": 50000},
    "big_foot": {"operator": "Chevron", "partners": "Chevron 60/Equinor 27.5/Marubeni 12.5",
              "facility": "extended tension-leg platform (ETLP), 15-slot", "play": "Miocene (unconfirmed)",
              "reported_first_oil": "2018-11", "reported_capex_usd": 4.0e9, "plateau_bopd": 75000},
    "cascade_chinook": {"operator": "Petrobras America", "partners": "Cascade: Petrobras 100; Chinook: Petrobras 66.67/TotalEnergies 33.33",
              "facility": "FPSO BW Pioneer (first US-GoM FPSO)", "play": "Lower Tertiary Wilcox",
              "reported_first_oil": "2012-02", "reported_capex_usd": None, "plateau_bopd": 80000},
    "anchor": {"operator": "Chevron", "partners": "Chevron 62.86/TotalEnergies 37.14",
              "facility": "semisubmersible FPU, 7-well subsea — industry-first 20,000 psi (20K)",
              "play": "Lower Tertiary Wilcox", "reported_first_oil": "2024-08",
              "reported_capex_usd": 5.7e9, "plateau_bopd": 75000},
}

lease_map = yaml.safe_load((LT / "lease_mapping_fdas.yml").read_text())
baseline = yaml.safe_load((LT / "golden_baseline_v30.yml").read_text())
base_by_id = baseline["projects"]

producing = set(lease_map.get("producing_fields", []))

registry = {"meta": {"source": "aceengineercode boem_fields + worldenergydata lease_mapping_fdas + golden_baseline_v30",
                     "discount_rate_annual": 0.10, "price_basis": "EIA WTI historical deck",
                     "validation": "field economics reproduce golden_baseline_v30.yml to ~0.001%"},
            "fields": {}}

for fid, fdata in lease_map["fields"].items():
    if fid not in BOEM:
        continue
    b = base_by_id.get(fid, {})
    name = fdata["field_name"]
    leases = [str(x) for x in fdata["leases"]]
    # producing = has real oil in the validated baseline (lease_mapping list is incomplete)
    if (b.get("total_oil_bbl") or 0) > 0:
        status = "producing"
    else:
        status = fdata.get("status", "non_producing")
    rec = {
        "field_nickname": name,
        "boem_fields": BOEM[fid],
        "leases": leases,
        "well_type": ["E", "D"],
        "dev_system": fdata.get("dev_system") or b.get("dev_system"),
        "water_depth_ft": fdata.get("water_depth_ft"),
        "status": status,
        "first_oil": b.get("first_oil"),
        "validated_economics": {
            "total_oil_bbl": b.get("total_oil_bbl"),
            "revenue_usd": b.get("revenue_usd"),
            "capex_usd": (b.get("facilities_cost_usd", 0) + b.get("dnc_total_usd", 0)) or None,
            "npv10_usd": b.get("npv_usd"),
            "mirr_annual": b.get("mirr_annual"),
            "producers": b.get("producers"),
            "wellbores": b.get("wellbores"),
        },
        "public_metadata": ENRICH.get(fid, {}),
    }
    registry["fields"][fid] = rec

    # per-field input file (clean, self-contained, worldenergydata-native)
    e = rec["validated_economics"]
    per = {
        "field": {
            "nickname": name, "id": fid, "status": status,
            "dev_system": rec["dev_system"], "water_depth_ft": rec["water_depth_ft"],
            "first_oil": b.get("first_oil"),
        },
        "location": {
            "boem_fields": BOEM[fid],          # BOEM area-block (aceengineercode)
            "leases": leases,                  # BSEE lease numbers (worldenergydata)
            "well_type": ["E", "D"],           # Exploration + Development
        },
        "analysis": {
            "economics": True, "discount_rate_annual": 0.10,
            "by": ["field", "block", "well"], "vintages": ["v30", "latest"],
        },
        "validated_economics": e,              # from golden_baseline_v30.yml (~0.001% repro)
        "public_metadata": ENRICH.get(fid, {}),  # operator press releases + offshore trade press
        "provenance": {
            "boem_source": "aceengineercode/config/ong_field_development/" + ACE_REF[fid],
            "lease_source": "config/analysis/lower_tertiary/lease_mapping_fdas.yml",
            "economics_source": "config/analysis/lower_tertiary/golden_baseline_v30.yml",
        },
    }
    fpath = OUT / f"{FILE_NAME[fid]}.yml"
    fpath.write_text("# Auto-generated field input — scripts/gen_field_inputs.py\n"
                     "# BOEM blocks mirror aceengineercode config/ong_field_development; enriched with BSEE leases + validated economics.\n"
                     + yaml.safe_dump(per, sort_keys=False, default_flow_style=False, width=100))

(OUT / "fields_registry.yml").write_text(
    "# Auto-generated canonical registry — see scripts/gen_field_inputs.py\n"
    + yaml.safe_dump(registry, sort_keys=False, default_flow_style=False, width=100))

print(f"Wrote {len(registry['fields'])} per-field input files + fields_registry.yml to {OUT.relative_to(REPO)}")
for fid, r in registry["fields"].items():
    e = r["validated_economics"]
    print(f"  {FILE_NAME[fid]+'.yml':22} boem={','.join(r['boem_fields']):24} status={r['status']:14} "
          f"NPV={e['npv10_usd']/1e6 if e['npv10_usd'] else 0:9.1f}M")
