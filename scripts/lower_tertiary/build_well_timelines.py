#!/usr/bin/env python3
"""ABOUTME: Generate per-well GRANULAR life-cycle timelines (the fractal well-level deep-dive).
ABOUTME: Reads _wells.json facts and stamps them into one shared well template (epic #754, issue #758).

Design mirrors the field life-cycle generator: a small per-well *facts* record →
a render-shaped ``WELL`` object stamped into ``well_lifecycle_template.html``
(``__WELL_JSON__`` placeholder). The geometry is computed in code:

  - Well construction band uses a **rig-day scale** (Drill days → Complete days),
    NOT calendar, because a well can be spudded years before it reaches TD
    (e.g. Big Foot A008: spud 2013, TD 2021, but only 118 rig-days).
  - Production life band uses a **calendar-year scale** from first oil, with
    workover markers and a "today" marker.

Usage
-----
    python scripts/lower_tertiary/build_well_timelines.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "packages/worldenergydata-bsee/src"))

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
import site_nav  # noqa: E402  (nav-spine helper, issue #850)

HERE = REPO / "reports/lower_tertiary/lifecycle/wells"
TEMPLATE = HERE / "well_lifecycle_template.html"
FACTS = HERE / "_wells.json"
GENERATED = "Generated 2026-07-04"
TODAY_YEAR = 2026.5

MONTHS = [
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


def _year(v):
    """'YYYY-MM-DD' or 'YYYY-MM' → decimal year (mid-month)."""
    if v is None:
        return None
    p = str(v).split("-")
    y = int(p[0])
    m = int(p[1]) if len(p) > 1 else 6
    return y + (m - 0.5) / 12.0


def _pretty(v):
    if v is None:
        return "—"
    p = str(v).split("-")
    if len(p) >= 2:
        return f"{MONTHS[int(p[1]) - 1]} {p[0]}"
    return p[0]


def facts_to_well(w: dict, field: dict) -> dict:
    drill = w.get("drilling_rig_days") or 0
    compl = w.get("completion_rig_days") or 0
    total = drill + compl
    fo = _year(w["first_oil"])

    # --- construction band: rig-day scale ---
    end_c = total if total else 1
    step = 50 if end_c <= 250 else 100
    ticks_c = [{"v": t, "t": str(t)} for t in range(0, end_c + 1, step)]
    if ticks_c[-1]["v"] != end_c:
        ticks_c.append({"v": end_c, "t": str(end_c)})
    c_gates = [{"x": 0, "lab": "Spud", "dt": _pretty(w["spud_date"]), "kind": ""}]
    if drill:
        c_gates.append(
            {
                "x": drill,
                "lab": "TD reached",
                "dt": _pretty(w.get("td_date")),
                "kind": "",
            }
        )
    c_gates.append(
        {"x": end_c, "lab": "Completed", "dt": _pretty(w["first_oil"]), "kind": "now"}
    )
    c_spans = []
    if drill:
        c_spans.append({"from": 0, "to": drill, "txt": f"Drill · {drill:g} rig-days"})
    if compl:
        c_spans.append(
            {"from": drill, "to": total, "txt": f"Complete · {compl:g} rig-days"}
        )

    # --- production band: calendar years ---
    start_p = int(fo)
    end_p = start_p + 20
    end_p += (5 - end_p % 5) % 5
    start_p -= start_p % 5 if start_p % 5 <= 2 else 0
    ticks_p = [
        {"v": t, "t": str(t)} for t in range(((start_p + 4) // 5) * 5, end_p + 1, 5)
    ]
    p_gates = [
        {"x": fo, "lab": "First oil", "dt": _pretty(w["first_oil"]), "kind": "now"}
    ]
    for wo in w.get("workovers", []):
        p_gates.append(
            {
                "x": _year(wo["date"]),
                "lab": wo["type"],
                "dt": _pretty(wo["date"]),
                "kind": "sec",
            }
        )
    if fo < TODAY_YEAR < end_p:
        p_gates.append(
            {"x": TODAY_YEAR, "lab": "Today", "dt": "2026", "kind": "nowmark"}
        )
    cum = w.get("cum_oil_mmbbl")
    up = w.get("uptime_pct")
    prod_txt = "Producing"
    if cum is not None:
        prod_txt += f" · {cum:g} MMbbl"
    if up is not None:
        prod_txt += f" · {up:g}% uptime"
    p_spans = [{"from": fo, "to": end_p - 2, "txt": prod_txt}]

    metrics = [
        {"k": "Drilling", "v": f"{drill:g}", "u": "rig-days"},
        {"k": "Completion", "v": f"{compl:g}", "u": "rig-days"},
    ]
    if w.get("max_tvd_ft") is not None:
        metrics.append({"k": "Max TVD", "v": f"{w['max_tvd_ft']:,}", "u": "ft"})
    if w.get("mud_weight_ppg") is not None:
        metrics.append({"k": "Mud weight", "v": f"{w['mud_weight_ppg']:g}", "u": "ppg"})
    if cum is not None:
        metrics.append({"k": "Cum oil", "v": f"{cum:g}", "u": "MMbbl"})
    if up is not None:
        metrics.append({"k": "Uptime", "v": f"{up:g}", "u": "%"})

    wo_n = len(w.get("workovers", []))
    cards = [
        {
            "t": "Drill · done",
            "big": f"{drill:g} rig-days",
            "li": [
                f"TD {w.get('max_tvd_ft', 0):,} ft",
                f"{w.get('mud_weight_ppg', '—')} ppg mud",
                f"spud {_pretty(w['spud_date'])}",
            ],
        },
        {
            "t": "Complete · done",
            "big": f"{compl:g} rig-days",
            "li": [f"first oil {_pretty(w['first_oil'])}", field.get("play", "")],
        },
        {
            "t": "Produce · now",
            "big": (f"{cum:g} MMbbl" if cum is not None else "producing"),
            "li": ([f"{up:g}% uptime"] if up is not None else [])
            + [f"{field['display_name']} · {field.get('host', '')}"],
            "cur": True,
        },
        {
            "t": "Workover",
            "big": (f"{wo_n} event" + ("s" if wo_n != 1 else "")),
            "li": [
                f"{_pretty(wo['date'])} · {wo['type']}" for wo in w.get("workovers", [])
            ]
            or ["none to date"],
        },
        {"t": "Abandon", "big": "—", "li": ["still producing", "no P&A"]},
    ]

    fid = w["field_id"]
    return {
        "title": f"{field['display_name']} · {w['slot']}",
        "sub": (
            f"API {w['api']} · {field.get('block', '')} · {field.get('operator', '')} · "
            f"{field.get('play', '')} — nested under the "
            f"<a href=\"../{fid}_lifecycle.html\">{field['display_name']} field life-cycle</a>"
        ),
        "statusLabel": "Producing",
        "generated": GENERATED,
        "phases": [
            {"k": "spud", "n": "Spud"},
            {"k": "drill", "n": "Drill"},
            {"k": "complete", "n": "Complete"},
            {"k": "produce", "n": "Produce"},
            {"k": "abandon", "n": "Abandon"},
        ],
        "current": "produce",
        "metrics": metrics,
        "cAxis": {"start": 0, "end": end_c, "ticks": ticks_c},
        "cGates": c_gates,
        "cSpans": c_spans,
        "pAxis": {"start": int(fo) - (int(fo) % 5), "end": end_p, "ticks": ticks_p},
        "pGates": p_gates,
        "pSpans": p_spans,
        "cards": cards,
    }


def render(well: dict) -> str:
    return TEMPLATE.read_text().replace(
        "__WELL_JSON__", json.dumps(well, indent=2, ensure_ascii=False)
    )


def build_index(rows: list[dict]) -> str:
    items = "\n".join(
        f'      <li><a href="{r["file"]}">{r["title"]}</a><span>{r["cum"]}</span></li>'
        for r in sorted(rows, key=lambda r: -r["cum_val"])
    )
    return f"""<meta charset="utf-8">
