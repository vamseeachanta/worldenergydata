# ABOUTME: Build the deterministic well drilling-&-completion report HTML.
# ABOUTME: Reads the frozen V30 WAR-derived day counts and renders a static page.
"""Build the **well completion & drilling-days** report — a single self-contained
HTML page summarising, per Lower-Tertiary deepwater field, the drilling and
completion durations reconstructed from BSEE Well Activity Reports (WAR).

The numbers are read from one frozen, committed reference workbook
(``docs/modules/bsee/analysis/production/FDAS_V30/drilling_and_completion_days.xlsx``)
produced by the V30 SME drilling/completion-days methodology — so the published
page is deterministic and reproducible: same workbook in, byte-identical HTML out.

This generator may use openpyxl (a dev/build dependency); the published site
builder (``scripts/build_pages.py``) only ever *copies* the frozen HTML it emits,
so the Pages build stays stdlib-only.

Run:
    .venv/bin/python scripts/completion/build_completion_report.py

Output: reports/completion/index.html (self-contained, no external assets).
"""

from __future__ import annotations

import html
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import openpyxl

_REPO = Path(__file__).resolve().parents[2]
_SRC = (
    _REPO
    / "docs/modules/bsee/analysis/production/FDAS_V30/drilling_and_completion_days.xlsx"
)
_OUT = _REPO / "reports" / "completion" / "index.html"

# Field display order: largest well populations first, then alphabetical — fixed
# so the rendered table is deterministic regardless of dict iteration order.


def _load() -> list[dict]:
    wb = openpyxl.load_workbook(_SRC, data_only=True)
    ws = wb["Sheet1"]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    # A row is a real well record iff it carries an API well number (col 3).
    return [dict(zip(header, r)) for r in rows[1:] if r[3]]


def _num(values: list) -> list[float]:
    return [v for v in values if isinstance(v, (int, float))]


def _spud_year(value) -> int | None:
    if isinstance(value, datetime):
        return value.year
    if isinstance(value, str) and value.strip():
        try:
            return datetime.strptime(value.strip(), "%m/%d/%Y").year
        except ValueError:
            return None
    return None


def _stat_block(values: list[float]) -> dict:
    vals = _num(values)
    nz = [v for v in vals if v > 0]
    return {
        "n": len(vals),
        "mean": statistics.mean(vals) if vals else 0,
        "median": statistics.median(vals) if vals else 0,
        "min": min(vals) if vals else 0,
        "max": max(vals) if vals else 0,
        "zeros": sum(1 for v in vals if v == 0),
        "median_nz": statistics.median(nz) if nz else 0,
    }


def compute(data: list[dict]) -> dict:
    fields = sorted({d["LEASE_NAME"] for d in data})
    leases = {d["SURF_LEASE_NUM"] for d in data}
    years = [y for y in (_spud_year(d["WELL_SPUD_DATE"]) for d in data) if y]
    wd = _num([d["WATER_DEPTH"] for d in data])
    md = _num([d["MAX_BH_TOTAL_MD"] for d in data])
    tvd = _num([d["MAX_WELL_BORE_TVD"] for d in data])

    by_field = defaultdict(list)
    for d in data:
        by_field[d["LEASE_NAME"]].append(d)

    field_rows = []
    for f in fields:
        g = by_field[f]
        dd = _stat_block([x["DRILLING_DAYS"] for x in g])
        cd = _stat_block([x["COMPLETION_DAYS"] for x in g])
        g_wd = _num([x["WATER_DEPTH"] for x in g])
        field_rows.append(
            {
                "field": f,
                "wells": len(g),
                "drill_median": dd["median"],
                "drill_mean": dd["mean"],
                "comp_median": cd["median"],
                "comp_mean": cd["mean"],
                "water_depth": max(g_wd) if g_wd else 0,
            }
        )
    # Largest populations first, then alphabetical — deterministic ordering.
    field_rows.sort(key=lambda r: (-r["wells"], r["field"]))

    # Deepest well by measured depth, for a concrete extreme.
    deepest = max(
        (d for d in data if isinstance(d["MAX_BH_TOTAL_MD"], (int, float))),
        key=lambda d: d["MAX_BH_TOTAL_MD"],
        default=None,
    )

    return {
        "wells": len(data),
        "fields": len(fields),
        "leases": len(leases),
        "year_min": min(years) if years else None,
        "year_max": max(years) if years else None,
        "wd_min": min(wd) if wd else 0,
        "wd_max": max(wd) if wd else 0,
        "md_max": max(md) if md else 0,
        "tvd_max": max(tvd) if tvd else 0,
        "drill": _stat_block([d["DRILLING_DAYS"] for d in data]),
        "comp": _stat_block([d["COMPLETION_DAYS"] for d in data]),
        "field_rows": field_rows,
        "deepest": deepest,
    }


