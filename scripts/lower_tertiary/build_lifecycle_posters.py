#!/usr/bin/env python3
"""ABOUTME: Generate per-field life-cycle "page 1" posters for Lower Tertiary fields.
ABOUTME: Reads per-field FACTS (dates/metrics) and stamps them into one shared HTML template.

Design
------
The presentation is single-sourced in ``lifecycle_template.html`` (CSS + the fixed
8-phase MODEL + the render script, with a ``__FIELD_JSON__`` placeholder). This
generator turns a small, human/agent-authored *facts* record per field into the
render-shaped ``FIELD`` object — computing the calendar axis, gate positions and
cycle-time spans deterministically in code so no layout math is invented by hand.

Facts come from ``_facts.json`` (a list of field-facts dicts). Run with no args to
self-test against the Big Foot tracer.

Usage
-----
    python scripts/lower_tertiary/build_lifecycle_posters.py            # build all in _facts.json
    python scripts/lower_tertiary/build_lifecycle_posters.py --self-test
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from worldenergydata.field_development.host_text_classifier import (  # noqa: E402
    classify_tree_type,
)
from worldenergydata.field_development.decommission_risk import (  # noqa: E402
    classify_decommissioning,
)
from worldenergydata.field_development.hpht_risk import classify_hpht  # noqa: E402
from worldenergydata.field_development.landman import (  # noqa: E402
    build_landman,
)

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import site_nav  # noqa: E402  (nav-spine helper, issue #850)

from worldenergydata.common.fields_registry import load_fields  # noqa: E402

HERE = Path(__file__).resolve().parents[2] / "reports/lower_tertiary/lifecycle"
TEMPLATE = HERE / "lifecycle_template.html"
FACTS = HERE / "_facts.json"
# Facility decommissioning liabilities (#949 underwriting badge). Comment lines
# (leading '#') are the provenance header; skip them.
_DECOM_CSV = (
    Path(__file__).resolve().parents[2]
    / "reports/decommissioning/regional_liability.csv"
)


def _load_decom_rows() -> list[dict]:
    if not _DECOM_CSV.exists():
        return []
    lines = [ln for ln in _DECOM_CSV.read_text().splitlines() if not ln.startswith("#")]
    return list(csv.DictReader(lines))


_DECOM_ROWS = _load_decom_rows()
TODAY_YEAR = 2026.5  # generated 2026-07-03; a fixed "you are here" marker on the axis
FIELDS_REGISTRY = load_fields()

# BSEE lease attributes for the landman panel (#951). Committed source is the
# FDAS V30 lease workbook (name/depth/dev-system only); status/dates/WI/block are
# placeholders linking the ingest issue below. Build-time only (pandas); the
# published site just copies the frozen posters + _explorer.json.
_LEASE_INGEST_ISSUE = 959
_V30_DIR = (
    Path(__file__).resolve().parents[2]
    / "docs/modules/bsee/analysis/production/FDAS_V30"
)


def _load_lease_rows() -> dict:
    """{normalized_lease_num: {water_depth_ft, dev_system, lease_name}}."""
    try:
        import pandas as pd
    except ImportError:
        return {}
    rows: dict[str, dict] = {}
    for name in ("leases.xlsx", "leases_v21_kc.csv"):
        path = _V30_DIR / name
        if not path.exists():
            continue
        df = pd.read_excel(path) if name.endswith(".xlsx") else pd.read_csv(path)
        for _, r in df.iterrows():
            key = str(r["LEASE_NUM"]).upper().replace(" ", "").strip()
            wd = pd.to_numeric(r.get("WATER_DEPTH"), errors="coerce")
            rows.setdefault(
                key,
                {
                    "lease_name": (
                        str(r["LEASE_NAME"]).strip()
                        if pd.notna(r.get("LEASE_NAME"))
                        else None
                    ),
                    "water_depth_ft": int(wd) if pd.notna(wd) else None,
                    "dev_system": (
                        str(r["DEV_SYSTEM"]).strip()
                        if pd.notna(r.get("DEV_SYSTEM"))
                        else None
                    ),
                },
            )
    return rows


_LEASE_ROWS = _load_lease_rows()

PHASE_KEYS = [
    "acquire",
    "explore",
    "appraise",
    "select",
    "define",
    "execute",
    "operate",
    "abandon",
]

STATUS = {  # status -> (pill label, CSS hue var for the status pill)
    "producing": ("Producing", "var(--good)"),
    "execution": ("Under construction", "var(--done)"),
    "sanctioned": ("Sanctioned · pre-first-oil", "var(--done)"),
    "appraisal": ("Appraisal", "var(--muted)"),
    "select": ("Concept select", "var(--muted)"),
    "explore": ("Exploration", "var(--muted)"),
    "abandoned": ("Abandoned", "var(--alert)"),
}


def _year(v):
    """Parse 'YYYY' or 'YYYY-MM' -> decimal year (mid-month), or None."""
    if v is None:
        return None
    s = str(v)
    if "-" in s:
        y, m = s.split("-")[:2]
        return int(y) + (int(m) - 0.5) / 12.0
    return float(s)


def _pretty(v):
    if v is None:
        return None
    s = str(v)
    if "-" in s:
        y, m = s.split("-")[:2]
        months = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        return f"{months[int(m) - 1]} {y}"
    return s


def _span_txt(a, b, label, extra=""):
    yrs = round(b - a)
    return f"{label} ~{yrs} yr{extra}"


def facts_to_field(f: dict) -> dict:
    """Transform an author-authored facts record into the render-shaped FIELD object."""
    g = f.get("gates", {})
    disc = _year(g.get("discovery_year"))
    fid = _year(g.get("fid_year"))
    lease = _year(g.get("lease_year"))
    first = _year(g.get("first_oil"))
    cop = _year(g.get("projected_cop_year"))
    incident = g.get("incident")  # {"year":..,"label":..} or None

    known = [y for y in (lease, disc, fid, first) if y is not None]
    start = int((min(known) if known else TODAY_YEAR) - 2)
    if cop is not None:
        end = int(cop)
    elif first is not None:
        end = int(first + 20)
    elif fid is not None:
        end = int(fid + 12)
    elif disc is not None:
        end = int(disc + 25)
    else:
        end = start + 30
    start -= start % 5  # align to a 5-year grid start
    end += (5 - end % 5) % 5
    ticks = list(range(start, end + 1, 5))

    gates = []
    if disc is not None:
        gates.append(
            {
                "year": disc,
                "phase": "explore",
                "lab": "Discovery",
                "dt": str(g["discovery_year"]),
                "kind": "primary",
            }
        )
    if fid is not None:
        gates.append(
            {
                "year": fid,
                "phase": "define",
                "lab": "FID / Sanction",
                "dt": str(g["fid_year"]),
                "kind": "primary",
            }
        )
    if incident:
        # keep the flag terse — take the leading clause and cap length so a long
        # sentence (agents sometimes return a full description) can't break the timeline.
        lab = incident["label"].split("(")[0].split(";")[0].split(",")[0].strip()
        if len(lab) > 26:
            lab = lab[:24].rstrip() + "…"
        gates.append(
            {
                "year": _year(incident["year"]),
                "phase": "execute",
                "lab": lab,
                "dt": str(incident["year"]),
                "kind": "sec",
            }
        )
    if first is not None:
        gates.append(
            {
                "year": first,
                "phase": "operate",
                "lab": "First oil",
                "dt": _pretty(g["first_oil"]),
                "kind": "now",
            }
        )
    if (
        f.get("status") == "producing"
        and first is not None
        and start < TODAY_YEAR < end
    ):
        gates.append(
            {
                "year": TODAY_YEAR,
                "phase": "operate",
                "lab": "Today",
                "dt": "2026",
                "kind": "nowmark",
            }
        )

    spans = []
    if disc is not None and fid is not None:
        spans.append(
            {"from": disc, "to": fid, "txt": _span_txt(disc, fid, "Discovery→FID")}
        )
    if fid is not None and first is not None:
        extra = " (incl. delay)" if incident else ""
        spans.append(
            {
                "from": fid,
                "to": first,
                "txt": _span_txt(fid, first, "FID→first oil", extra),
            }
        )
    if first is not None and cop is not None:
        spans.append(
            {
                "from": first,
                "to": cop,
                "txt": _span_txt(first, cop, "Operating life", " proj."),
            }
        )

    metrics = []
    if f.get("water_depth_ft") is not None:
        metrics.append({"k": "Water depth", "v": f"{f['water_depth_ft']:,}", "u": "ft"})
    if f.get("capex_bn_usd") is not None:
        metrics.append({"k": "Gross CAPEX", "v": f"${f['capex_bn_usd']:g}", "u": "B"})
    if f.get("plateau_mbopd") is not None:
        metrics.append(
            {"k": "Plateau rate", "v": f"{f['plateau_mbopd']:g}", "u": "mbopd"}
        )
    if f.get("gor_scf") is not None:
        metrics.append({"k": "GOR", "v": f"{f['gor_scf']:,}", "u": "scf/bbl"})
    if f.get("opex_boe") is not None:
        metrics.append({"k": "OPEX", "v": f"${f['opex_boe']:g}", "u": "/boe"})
    wi = f.get("working_interest", [])
    op = next((w for w in wi if w.get("operator")), None)
    if op:
        metrics.append({"k": "Operator WI", "v": f"{op['wi']:g}", "u": "%"})

    host_facts = []
    if f.get("host_type"):
        host_facts.append(["Host type", f["host_type"]])
    if f.get("water_depth_ft") is not None:
        m = round(f["water_depth_ft"] * 0.3048)
        host_facts.append(["Water depth", f"{f['water_depth_ft']:,} ft ({m:,} m)"])
    if f.get("play"):
        host_facts.append(["Play", f["play"]])
    if g.get("first_oil"):
        host_facts.append(["First oil", _pretty(g["first_oil"])])
    elif fid is not None:
        host_facts.append(["Sanctioned", str(g["fid_year"])])
    if g.get("data_through"):
        host_facts.append(["Data through", _pretty(g["data_through"])])

    label, hue = STATUS.get(f.get("status", "producing"), STATUS["producing"])

    # Dry- vs wet-tree development-type badge (classified from the host text).
    tree_type, concept_label = classify_tree_type(f.get("host_type", ""))
    tree_label = None
    if tree_type is not None:
        tree_label = f"{'Dry' if tree_type == 'dry' else 'Wet'} tree · {concept_label}"

    region = f.get("region_block", "")
    if f.get("basin"):
        region = f"{region} · {f['basin']}" if region else f["basin"]

    # Drill-down to well-level timelines, if any were generated for this field.
    wells_dir = HERE / "wells"
    well_files = (
        sorted(wells_dir.glob(f"{f['id']}_*_well.html")) if wells_dir.exists() else []
    )
    assets_page = HERE / "assets" / f"{f['id']}_assets.html"
    registry_field = FIELDS_REGISTRY.by_id(f["id"])
    if registry_field is None:
        raise ValueError(f"Lifecycle facts id not in canonical registry: {f['id']}")
    economics_href = (
        f"../economics-{f['id']}.html"
        if registry_field.surfaces.get("economics_page")
        else None
    )

    return {
        "id": f["id"],
        "wellsHref": "wells/" if well_files else None,
        "wellsCount": len(well_files),
        "assetsHref": (
            f"assets/{f['id']}_assets.html" if assets_page.exists() else None
        ),
        "economics_href": economics_href,
        "benchmark_href": "../benchmark.html",
        "name": f["name"],
        "operator": f.get("operator", ""),
        "region": region,
        "host": f.get("host_type", ""),
        "statusLabel": label,
        "statusHue": hue,
        "treeType": tree_type,
        "treeLabel": tree_label,
        "currentPhase": f.get("current_phase", "operate"),
        "metrics": metrics,
        "axis": {"start": start, "end": end, "ticks": ticks},
        "gates": gates,
        "spans": spans,
        "workingInterest": [
            {
                "name": w["name"],
                "wi": w["wi"],
                **({"lead": True} if w.get("operator") else {}),
            }
            for w in wi
        ],
        "hostFacts": host_facts,
        "reservoir": f.get("reservoir"),
        "risk": {
            "hpht": classify_hpht(f.get("reservoir")),
            "decommissioning": classify_decommissioning(
                f.get("decommissioning_facility"), _DECOM_ROWS
            ),
        },
        "landman": build_landman(
            f,
            list(registry_field.leases),
            list(registry_field.area_blocks),
            _LEASE_ROWS,
            _LEASE_INGEST_ISSUE,
            registry_field.bsee_block_note,
        ),
        "provenance": f.get(
            "provenance", "Data: field YAML + public disclosures + BSEE"
        ),
    }


def render(field: dict) -> str:
    tpl = TEMPLATE.read_text()
    html = tpl.replace(
        "__FIELD_JSON__", json.dumps(field, indent=2, ensure_ascii=False)
    )
    return site_nav.inject_for(
        html, "poster", {"field_id": field["id"], "field_name": field["name"]}
    )


def build_index(fields: list[dict]) -> str:
    order = {k: i for i, k in enumerate(PHASE_KEYS)}
    rows = "\n".join(
        f'      <li><a href="{fl["id"]}_lifecycle.html">{fl["name"]}</a>'
        f'<span>{fl["operator"]}</span><span>{fl["statusLabel"]}</span></li>'
        for fl in sorted(
            fields, key=lambda x: (order.get(x["currentPhase"], 9), x["name"])
        )
    )
    return f"""<meta charset="utf-8">
