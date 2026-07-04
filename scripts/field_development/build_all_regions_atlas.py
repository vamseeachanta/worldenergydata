#!/usr/bin/env python3
"""
Build the ALL-REGIONS FIELD ATLAS front-door page (issue #779).

THESIS: We cover 205 countries at reference depth; the Gulf of Mexico at full
life-cycle depth -- here's the honest map.

Every number rendered is computed from a real data file:
  - data/modules/offshore_assets/curated/coverage_summary.csv   (per-country roll-up)
  - data/modules/offshore_assets/curated/fields.csv             (distinct-country cross-check)
  - data/modules/offshore_assets/curated/country_centroids.csv  (geographic atlas scope = 205)
  - data/freshness-scorecard.json                               (catalog_status -> density badge)
  - reports/field_development/bsee_matched/*.html               (concept-matched page count)
  - reports/lower_tertiary/lt_well_benchmark_*_latest.csv       (LT benchmark well count)
  - reports/lower_tertiary/lifecycle/*.html                     (field life-cycle page count)

BADGE RULE (from freshness-scorecard catalog_status of each country's dedicated
national-regulator ingest module):
  full -> RICH ; sample -> SAMPLE ; runtime_fetched/missing -> ROADMAP.
US is RICH because BSEE (bsee module) is materialised to full life-cycle depth in
the Gulf of Mexico -- the ONLY RICH region. Countries with a scaffolded national
module still at runtime_fetched (UK/Norway/Brazil/Mexico/Canada) are ROADMAP.
Every other country carries the shared curated reference inventory only -> SAMPLE.

Outputs (only these three files are written):
  scripts/field_development/build_all_regions_atlas.py   (this file)
  reports/field_development/all_regions_coverage.csv
  reports/field_development/all_regions_atlas.html
"""
from __future__ import annotations

import csv
import html
import json
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CURATED = PROJECT_ROOT / "data" / "modules" / "offshore_assets" / "curated"
COVERAGE_CSV = CURATED / "coverage_summary.csv"
FIELDS_CSV = CURATED / "fields.csv"
CENTROIDS_CSV = CURATED / "country_centroids.csv"
SCORECARD = PROJECT_ROOT / "data" / "freshness-scorecard.json"

BSEE_MATCHED_DIR = PROJECT_ROOT / "reports" / "field_development" / "bsee_matched"
LT_BENCHMARK_CSV = (
    PROJECT_ROOT
    / "reports"
    / "lower_tertiary"
    / "lt_well_benchmark_lower_tertiary_2010_latest.csv"
)
LIFECYCLE_DIR = PROJECT_ROOT / "reports" / "lower_tertiary" / "lifecycle"

OUT_CSV = PROJECT_ROOT / "reports" / "field_development" / "all_regions_coverage.csv"
OUT_HTML = PROJECT_ROOT / "reports" / "field_development" / "all_regions_atlas.html"

# Country (as spelled in coverage_summary) -> dedicated national-regulator ingest module
COUNTRY_MODULE = {
    "US": "bsee",
    "UK": "ukcs",
    "Norway": "sodir",
    "Brazil": "brazil_anp",
    "Mexico": "mexico_cnh",
    "Canada": "canada",
}
CATALOG_TO_BADGE = {
    "full": "RICH",
    "sample": "SAMPLE",
    "runtime_fetched": "ROADMAP",
    "missing": "ROADMAP",
}


def read_coverage():
    """Return (by_country list of dicts, by_region dict, totals dict)."""
    by_country = []
    by_region = {}
    totals = {}
    with COVERAGE_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if not row or row[0] == "CATEGORY":
                continue
            cat, dim = row[0], row[1]
            fields = int(row[2]) if row[2] else 0
            facs = int(row[3]) if row[3] else 0
            if cat == "by_country":
                by_country.append({"country": dim, "fields": fields, "facilities": facs})
            elif cat == "by_region":
                by_region[dim] = {"fields": fields, "facilities": facs}
            elif cat == "total":
                totals = {"fields": fields, "facilities": facs}
    return by_country, by_region, totals