_STYLE = """
  :root{--bg:#0d1117;--panel:#161b22;--line:#30363d;--ink:#e6edf3;--mut:#8b949e;
        --accent:#3b82f6;--ok:#3fb950;--warn:#d29922}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
       font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
  .wrap{max-width:1120px;margin:0 auto;padding:0 22px}
  header{padding:54px 0 30px;border-bottom:1px solid var(--line)}
  h1{margin:0 0 6px;font-size:30px;letter-spacing:-.4px}
  .sub{color:var(--mut);font-size:16px;max-width:800px}
  .tag{display:inline-block;margin-top:14px;padding:3px 10px;border:1px solid var(--line);
       border-radius:20px;color:var(--mut);font-size:12.5px}
  h2{font-size:18px;margin:38px 0 14px;letter-spacing:-.2px}
  .stats{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:14px;margin-top:6px}
  .stat{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 18px}
  .stat .v{font-size:26px;font-weight:650;letter-spacing:-.5px;
           font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
  .stat .k{color:var(--mut);font-size:12.5px;margin-top:4px}
  table{width:100%;border-collapse:collapse;font-size:13.5px;margin-top:6px;
        background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden}
  th,td{padding:9px 12px;text-align:left;border-bottom:1px solid var(--line)}
  th{background:#1c2330;color:var(--mut);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.4px}
  tr:last-child td{border-bottom:none}
  td.val,th.val{text-align:right;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
  .note{color:var(--mut);font-size:13px;margin:10px 0 0}
  footer{margin:46px 0 30px;padding-top:22px;border-top:1px solid var(--line);
         color:var(--mut);font-size:12.5px}
  a{color:var(--accent);text-decoration:none}
  code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;background:#1c2330;
       padding:1px 5px;border-radius:4px;font-size:12.5px}
"""


def _stat(value: str, label: str) -> str:
    return f'<div class="stat"><div class="v">{value}</div><div class="k">{label}</div></div>'