<title>Lower Tertiary — Field Life-Cycle Posters</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body{{margin:0;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;
       background:#eef2f6;color:#0c1a28}}
  @media (prefers-color-scheme:dark){{body{{background:#0a141f;color:#e8eef4}}}}
  .w{{max-width:720px;margin:0 auto;padding:40px 24px}}
  h1{{font-size:28px;letter-spacing:-.02em;margin:0 0 4px}}
  p.sub{{color:#5a6b7b;margin:0 0 28px}}
  ul{{list-style:none;padding:0;margin:0;display:grid;gap:8px}}
  li{{display:grid;grid-template-columns:1fr auto auto;gap:16px;align-items:center;
     background:#fff;border:1px solid #d6e0ea;border-radius:10px;padding:14px 18px}}
  @media (prefers-color-scheme:dark){{li{{background:#10202f;border-color:#24384b}}}}
  a{{font-weight:700;text-decoration:none;color:inherit;font-size:16px}}
  li span{{font-family:ui-monospace,monospace;font-size:12px;color:#5a6b7b}}
</style>
<div class="w">
  {site_nav.crumb_for("gallery")}
  <h1>Lower Tertiary field life-cycle posters</h1>
  <p class="sub">Stage-gate "page 1" summaries · draft tracers for wed #738 ·
    sorted by current phase</p>
  <ul>
{rows}
  </ul>
</div>
"""


BIG_FOOT_FACTS = {
    "id": "big_foot",
    "name": "Big Foot",
    "operator": "Chevron",
    "region_block": "Walker Ridge 29 (G16942)",
    "basin": "US Gulf of Mexico",
    "host_type": "Extended Tension-Leg Platform (eTLP)",
    "play": "Wilcox / Lower Tertiary",
    "water_depth_ft": 5200,
    "status": "producing",
    "current_phase": "operate",
    "capex_bn_usd": 5.2,
    "plateau_mbopd": 75,
    "gor_scf": 1100,
    "opex_boe": 15.0,
    "working_interest": [
        {"name": "Chevron", "wi": 60, "operator": True},
        {"name": "Equinor", "wi": 27.5},
        {"name": "Marubeni Oil & Gas", "wi": 12.5},
    ],
    "gates": {
        "discovery_year": 2006,
        "fid_year": 2010,
        "incident": {"year": 2015, "label": "Tendon incident"},
        "first_oil": "2018-11",
        "data_through": "2024-12",
        "projected_cop_year": 2038,
    },
    "provenance": (
        "Data: big_foot.yml + Chevron public disclosures + BSEE "
        "(dates to be reconciled in #375)"
    ),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    facts = (
        [BIG_FOOT_FACTS]
        if (args.self_test or not FACTS.exists())
        else json.loads(FACTS.read_text())
    )
    # Phase-norm chips (issue #848): attach per-field vs-norm strip data when
    # the norms contract exists (build_phase_norms.py writes it). Posters stay
    # buildable without it — the template hides the strip when norms is empty.
    norms_chips = {}
    norms_path = HERE / "_norms.json"
    if norms_path.exists():
        norms_chips = json.loads(norms_path.read_text()).get("chips", {})

    # Field-performance stats (issue #756): attach the per-field BSEE
    # life-to-date contract when present. Only the 7 producing fields have a
    # record; None makes the template hide the card (honesty-gated).
    perf_fields = {}
    perf_path = HERE / "_performance.json"
    if perf_path.exists():
        perf_fields = json.loads(perf_path.read_text()).get("fields", {})

    fields = []
    for f in facts:
        field = facts_to_field(f)
        field["norms"] = norms_chips.get(f["id"], [])
        field["performance"] = perf_fields.get(f["id"])
        out = HERE / f"{f['id']}_lifecycle.html"
        out.write_text(render(field))
        fields.append(field)
        print(
            f"  wrote {out.name}  ({field['statusLabel']}, "
            f"phase={field['currentPhase']}, gates={len(field['gates'])})"
        )
    (HERE / "index.html").write_text(build_index(fields))
    print(f"  wrote index.html  ({len(fields)} fields)")

    # Explorer sidecar (issue #946): the SAME post-enrichment payloads the
    # posters embed (facts_to_field + norms + performance), keyed by id, plus
    # the wells contract verbatim — one fetch for the field-atlas shell.
    # Hrefs inside are lifecycle/-relative by contract; consumers outside
    # lifecycle/ must rebase against ../lifecycle/ (link-graph gate enforces).
    wells_contract = {}
    wells_facts = HERE / "wells" / "_wells.json"
    if wells_facts.exists():
        wells_contract = json.loads(wells_facts.read_text())
    (HERE / "_explorer.json").write_text(
        json.dumps(
            {
                "meta": {
                    "generated_by": "scripts/lower_tertiary/build_lifecycle_posters.py",
                    "issue": 946,
                },
                "fields": {fl["id"]: fl for fl in fields},
                "wells": wells_contract,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    print(f"  wrote _explorer.json  ({len(fields)} fields)")


if __name__ == "__main__":
    main()