<title>Well Life-Cycle Timelines</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body{{margin:0;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;background:#eef2f6;color:#0c1a28}}
  @media (prefers-color-scheme:dark){{body{{background:#0a141f;color:#e8eef4}}}}
  .w{{max-width:640px;margin:0 auto;padding:40px 24px}} h1{{font-size:26px;letter-spacing:-.02em;margin:0 0 4px}}
  p.sub{{color:#5a6b7b;margin:0 0 24px}} ul{{list-style:none;padding:0;margin:0;display:grid;gap:8px}}
  li{{display:grid;grid-template-columns:1fr auto;gap:16px;align-items:center;background:#fff;border:1px solid #d6e0ea;border-radius:10px;padding:14px 18px}}
  @media (prefers-color-scheme:dark){{li{{background:#10202f;border-color:#24384b}}}}
  a{{font-weight:700;text-decoration:none;color:inherit;font-size:16px}} li span{{font-family:ui-monospace,monospace;font-size:12px;color:#5a6b7b}}
</style>
<div class="w">{site_nav.crumb_for("wells_index")}<h1>Well life-cycle timelines</h1>
<p class="sub">Per-well granular deep-dives · draft tracers for #758 · sorted by cumulative oil</p>
<ul>
{items}
</ul></div>
"""


def _economics_context():
    """Load the #849 economics substrate once (config, rates, revenue, norms)."""
    import yaml

    from worldenergydata.bsee.analysis.cost.regional_loader import RegionalCostLoader
    from worldenergydata.field_development import well_economics as we

    cfg = yaml.safe_load((REPO / "config/well_economics.yml").read_text())
    src = cfg["sources"]
    rates_dir = REPO / src["rates_dir"]
    loader = RegionalCostLoader(config_dir=rates_dir)  # explicit, not parents[7]
    revenue_map = we.load_revenue_map(REPO / src["benchmark_csv"])
    field_facts = {
        f["id"]: f for f in json.loads((REPO / src["facts_json"]).read_text())
    }
    norms_path = REPO / src["norms_json"]
    return we, cfg, loader, rates_dir, revenue_map, field_facts, norms_path


def main():
    data = json.loads(FACTS.read_text())
    fields = data["fields"]
    we, econ_cfg, loader, rates_dir, revenue_map, field_facts, norms_path = (
        _economics_context()
    )
    rows = []
    for w in data["wells"]:
        field = fields[w["field_id"]]
        well = facts_to_well(w, field)
        # --- economics card payload (issue #849) ---
        ff = field_facts.get(w["field_id"], {})
        econ = we.compute_well_economics(
            w,
            {"id": w["field_id"], "water_depth_ft": ff.get("water_depth_ft")},
            revenue=revenue_map.get(w["api"]),
            loader=loader,
            rates_dir=rates_dir,
            cfg=econ_cfg,
        )
        payload = econ.to_json()
        payload["field_id"] = w["field_id"]
        payload["norms"] = we.norms_comparison(w, w["field_id"], norms_path)
        payload["display"] = econ_cfg["display"]
        well["economics"] = payload
        fname = f"{w['field_id']}_{w['slot']}_well.html"
        html = site_nav.inject_for(
            render(well),
            "well",
            {
                "field_id": w["field_id"],
                "slot": w["slot"],
                "field_name": field["display_name"],
            },
        )
        (HERE / fname).write_text(html)
        cum = w.get("cum_oil_mmbbl") or 0
        rows.append(
            {
                "file": fname,
                "title": well["title"],
                "cum": f"{cum:g} MMbbl",
                "cum_val": cum,
            }
        )
        print(
            f"  wrote {fname}  (drill {w.get('drilling_rig_days')}/compl {w.get('completion_rig_days')} rig-days)"
        )
    (HERE / "index.html").write_text(build_index(rows))
    print(f"  wrote index.html  ({len(rows)} wells)")


if __name__ == "__main__":
    main()