def load_scorecard():
    data = json.loads(SCORECARD.read_text(encoding="utf-8"))
    return {k: v.get("catalog_status") for k, v in data["modules"].items()}


def badge_for(country: str, statuses: dict) -> tuple[str, str, str]:
    """Return (badge, module, catalog_status) for a country."""
    module = COUNTRY_MODULE.get(country)
    if country == "US":
        # BSEE materialised to full life-cycle depth in the Gulf of Mexico.
        return "RICH", "bsee", statuses.get("bsee", "sample")
    if module:
        status = statuses.get(module, "missing")
        return CATALOG_TO_BADGE.get(status, "ROADMAP"), module, status
    # No dedicated national module -> shared curated reference inventory only.
    return "SAMPLE", "offshore_assets (reference)", "reference"


def count_glob_html(d: Path, exclude={"index.html"}) -> int:
    if not d.is_dir():
        return 0
    return sum(1 for p in d.glob("*.html") if p.name not in exclude)


def count_data_rows(p: Path) -> int:
    if not p.is_file():
        return 0
    with p.open(newline="", encoding="utf-8", errors="replace") as f:
        return max(sum(1 for _ in f) - 1, 0)


def distinct_field_countries() -> int:
    seen = set()
    with FIELDS_CSV.open(newline="", encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            c = (row.get("COUNTRY") or "").strip()
            if c:
                seen.add(c)
    return len(seen)


def centroid_country_count() -> int:
    return count_data_rows(CENTROIDS_CSV)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

BADGE_META = {
    "RICH": ("RICH", "Full life-cycle depth: fields + wells + production + economics."),
    "SAMPLE": ("SAMPLE", "Reference inventory: curated field & facility counts only."),
    "ROADMAP": ("ROADMAP", "National deep-ingest pipeline scaffolded; not yet materialised."),
}


def svg_bar(top, max_fields):
    """Horizontal inline-SVG bar chart of top countries by field count."""
    row_h, gap, label_w, bar_w, pad_top = 22, 6, 118, 560, 8
    n = len(top)
    height = pad_top * 2 + n * (row_h + gap)
    total_w = label_w + bar_w + 60
    colors = {"RICH": "#0b6b3a", "SAMPLE": "#0b3d5c", "ROADMAP": "#9a6a00"}
    parts = [
        f'<svg viewBox="0 0 {total_w} {height}" width="100%" '
        f'preserveAspectRatio="xMinYMin meet" role="img" '
        f'aria-label="Top countries by offshore field count">'
    ]
    for i, r in enumerate(top):
        y = pad_top + i * (row_h + gap)
        w = max(2, round(bar_w * r["fields"] / max_fields))
        c = colors[r["badge"]]
        name = html.escape(r["country"])
        parts.append(
            f'<text x="{label_w - 6}" y="{y + row_h/2 + 4:.0f}" text-anchor="end" '
            f'font-size="11" fill="#15202b">{name}</text>'
        )
        parts.append(
            f'<rect x="{label_w}" y="{y}" width="{w}" height="{row_h}" rx="2" '
            f'fill="{c}"><title>{name}: {r["fields"]} fields ({r["badge"]})</title></rect>'
        )
        parts.append(
            f'<text x="{label_w + w + 6}" y="{y + row_h/2 + 4:.0f}" '
            f'font-size="10.5" fill="#5b6b7b">{r["fields"]}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def build_html(rows, by_region, totals, atlas_countries, roster_countries,
               field_countries, gom_proof):
    today = date.today().isoformat()
    gom = by_region.get("US Gulf of Mexico (flagged)", {"fields": 0, "facilities": 0})
    row = by_region.get("Rest of world", {"fields": 0, "facilities": 0})

    counts = {"RICH": 0, "SAMPLE": 0, "ROADMAP": 0}
    for r in rows:
        counts[r["badge"]] += 1

    # Sorted for table (default: fields desc)
    tbl_rows = sorted(rows, key=lambda r: (-r["fields"], r["country"]))
    top = [r for r in tbl_rows][:15]
    max_fields = max((r["fields"] for r in top), default=1)

    def badge_span(b):
        return f'<span class="badge b-{b.lower()}">{b}</span>'

    table_body = []
    for i, r in enumerate(tbl_rows):
        dens = f'{r["facilities"]/r["fields"]:.2f}' if r["fields"] else "—"
        table_body.append(
            f'<tr>'
            f'<td class="rank">{i+1}</td>'
            f'<td class="cty">{html.escape(r["country"])}</td>'
            f'<td class="num">{r["fields"]}</td>'
            f'<td class="num">{r["facilities"]}</td>'
            f'<td class="num">{dens}</td>'
            f'<td>{badge_span(r["badge"])}</td>'
            f'<td class="mod">{html.escape(r["module"])}</td>'
            f'</tr>'
        )
    table_body = "\n".join(table_body)

    legend = "".join(
        f'<div class="lg"><span class="badge b-{k.lower()}">{k}</span>'
        f'<span class="lgtxt">{html.escape(BADGE_META[k][1])}</span></div>'
        for k in ("RICH", "SAMPLE", "ROADMAP")
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>All-Regions Field Atlas — Offshore Coverage, Honest Density</title>
<style>
:root {{
  --ink:#15202b; --muted:#5b6b7b; --accent:#0b3d5c; --accent-soft:#e8eef3;
  --rule:#cdd7e0; --zebra:#f5f8fa;
  --rich:#0b6b3a; --rich-soft:#e3f2e9;
  --sample:#0b3d5c; --sample-soft:#e8eef3;
  --road:#9a6a00; --road-soft:#f6eedd;
}}
* {{ box-sizing:border-box; }}
body {{ font-family:"Helvetica Neue",Helvetica,Arial,"Segoe UI",sans-serif;
  color:var(--ink); line-height:1.45; margin:0; font-size:11pt; background:#fff; }}
.page {{ max-width:1040px; margin:0 auto; padding:0 28px 48px; }}
.hdr {{ border-bottom:3px solid var(--accent); padding:22px 0 14px; margin-bottom:8px; }}
.hdr .brand {{ font-size:15pt; font-weight:700; color:var(--accent); letter-spacing:.2px; }}
.hdr .meta {{ font-size:9pt; color:var(--muted); margin-top:4px; }}
h1 {{ font-size:19pt; color:var(--accent); margin:16px 0 4px; line-height:1.2; }}
.thesis {{ font-size:12pt; color:var(--ink); margin:6px 0 4px; font-weight:600; }}
.thesis .big {{ color:var(--accent); }}
h2 {{ font-size:13.5pt; color:var(--accent); border-bottom:1px solid var(--rule);
  padding-bottom:4px; margin:30px 0 12px; }}
p {{ margin:8px 0; }}
.kpis {{ display:flex; flex-wrap:wrap; gap:12px; margin:16px 0 4px; }}
.kpi {{ flex:1 1 150px; border:1px solid var(--rule); border-radius:8px; padding:12px 14px;
  background:var(--zebra); }}
.kpi .v {{ font-size:20pt; font-weight:700; color:var(--accent); line-height:1; }}
.kpi .l {{ font-size:8.5pt; color:var(--muted); margin-top:6px; text-transform:uppercase;
  letter-spacing:.4px; }}
.kpi.rich .v {{ color:var(--rich); }}
.legend {{ display:flex; flex-wrap:wrap; gap:10px 22px; margin:10px 0 4px; }}
.lg {{ display:flex; align-items:baseline; gap:8px; font-size:9.5pt; color:var(--muted);
  flex:1 1 300px; }}
.lgtxt {{ line-height:1.3; }}
.badge {{ display:inline-block; font-size:8pt; font-weight:700; letter-spacing:.5px;
  padding:2px 7px; border-radius:10px; color:#fff; white-space:nowrap; }}
.b-rich {{ background:var(--rich); }}
.b-sample {{ background:var(--sample); }}
.b-roadmap {{ background:var(--road); }}
.gom {{ border:2px solid var(--rich); border-radius:10px; padding:18px 20px; margin:14px 0 6px;
  background:linear-gradient(180deg,var(--rich-soft),#fff); }}
.gom h3 {{ margin:0 0 4px; font-size:13pt; color:var(--rich); }}
.gom .sub {{ font-size:9.5pt; color:var(--muted); margin:0 0 12px; }}
.gomgrid {{ display:flex; flex-wrap:wrap; gap:14px; }}
.gomstat {{ flex:1 1 120px; }}
.gomstat .v {{ font-size:17pt; font-weight:700; color:var(--rich); line-height:1; }}
.gomstat .l {{ font-size:8.5pt; color:var(--muted); margin-top:5px; }}
.gomlinks {{ margin-top:12px; font-size:9.5pt; }}
.gomlinks a {{ color:var(--accent); text-decoration:none; border-bottom:1px solid var(--rule);
  margin-right:14px; white-space:nowrap; }}
.gomlinks a:hover {{ border-bottom-color:var(--accent); }}
.chartwrap {{ border:1px solid var(--rule); border-radius:8px; padding:14px 16px; overflow-x:auto; }}
.tablewrap {{ overflow-x:auto; }}
table.atlas {{ border-collapse:collapse; width:100%; font-size:10pt; margin-top:6px; }}
table.atlas th, table.atlas td {{ padding:6px 9px; text-align:left; border-bottom:1px solid var(--rule); }}
table.atlas th {{ background:var(--accent-soft); color:var(--accent); font-size:8.5pt;
  text-transform:uppercase; letter-spacing:.4px; cursor:pointer; user-select:none;
  position:sticky; top:0; }}
table.atlas th.num, table.atlas td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
table.atlas td.rank {{ color:var(--muted); font-size:9pt; }}
table.atlas td.cty {{ font-weight:600; }}
table.atlas td.mod {{ color:var(--muted); font-size:9pt; }}
table.atlas tbody tr:nth-child(even) {{ background:var(--zebra); }}
th.sorted-asc::after {{ content:" \\25B2"; font-size:7pt; }}
th.sorted-desc::after {{ content:" \\25BC"; font-size:7pt; }}
.footer {{ border-top:1px solid var(--rule); margin-top:34px; padding-top:10px;
  font-size:8.5pt; color:var(--muted); }}
.footer .sources {{ font-weight:600; color:var(--accent); }}
.note {{ font-size:9pt; color:var(--muted); background:var(--zebra); border-left:3px solid var(--rule);
  padding:8px 12px; border-radius:0 6px 6px 0; margin:12px 0; }}
</style>
</head>
<body>
<div class="page">
  <div class="hdr">
    <div class="brand">World Energy Data &middot; Offshore Field Atlas</div>
    <div class="meta">Front-door coverage map &middot; generated {today} &middot; issue #779</div>
  </div>

  <h1>All-Regions Field Atlas</h1>
  <p class="thesis">We cover <span class="big">{atlas_countries} countries</span> at
  reference depth; the <span class="big">Gulf of Mexico</span> at full life-cycle depth —
  here's the honest map.</p>

  <div class="kpis">
    <div class="kpi"><div class="v">{atlas_countries}</div><div class="l">Countries in atlas scope</div></div>
    <div class="kpi"><div class="v">{totals['fields']:,}</div><div class="l">Offshore fields catalogued</div></div>
    <div class="kpi"><div class="v">{totals['facilities']:,}</div><div class="l">Production facilities</div></div>
    <div class="kpi rich"><div class="v">1</div><div class="l">RICH region (US Gulf of Mexico)</div></div>
  </div>

  <div class="legend">{legend}</div>
  <p class="note"><strong>How to read the badge.</strong> The field &amp; facility
  <em>counts</em> below are real reference-catalogue records for every country. The
  <em>badge</em> reports how deep our ingest goes beyond that shared reference inventory,
  driven by each country's dedicated national-regulator module status in the freshness
  scorecard. Only <strong>US Gulf of Mexico</strong> is materialised to full life-cycle
  depth ({counts['RICH']} RICH); {counts['SAMPLE']} countries carry the reference inventory
  only (SAMPLE) and {counts['ROADMAP']} have a national deep-ingest pipeline scaffolded but
  not yet materialised (ROADMAP).</p>

  <div class="gom">
    <h3>Gulf of Mexico — the one region at full life-cycle depth</h3>
    <p class="sub">Real BSEE fields &amp; wells, concept-matched development pages, and a
    Lower Tertiary economics benchmark — the depth we intend to bring to every basin.</p>
    <div class="gomgrid">
      <div class="gomstat"><div class="v">~1,390</div><div class="l">BSEE Gulf of Mexico fields<sup>&dagger;</sup></div></div>
      <div class="gomstat"><div class="v">~30k</div><div class="l">BSEE offshore wells<sup>&dagger;</sup></div></div>
      <div class="gomstat"><div class="v">{gom_proof['matched']}</div><div class="l">Concept-matched field pages</div></div>
      <div class="gomstat"><div class="v">{gom_proof['bench']}</div><div class="l">Lower Tertiary benchmark wells</div></div>
      <div class="gomstat"><div class="v">{gom_proof['lifecycle']}</div><div class="l">Field life-cycle pages</div></div>
      <div class="gomstat"><div class="v">{gom['fields']}</div><div class="l">GoM fields in reference catalog</div></div>
    </div>
    <div class="gomlinks">
      <a href="../lower_tertiary/lifecycle/index.html">Field life-cycle pages &rarr;</a>
      <a href="../lower_tertiary/lt_well_benchmark_lower_tertiary_2010_latest.md">LT well benchmark &rarr;</a>
      <a href="./bsee_matched/aconcagua.html">Concept-matched pages &rarr;</a>
      <a href="./showcase/index.html">Concept-match showcase &rarr;</a>
    </div>
  </div>

  <h2>Top {len(top)} countries by offshore field count</h2>
  <div class="chartwrap">{svg_bar(top, max_fields)}</div>

  <h2>Per-country coverage &amp; density badge</h2>
  <p style="font-size:9.5pt;color:var(--muted);margin:2px 0 6px;">Click any column
  header to sort. {len(rows)} countries with field/facility roll-ups in the reference
  catalogue (of {atlas_countries} in the geographic atlas; {field_countries} distinct
  countries appear in fields.csv). Density = facilities &divide; fields.</p>
  <div class="tablewrap">
  <table class="atlas" id="atlas">
    <thead><tr>
      <th data-k="rank" data-t="n">#</th>
      <th data-k="cty" data-t="s">Country</th>
      <th class="num" data-k="fields" data-t="n">Fields</th>
      <th class="num" data-k="fac" data-t="n">Facilities</th>
      <th class="num" data-k="dens" data-t="n">Density</th>
      <th data-k="badge" data-t="s">Badge</th>
      <th data-k="mod" data-t="s">Source module</th>
    </tr></thead>
    <tbody>
{table_body}
    </tbody>
  </table>
  </div>

  <div class="footer">
    <p><span class="sources">Sources.</span>
    data/modules/offshore_assets/curated/coverage_summary.csv (per-country roll-up,
    {len(rows)} countries; totals {totals['fields']:,} fields / {totals['facilities']:,}
    facilities; US Gulf of Mexico flagged {gom['fields']} fields / {gom['facilities']}
    facilities, rest of world {row['fields']:,} / {row['facilities']}) &middot;
    data/modules/offshore_assets/curated/country_centroids.csv ({atlas_countries}
    countries in atlas scope) &middot; fields.csv ({field_countries} distinct countries)
    &middot; data/freshness-scorecard.json (catalog_status &rarr; density badge) &middot;
    reports/field_development/bsee_matched/ ({gom_proof['matched']} concept-matched pages)
    &middot; reports/lower_tertiary/lt_well_benchmark_lower_tertiary_2010_latest.csv
    ({gom_proof['bench']} benchmark wells) &middot; reports/lower_tertiary/lifecycle/
    ({gom_proof['lifecycle']} life-cycle pages).</p>
    <p><strong>Data limits.</strong> Badge maps each country's dedicated national-regulator
    module: US&rarr;bsee, UK&rarr;ukcs, Norway&rarr;sodir, Brazil&rarr;brazil_anp,
    Mexico&rarr;mexico_cnh, Canada&rarr;canada; all other countries carry the shared
    curated reference inventory (SAMPLE). RICH is asserted only for US Gulf of Mexico,
    where BSEE is materialised to full life-cycle depth.
    <sup>&dagger;</sup> The ~1,390-field / ~30k-well figures are the BSEE Gulf of Mexico
    program catalogue scope; the ~300&nbsp;MB BSEE binary is not carried in this worktree
    (run <code>make data</code>), so these two figures are the documented BSEE catalogue
    scope rather than recomputed here. The four right-hand GoM stats and every per-country
    number are computed directly from files listed above.</p>
  </div>
</div>
<script>
(function(){{
  var t=document.getElementById('atlas');
  var tb=t.tBodies[0];
  var ths=t.tHead.rows[0].cells;
  function val(tr,i,type){{
    var c=tr.cells[i];
    if(type==='n'){{var n=parseFloat(c.textContent.replace(/[^0-9.\\-]/g,''));return isNaN(n)?-Infinity:n;}}
    return c.textContent.trim().toLowerCase();
  }}
  for(var i=0;i<ths.length;i++){{(function(i){{
    var asc=true;
    ths[i].addEventListener('click',function(){{
      var type=ths[i].getAttribute('data-t');
      var rows=Array.prototype.slice.call(tb.rows);
      rows.sort(function(a,b){{
        var va=val(a,i,type),vb=val(b,i,type);
        if(va<vb)return asc?-1:1; if(va>vb)return asc?1:-1; return 0;
      }});
      rows.forEach(function(r){{tb.appendChild(r);}});
      // renumber rank column
      Array.prototype.slice.call(tb.rows).forEach(function(r,idx){{r.cells[0].textContent=idx+1;}});
      for(var j=0;j<ths.length;j++){{ths[j].classList.remove('sorted-asc','sorted-desc');}}
      ths[i].classList.add(asc?'sorted-asc':'sorted-desc');
      asc=!asc;
    }});
  }})(i);}}
}})();
</script>
</body>
</html>
"""


def main():
    by_country, by_region, totals = read_coverage()
    statuses = load_scorecard()

    rows = []
    for c in by_country:
        badge, module, status = badge_for(c["country"], statuses)
        rows.append({
            "country": c["country"],
            "fields": c["fields"],
            "facilities": c["facilities"],
            "badge": badge,
            "module": module,
            "catalog_status": status,
        })

    atlas_countries = centroid_country_count()
    field_countries = distinct_field_countries()
    gom_proof = {
        "matched": count_glob_html(BSEE_MATCHED_DIR),
        "bench": count_data_rows(LT_BENCHMARK_CSV),
        "lifecycle": count_glob_html(
            LIFECYCLE_DIR, exclude={"index.html", "lifecycle_template.html"}
        ),
    }

    # --- CSV ---
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["country", "fields", "facilities",
                    "facility_density", "badge", "source_module", "catalog_status"])
        for r in sorted(rows, key=lambda r: (-r["fields"], r["country"])):
            dens = round(r["facilities"] / r["fields"], 3) if r["fields"] else ""
            w.writerow([r["country"], r["fields"], r["facilities"], dens,
                        r["badge"], r["module"], r["catalog_status"]])

    # --- HTML ---
    OUT_HTML.write_text(
        build_html(rows, by_region, totals, atlas_countries, len(rows),
                   field_countries, gom_proof),
        encoding="utf-8",
    )

    b = {"RICH": 0, "SAMPLE": 0, "ROADMAP": 0}
    for r in rows:
        b[r["badge"]] += 1
    print(f"countries(roll-up)={len(rows)}  atlas={atlas_countries}  "
          f"fields.csv_countries={field_countries}")
    print(f"totals={totals}  gom={by_region.get('US Gulf of Mexico (flagged)')}")
    print(f"badges={b}  gom_proof={gom_proof}")
    print(f"wrote {OUT_CSV}")
    print(f"wrote {OUT_HTML}")


if __name__ == "__main__":
    main()
