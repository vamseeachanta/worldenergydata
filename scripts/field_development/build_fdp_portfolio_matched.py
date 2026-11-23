# ABOUTME: Generate the BSEE-matched FDP portfolio (per-field HTML + index + json).
# ABOUTME: Issue #567 — engine recommendation vs as-built concept across matched GoM.
"""
Build an FDP portfolio for the BSEE-matched Gulf-of-Mexico fields.

Reads the matched SubseaIQ→BSEE block crosswalk, builds a host-enriched
:class:`FieldConcept` per field (``concept_type`` = the as-built host concept),
runs the recommendation engine on a *blind probe* (answer stripped), and renders:

* one self-contained FDP HTML per field (``<slug>.html``),
* an ``index.html`` with a sortable comparison table, and
* a ``_summary.json`` (per-field actual vs recommended + aggregate top-1 rate).

The data layer lives in
:mod:`worldenergydata.field_development.portfolio_matched` (unit-tested); this
script is the HTML/IO glue.

Run:
    .venv/bin/python scripts/field_development/build_fdp_portfolio_matched.py
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from worldenergydata.field_development import build_fdp_html
from worldenergydata.field_development.portfolio_matched import (
    PortfolioRow,
    build_portfolio,
    summarize,
)

OUT_DIR = Path(__file__).parents[2] / "reports" / "field_development" / "bsee_matched"


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _pretty(value: str | None) -> str:
    """Render a concept enum value for humans (``semisub_fps`` -> ``Semisub Fps``)."""
    return value.replace("_", " ").title() if value else "—"


def _actuals(row: PortfolioRow) -> dict:
    """Known real figures shown beside the engine estimate on a field page."""
    actual = row.actual.value if row.actual else None
    rec = row.recommended.value if row.recommended else None
    out = {
        "Block": row.match.block or "—",
        "BSEE code": row.match.bsee_block_code or "—",
        "Operator": row.match.operator or "—",
        "Concept (as built)": _pretty(actual),
        "Engine top pick": _pretty(rec),
    }
    if actual is not None:
        out["Match"] = "✓ match" if row.is_match else "✗ differs"
    return out


def _narrative(row: PortfolioRow) -> str:
    rec = _pretty(row.recommended.value if row.recommended else None)
    if row.actual is None:
        return (
            f"No as-built concept is recorded for this matched field. The engine's "
            f"top recommendation on the field inputs is {rec} (Concept-Select "
            f"fidelity)."
        )
    actual = _pretty(row.actual.value)
    if row.is_match:
        return (
            f"The engine's top recommendation ({rec}) matches the concept actually "
            f"built ({actual}). The recommendation is produced on a blind probe — "
            f"the as-built concept is stripped before scoring — so the agreement "
            f"reflects the depth, basin and host-proximity signal, not the answer."
        )
    return (
        f"The engine's top recommendation ({rec}) differs from the concept actually "
        f"built ({actual}). The recommendation is produced on a blind probe (the "
        f"as-built concept stripped before scoring); the shortlist below shows where "
        f"the built concept ranks. Divergence is expected where the real choice "
        f"turned on data outside the engine's inputs (reserves, schedule, "
        f"operator preference)."
    )


def _row_html(row: PortfolioRow) -> str:
    actual = row.actual.value if row.actual else None
    rec = row.recommended.value if row.recommended else None
    if actual is None:
        match_cell = '<td data-sort="2" class="na">n/a</td>'
    elif row.is_match:
        match_cell = '<td data-sort="1" class="yes">Y</td>'
    else:
        match_cell = '<td data-sort="0" class="no">N</td>'
    depth = row.concept.water_depth_m
    depth_sort = depth if depth is not None else -1
    depth_txt = f"{depth:g} m" if depth is not None else "—"
    return (
        f'<tr><td><a href="{_slug(row.match.og_field_name)}.html">'
        f"{html.escape(row.match.og_field_name)}</a></td>"
        f"<td>{html.escape(row.match.block or '—')}</td>"
        f"<td>{html.escape(row.match.operator or '—')}</td>"
        f'<td data-sort="{depth_sort:g}">{depth_txt}</td>'
        f"<td>{html.escape(_pretty(actual))}</td>"
        f"<td>{html.escape(_pretty(rec))}</td>"
        f"{match_cell}</tr>"
    )


_INDEX_CSS = """
body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f4f6f9;
color:#1a2330}.wrap{max-width:1100px;margin:0 auto;padding:24px}
h1{font-size:24px;margin:0 0 4px}.sub{color:#5b6b80}
.cards{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0}
.card{background:#fff;border:1px solid #dde4ee;border-radius:8px;padding:10px 14px;
min-width:120px}.card .k{font-size:11px;color:#6b7a90;text-transform:uppercase}
.card .v{font-size:22px;font-weight:600}
table{border-collapse:collapse;width:100%;background:#fff;font-size:13px}
th,td{border:1px solid #dde4ee;padding:7px 10px;text-align:left}
th{background:#eef2f7;cursor:pointer;user-select:none}th:hover{background:#e2e9f2}
a{color:#234e78}.yes{color:#2c7a3f;font-weight:600}.no{color:#a4441a;font-weight:600}
.na{color:#8a97a8}
"""

_SORT_JS = """
document.querySelectorAll('th').forEach(function(th,i){th.addEventListener('click',
function(){var tb=th.closest('table').tBodies[0];var rows=[].slice.call(tb.rows);
var asc=th.dataset.asc!=='1';th.dataset.asc=asc?'1':'0';
rows.sort(function(a,b){var x=a.cells[i].dataset.sort||a.cells[i].innerText;
var y=b.cells[i].dataset.sort||b.cells[i].innerText;var nx=parseFloat(x),ny=parseFloat(y);
if(!isNaN(nx)&&!isNaN(ny)){x=nx;y=ny;}return (x>y?1:x<y?-1:0)*(asc?1:-1);});
rows.forEach(function(r){tb.appendChild(r);});});});
"""


def build_index(rows: list[PortfolioRow], summary: dict) -> str:
    body = "".join(_row_html(r) for r in rows)
    rate = summary["top1_match_rate"]
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>FDP Portfolio — BSEE-matched Gulf of Mexico</title>
<style>{_INDEX_CSS}</style></head><body><div class="wrap">
<h1>Field Development Plan Portfolio — BSEE-matched Gulf of Mexico</h1>
<p class="sub">{summary['n_total']} SubseaIQ fields that crosswalk to a real BSEE
block. For each, the worldenergydata field-development engine (epic #567,
calibration v2: basin prior + host enrichment) recommends a concept from the
field inputs on a <b>blind probe</b> — the as-built concept is stripped before
scoring — and we compare its top pick to what was actually built.</p>
<div class="cards">
<div class="card"><div class="k">Matched fields</div>
<div class="v">{summary['n_total']}</div></div>
<div class="card"><div class="k">With as-built concept</div>
<div class="v">{summary['n_with_actual']}</div></div>
<div class="card"><div class="k">Top-1 matches</div>
<div class="v">{summary['n_matched']}</div></div>
<div class="card"><div class="k">Top-1 match rate</div>
<div class="v">{rate:.0%}</div></div>
</div>
<p class="sub" style="font-size:12px">Click any header to sort. Match rate is over
the {summary['n_with_actual']} fields with a recorded as-built concept.</p>
<table><thead><tr><th>Field</th><th>Block</th><th>Operator</th>
<th>Water depth</th><th>Concept (as built)</th><th>Engine top pick</th>
<th>Match</th></tr></thead><tbody>{body}</tbody></table>
<p class="sub" style="font-size:11px;margin-top:20px">SubseaIQ field catalog
(~2014) + BSEE block crosswalk. Recommendations are Concept-Select / FEL-1
fidelity, not sanctioned designs.</p>
<script>{_SORT_JS}</script></div></body></html>"""


def main() -> None:
    rows = build_portfolio()
    summary = summarize(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for row in rows:
        page = build_fdp_html(
            row.concept,
            actuals=_actuals(row),
            narrative=_narrative(row),
            title=f"Field Development Plan — {row.match.og_field_name}",
        )
        (OUT_DIR / f"{_slug(row.match.og_field_name)}.html").write_text(
            page, encoding="utf-8"
        )
    (OUT_DIR / "index.html").write_text(build_index(rows, summary), encoding="utf-8")
    (OUT_DIR / "_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(
        f"wrote {summary['n_total']} FDPs + index to {OUT_DIR} "
        f"(top-1 match {summary['top1_match_rate']:.0%} over "
        f"{summary['n_with_actual']} fields with an as-built concept)"
    )


if __name__ == "__main__":
    main()