def render(c: dict) -> str:
    yr = (
        f"{c['year_min']}&ndash;{c['year_max']}"
        if c["year_min"] and c["year_max"]
        else "&mdash;"
    )
    stats = "".join(
        [
            _stat(f"{c['wells']}", "deepwater wells (WAR records)"),
            _stat(f"{c['fields']}", "Lower-Tertiary fields"),
            _stat(f"{c['leases']}", "federal surface leases"),
            _stat(yr, "spud-year span"),
            _stat(f"{c['drill']['median']:.0f} d", "median drilling time"),
            _stat(f"{c['comp']['median']:.0f} d", "median completion time"),
            _stat(
                f"{c['wd_min']:,.0f}&ndash;{c['wd_max']:,.0f} ft", "water-depth range"
            ),
            _stat(f"{c['md_max']:,.0f} ft", "deepest well (measured depth)"),
        ]
    )

    field_rows = "".join(
        f"<tr><td>{html.escape(r['field'])}</td>"
        f'<td class="val">{r["wells"]}</td>'
        f'<td class="val">{r["drill_median"]:.0f}</td>'
        f'<td class="val">{r["drill_mean"]:.1f}</td>'
        f'<td class="val">{r["comp_median"]:.0f}</td>'
        f'<td class="val">{r["comp_mean"]:.1f}</td>'
        f'<td class="val">{r["water_depth"]:,.0f}</td></tr>'
        for r in c["field_rows"]
    )

    dz = c["drill"]["zeros"]
    cz = c["comp"]["zeros"]
    deepest = c["deepest"]
    deepest_txt = ""
    if deepest:
        deepest_txt = (
            f" The deepest borehole in the set is "
            f"{html.escape(str(deepest['LEASE_NAME']))} well "
            f"<code>{html.escape(str(deepest['API_WELL_NUMBER']))}</code> at "
            f"{deepest['MAX_BH_TOTAL_MD']:,.0f} ft measured / "
            f"{deepest['MAX_WELL_BORE_TVD']:,.0f} ft TVD."
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>worldenergydata — Well Drilling &amp; Completion Days</title>
<style>{_STYLE}</style>
</head>
<body>
<header><div class="wrap">
  <h1>Well Drilling &amp; Completion Days</h1>
  <div class="sub">Drilling and completion durations reconstructed from BSEE Well
  Activity Reports for {c['wells']} wells across the {c['fields']} Lower-Tertiary
  deepwater fields &mdash; spud-to-total-depth (drilling) and total-depth-to-final-
  completion-activity (completion), with per-well depth and water-depth context.</div>
  <span class="tag">BSEE Well Activity Reports &middot; V30 drilling/completion-days methodology &middot; deterministic from a frozen reference</span>
</div></header>

<div class="wrap">

  <h2>Portfolio at a glance</h2>
  <div class="stats">{stats}</div>

  <h2>By field</h2>
  <p class="note">Drilling days = spud date &rarr; total-depth date. Completion days =
  total-depth date &rarr; last completion activity. Medians are the headline figure
  (robust to the sidetracks and recompletions whose WAR milestones coincide on a
  single day); means are shown alongside.{deepest_txt}</p>
  <div class="table-wrap"><table>
    <thead><tr>
      <th>Field</th><th class="val">Wells</th>
      <th class="val">Drill (med)</th><th class="val">Drill (mean)</th>
      <th class="val">Compl (med)</th><th class="val">Compl (mean)</th>
      <th class="val">Water depth (ft)</th>
    </tr></thead>
    <tbody>{field_rows}</tbody>
  </table></div>

  <h2>How the durations are measured</h2>
  <p class="note">Each well's milestones come from its BSEE Well Activity Reports:
  the spud date, the total-depth date, and the last recorded completion activity.
  Drilling and completion days are the calendar spans between them. Records where a
  milestone is missing or the span is zero ({dz} wells show zero drilling days,
  {cz} show zero completion days &mdash; typically sidetracks or recompletions that
  open and finish an interval the same day) are kept in the population and reported
  as-is rather than dropped or estimated, which is why the mean sits well above the
  median for several fields.</p>

  <h2>Provenance</h2>
  <p class="note">Figures are computed deterministically from one frozen, committed
  reference workbook,
  <a href="https://github.com/vamseeachanta/worldenergydata/blob/main/docs/modules/bsee/analysis/production/FDAS_V30/drilling_and_completion_days.xlsx"><code>docs/&hellip;/FDAS_V30/drilling_and_completion_days.xlsx</code></a>,
  itself derived from public BSEE Well Activity Reports under the V30 drilling/
  completion-days methodology. The page is regenerated by
  <code>scripts/completion/build_completion_report.py</code> &mdash; same workbook
  in, byte-identical HTML out.</p>

  <footer>
    Part of <a href="../capabilities/">worldenergydata &middot; Open Energy-Data
    Capabilities</a>. Drilling/completion durations are observational WAR-derived
    spans for US Gulf of Mexico / Gulf of America Lower-Tertiary deepwater wells;
    they are not predictive estimates.
  </footer>
</div>
</body>
</html>
"""


def main() -> None:
    data = _load()
    c = compute(data)
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(render(c), encoding="utf-8")
    print(
        f"Wrote {_OUT.relative_to(_REPO)} — {c['wells']} wells, {c['fields']} fields, "
        f"median drill {c['drill']['median']:.0f}d / completion {c['comp']['median']:.0f}d."
    )


if __name__ == "__main__":
    main()
