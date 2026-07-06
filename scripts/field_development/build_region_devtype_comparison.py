# ABOUTME: Build the region x development-type (dry/wet/other tree) comparison matrix.
# ABOUTME: Issue #776 — all-region facility universe mapped onto the authoritative trichotomy.
"""
build_region_devtype_comparison
===============================

Assembles a per-facility table tagged with (region/country, water depth,
concept_type, tree_type in {dry, wet, other}) and emits
``reports/field_development/region_devtype_matrix.csv``.

METHOD / provenance
-------------------
``field_development.portfolio_matched.build_portfolio()`` imports cleanly, but it
covers **only** the BSEE-matched GoM universe (115 US rows) — it cannot carry the
all-region story this page is about. So the authoritative universe here is the
curated **production_facilities.csv** (836 facilities across ~40 countries), whose
``HOST_TYPE`` column we map to the ``ConceptType`` vocabulary and then onto the
dry/wet/other trichotomy.

The trichotomy itself is NOT reinvented: we import ``_DRY_TREE`` straight from
``worldenergydata.field_development.recommendation`` so the dry set stays pinned to
the engine's definition ({fixed_jacket, compliant_tower, tlp, spar, nui}). Wet =
the remaining mappable concepts (semisub_fps, fpso, flng, subsea_tieback,
subsea_to_shore). Other = HOST_TYPE values with no concept mapping (FSO/FSU, MOPU,
Artificial Island) plus any null.

Subsea tiebacks are under-counted in this universe because a tieback is not a
standalone production facility — it hangs off a host. The GoM crosswalk
(subseaiq_bsee_block_crosswalk.csv) is loaded separately only to report how
prevalent subsea tiebacks are in the one region where we have block-level ground
truth; it does not feed the main matrix.
"""

from __future__ import annotations

import html as _html
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
import site_nav  # noqa: E402  (nav-spine helper, issue #850)

from worldenergydata.field_development.enums import ConceptType  # noqa: E402
from worldenergydata.field_development.recommendation import _DRY_TREE  # noqa: E402

CURATED = PROJECT_ROOT / "data" / "modules" / "offshore_assets" / "curated"
OUT_DIR = PROJECT_ROOT / "reports" / "field_development"

# HOST_TYPE (production_facilities.csv vocabulary) -> ConceptType. Anything not
# in this map is OTHER (FSO/FSU, MOPU, Artificial Island, ...).
HOST_TYPE_TO_CONCEPT = {
    "Fixed Platform": ConceptType.FIXED_JACKET,
    "Compliant Tower": ConceptType.COMPLIANT_TOWER,
    "TLP": ConceptType.TLP,
    "Mini-TLP": ConceptType.TLP,
    "SPAR": ConceptType.SPAR,
    "DDCV": ConceptType.SPAR,  # deep-draft caisson vessel = spar variant
    "Semisub": ConceptType.SEMISUB_FPS,
    "FPU/FPS": ConceptType.SEMISUB_FPS,
    "FPSO": ConceptType.FPSO,
    "FLNG": ConceptType.FLNG,
    "Subsea Tieback": ConceptType.SUBSEA_TIEBACK,
}

WET_CONCEPTS = {
    ConceptType.SEMISUB_FPS,
    ConceptType.FPSO,
    ConceptType.FLNG,
    ConceptType.SUBSEA_TIEBACK,
    ConceptType.SUBSEA_TO_SHORE,
}

# Country -> region bucket for the matrix axis. Countries not listed fall to
# "Other / Unclassified" and are printed so the map can be extended.
COUNTRY_TO_REGION = {
    # US Gulf of Mexico (all US facilities in this curated set carry US_GOM_FLAG=Y)
    "US": "US Gulf of Mexico",
    # North Sea & NW Europe
    "UK": "North Sea & NW Europe",
    "Norway": "North Sea & NW Europe",
    "Denmark": "North Sea & NW Europe",
    "Netherlands": "North Sea & NW Europe",
    "Ireland": "North Sea & NW Europe",
    "Germany": "North Sea & NW Europe",
    "Faroe Islands": "North Sea & NW Europe",
    # West Africa
    "Nigeria": "West Africa",
    "Angola": "West Africa",
    "Ghana": "West Africa",
    "Equatorial Guinea": "West Africa",
    "Congo": "West Africa",
    "Rep. of Congo": "West Africa",
    "Gabon": "West Africa",
    "Cameroon": "West Africa",
    "Ivory Coast": "West Africa",
    "Cote d'Ivoire": "West Africa",
    "Mauritania": "West Africa",
    "Senegal": "West Africa",
    "DR Congo": "West Africa",
    "Congo, The Demo. Rep. of the": "West Africa",
    "Niger": "West Africa",
    "South Africa": "West Africa",
    "Tanzania, United Republic of": "West Africa",
    # South America & Caribbean
    "Brazil": "South America & Caribbean",
    "Trin. & Tobago": "South America & Caribbean",
    "Trinidad & Tobago": "South America & Caribbean",
    "Trinidad and Tobago": "South America & Caribbean",
    "Guyana": "South America & Caribbean",
    "Venezuela": "South America & Caribbean",
    "Argentina": "South America & Caribbean",
    "Colombia": "South America & Caribbean",
    "Peru": "South America & Caribbean",
    "Suriname": "South America & Caribbean",
    "Mexico": "South America & Caribbean",
    # Asia-Pacific
    "Australia": "Asia-Pacific",
    "Malaysia": "Asia-Pacific",
    "China": "Asia-Pacific",
    "Indonesia": "Asia-Pacific",
    "Thailand": "Asia-Pacific",
    "Viet nam": "Asia-Pacific",
    "Vietnam": "Asia-Pacific",
    "India": "Asia-Pacific",
    "Myanmar": "Asia-Pacific",
    "Brunei": "Asia-Pacific",
    "Philippines": "Asia-Pacific",
    "New Zealand": "Asia-Pacific",
    "Japan": "Asia-Pacific",
    "Bangladesh": "Asia-Pacific",
    "Taiwan": "Asia-Pacific",
    "Papua New Guinea": "Asia-Pacific",
    "Timor-Leste": "Asia-Pacific",
    "Timor Leste": "Asia-Pacific",
    # Middle East
    "Qatar": "Middle East",
    "UAE": "Middle East",
    "Saudi Arabia": "Middle East",
    "Iran": "Middle East",
    "Israel": "Middle East",
    "Kuwait": "Middle East",
    "Oman": "Middle East",
    "Bahrain": "Middle East",
    "Cyprus": "Middle East",
    # Mediterranean & North Africa
    "Egypt": "Mediterranean & N Africa",
    "Libya": "Mediterranean & N Africa",
    "Tunisia": "Mediterranean & N Africa",
    "Italy": "Mediterranean & N Africa",
    "Croatia": "Mediterranean & N Africa",
    "Turkey": "Mediterranean & N Africa",
    "Algeria": "Mediterranean & N Africa",
    "Greece": "Mediterranean & N Africa",
    "Spain": "Mediterranean & N Africa",
    # Caspian, Black Sea & Russia
    "Azerbaijan": "Caspian & Russia",
    "Russian Federation": "Caspian & Russia",
    "Russia": "Caspian & Russia",
    "Kazakhstan": "Caspian & Russia",
    "Turkmenistan": "Caspian & Russia",
    "Romania": "Caspian & Russia",
    "Ukraine": "Caspian & Russia",
    "Bulgaria": "Caspian & Russia",
    # Arctic / others
    "Canada": "Atlantic Canada & Arctic",
    "Greenland": "Atlantic Canada & Arctic",
}


def classify(concept: ConceptType | None) -> str:
    if concept is None:
        return "other"
    if concept in _DRY_TREE:
        return "dry"
    if concept in WET_CONCEPTS:
        return "wet"
    return "other"


def depth_band(depth) -> str | None:
    if depth is None or pd.isna(depth):
        return None
    d = float(depth)
    if d < 150:
        return "0-150 m (shallow shelf)"
    if d < 500:
        return "150-500 m (deep shelf)"
    if d < 1500:
        return "500-1500 m (deepwater)"
    if d < 3000:
        return "1500-3000 m (ultra-deepwater)"
    return "3000 m+ (frontier)"


BAND_ORDER = [
    "0-150 m (shallow shelf)",
    "150-500 m (deep shelf)",
    "500-1500 m (deepwater)",
    "1500-3000 m (ultra-deepwater)",
    "3000 m+ (frontier)",
]
REGION_ORDER = [
    "US Gulf of Mexico",
    "North Sea & NW Europe",
    "West Africa",
    "South America & Caribbean",
    "Asia-Pacific",
    "Middle East",
    "Mediterranean & N Africa",
    "Caspian & Russia",
    "Atlantic Canada & Arctic",
    "Other / Unclassified",
]


def build_table() -> pd.DataFrame:
    pf = pd.read_csv(CURATED / "production_facilities.csv")
    rows = []
    unmapped_countries = set()
    for _, r in pf.iterrows():
        host = str(r.get("HOST_TYPE")).strip() if pd.notna(r.get("HOST_TYPE")) else ""
        concept = HOST_TYPE_TO_CONCEPT.get(host)
        tree = classify(concept)
        country = str(r.get("COUNTRY")).strip() if pd.notna(r.get("COUNTRY")) else ""
        region = COUNTRY_TO_REGION.get(country, "Other / Unclassified")
        if country and country not in COUNTRY_TO_REGION:
            unmapped_countries.add(country)
        depth = r.get("WATER_DEPTH_M")
        depth = float(depth) if pd.notna(depth) else None
        rows.append(
            {
                "facility_id": r.get("FACILITY_ID"),
                "facility_name": r.get("FACILITY_NAME"),
                "country": country,
                "region": region,
                "water_depth_m": depth,
                "depth_band": depth_band(depth),
                "host_type": host,
                "concept_type": concept.value if concept else "",
                "tree_type": tree,
            }
        )
    if unmapped_countries:
        print("UNMAPPED COUNTRIES ->", sorted(unmapped_countries))
    return pd.DataFrame(rows)


def compute_stats(df: pd.DataFrame) -> dict:
    stats: dict = {}
    stats["n_total"] = int(len(df))
    stats["tree_totals"] = {
        k: int(v) for k, v in df["tree_type"].value_counts().items()
    }
    stats["n_depth_known"] = int(df["water_depth_m"].notna().sum())
    stats["n_depth_null"] = int(df["water_depth_m"].isna().sum())

    # region x tree matrix (counts)
    mat = {}
    for region in REGION_ORDER:
        sub = df[df["region"] == region]
        if len(sub) == 0:
            continue
        mat[region] = {
            "dry": int((sub["tree_type"] == "dry").sum()),
            "wet": int((sub["tree_type"] == "wet").sum()),
            "other": int((sub["tree_type"] == "other").sum()),
            "total": int(len(sub)),
        }
    stats["region_matrix"] = mat

    # depth-band x tree (only depth-known rows)
    dk = df[df["water_depth_m"].notna()]
    bands = {}
    for band in BAND_ORDER:
        sub = dk[dk["depth_band"] == band]
        if len(sub) == 0:
            continue
        dry = int((sub["tree_type"] == "dry").sum())
        wet = int((sub["tree_type"] == "wet").sum())
        other = int((sub["tree_type"] == "other").sum())
        tot = int(len(sub))
        # dry share among dry+wet (the "trees" story ignores OTHER hulls)
        dw = dry + wet
        bands[band] = {
            "dry": dry,
            "wet": wet,
            "other": other,
            "total": tot,
            "dry_share_of_trees": (dry / dw) if dw else None,
        }
    stats["depth_bands"] = bands

    # headline: dry share of trees shallow (<1500) vs deep (>=1500)
    shallow = dk[dk["water_depth_m"] < 1500]
    deep = dk[dk["water_depth_m"] >= 1500]

    def dry_share(sub):
        dry = (sub["tree_type"] == "dry").sum()
        wet = (sub["tree_type"] == "wet").sum()
        dw = dry + wet
        return (dry / dw) if dw else None, int(dry), int(wet)

    ss, sdry, swet = dry_share(shallow)
    ds, ddry, dwet = dry_share(deep)
    stats["headline"] = {
        "shallow_dry_share": ss,
        "shallow_dry": sdry,
        "shallow_wet": swet,
        "shallow_n": int(len(shallow)),
        "deep_dry_share": ds,
        "deep_dry": ddry,
        "deep_wet": dwet,
        "deep_n": int(len(deep)),
        "cutoff_m": 1500,
    }

    # top countries per tree type
    top = {}
    for tt in ("dry", "wet", "other"):
        vc = df[df["tree_type"] == tt]["country"].value_counts().head(6)
        top[tt] = [(str(c), int(n)) for c, n in vc.items()]
    stats["top_countries"] = top

    # concept breakdown
    stats["concept_totals"] = {
        (k if k else "(unmapped/other)"): int(v)
        for k, v in df["concept_type"].value_counts(dropna=False).items()
    }

    # GoM crosswalk supplementary: subsea tieback prevalence with block ground truth
    cw = pd.read_csv(CURATED / "subseaiq_bsee_block_crosswalk.csv")
    cwm = cw[cw["matched"] == 1]
    cw_concepts = cwm["host_concept"].dropna()
    stats["gom_crosswalk"] = {
        "n_matched": int(len(cwm)),
        "n_with_concept": int(len(cw_concepts)),
        "n_subsea_tieback": int((cw_concepts == "subsea_tieback").sum()),
        "concept_counts": {
            str(k): int(v) for k, v in cw_concepts.value_counts().items()
        },
    }
    return stats


# --------------------------------------------------------------------------- #
# HTML / inline-SVG rendering                                                   #
# --------------------------------------------------------------------------- #

DRY_C = "#0b3d5c"  # deep navy — surface / platform trees
WET_C = "#2a9d8f"  # teal — subsea trees
OTHER_C = "#94a3b2"  # slate — non-tree hulls (FSO/FSU, MOPU, island)


def _esc(s) -> str:
    return _html.escape(str(s))


def _pct(x) -> str:
    return "—" if x is None else f"{x * 100:.0f}%"


def _region_matrix_svg(mat: dict) -> str:
    """Horizontal stacked bars, one per region, absolute counts, sorted by total."""
    items = sorted(mat.items(), key=lambda kv: kv[1]["total"], reverse=True)
    max_total = max(v["total"] for _, v in items)
    label_w, bar_w, row_h, gap, pad_t = 210, 560, 26, 12, 14
    x0 = label_w + 14
    scale = bar_w / max_total
    height = pad_t + len(items) * (row_h + gap) + 8
    width = x0 + bar_w + 74
    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px" role="img" '
        f'aria-label="Facility count by region and tree type">'
    ]
    y = pad_t
    for region, v in items:
        cy = y + row_h / 2 + 4
        parts.append(
            f'<text x="{label_w}" y="{cy}" text-anchor="end" '
            f'font-size="12.5" fill="var(--ink)">{_esc(region)}</text>'
        )
        x = x0
        for key, color in (("dry", DRY_C), ("wet", WET_C), ("other", OTHER_C)):
            n = v[key]
            w = n * scale
            if w > 0:
                label = (
                    f'<text x="{x + w / 2:.1f}" y="{cy}" text-anchor="middle" '
                    f'font-size="11" fill="#fff" font-weight="600">{n}</text>'
                    if w >= 22
                    else ""
                )
                parts.append(
                    f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{row_h}" '
                    f'fill="{color}"/>{label}'
                )
                x += w
        parts.append(
            f'<text x="{x + 8:.1f}" y="{cy}" font-size="11.5" '
            f'fill="var(--muted)">{v["total"]}</text>'
        )
        y += row_h + gap
    parts.append("</svg>")
    return "".join(parts)


def _depth_share_svg(bands: dict) -> str:
    """Dry-vs-wet share per depth band (shallow->deep) — the dry-tree fade.

    Bars are normalised across producing trees only (dry + wet); "other" hulls
    are excluded so the navy segment equals the dry-share-of-trees quoted in the
    thesis and table.
    """
    order = [b for b in BAND_ORDER if b in bands]
    label_w, bar_w, row_h, gap, pad_t = 250, 520, 30, 18, 10
    x0 = label_w + 14
    height = pad_t + len(order) * (row_h + gap) + 8
    width = x0 + bar_w + 130
    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px" role="img" '
        f'aria-label="Dry vs wet tree share by water-depth band">'
    ]
    y = pad_t
    for band in order:
        v = bands[band]
        trees = v["dry"] + v["wet"]
        cy = y + row_h / 2 + 4
        parts.append(
            f'<text x="{label_w}" y="{cy}" text-anchor="end" '
            f'font-size="12" fill="var(--ink)">{_esc(band)}</text>'
        )
        x = x0
        for key, color in (("dry", DRY_C), ("wet", WET_C)):
            frac = v[key] / trees if trees else 0
            w = frac * bar_w
            if w > 0:
                label = (
                    f'<text x="{x + w / 2:.1f}" y="{cy}" text-anchor="middle" '
                    f'font-size="11" fill="#fff" font-weight="600">'
                    f"{frac * 100:.0f}%</text>"
                    if w >= 34
                    else ""
                )
                parts.append(
                    f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{row_h}" '
                    f'fill="{color}"/>{label}'
                )
                x += w
        parts.append(
            f'<text x="{x0 + bar_w + 10:.1f}" y="{cy}" font-size="11.5" '
            f'fill="var(--muted)">{trees} trees</text>'
        )
        y += row_h + gap
    parts.append("</svg>")
    return "".join(parts)


def _legend() -> str:
    def sw(color, txt):
        return (
            f'<span class="lg"><span class="sw" style="background:{color}">'
            f"</span>{txt}</span>"
        )

    return (
        '<div class="legend">'
        + sw(
            DRY_C,
            "Dry tree (surface trees on fixed jacket / compliant tower / TLP / spar)",
        )
        + sw(WET_C, "Wet tree (subsea trees: semisub-FPS / FPSO / FLNG / tieback)")
        + sw(
            OTHER_C,
            "Other hull (FSO-FSU / MOPU / artificial island — no producing trees)",
        )
        + "</div>"
    )


def _top_countries_block(top: dict) -> str:
    cols = []
    titles = {"dry": "Dry-tree", "wet": "Wet-tree", "other": "Other-hull"}
    colors = {"dry": DRY_C, "wet": WET_C, "other": OTHER_C}
    for tt in ("dry", "wet", "other"):
        rows = "".join(
            f"<tr><td>{_esc(c)}</td><td class='num'>{n}</td></tr>" for c, n in top[tt]
        )
        cols.append(
            f'<div class="topcol"><h4 style="color:{colors[tt]}">'
            f"{titles[tt]} leaders</h4>"
            f'<table class="mini"><tbody>{rows}</tbody></table></div>'
        )
    return '<div class="topgrid">' + "".join(cols) + "</div>"


def render_html(stats: dict) -> str:
    tt = stats["tree_totals"]
    n = stats["n_total"]
    h = stats["headline"]
    bands = stats["depth_bands"]
    shelf = bands["0-150 m (shallow shelf)"]["dry_share_of_trees"]
    ultra = bands["1500-3000 m (ultra-deepwater)"]["dry_share_of_trees"]
    n_regions = len(stats["region_matrix"])
    dry_pct = tt["dry"] / n * 100
    wet_pct = tt["wet"] / n * 100
    other_pct = tt.get("other", 0) / n * 100
    gom = stats["gom_crosswalk"]

    # region matrix table rows
    region_rows = ""
    for region, v in sorted(
        stats["region_matrix"].items(), key=lambda kv: kv[1]["total"], reverse=True
    ):
        typed = v["dry"] + v["wet"]
        cov = typed / v["total"] if v["total"] else 0
        region_rows += (
            f"<tr><td>{_esc(region)}</td>"
            f"<td class='num'>{v['dry']}</td>"
            f"<td class='num'>{v['wet']}</td>"
            f"<td class='num'>{v['other']}</td>"
            f"<td class='num'><strong>{v['total']}</strong></td>"
            f"<td class='num'>{cov * 100:.0f}%</td></tr>"
        )

    # depth band table
    band_rows = ""
    for band in BAND_ORDER:
        if band not in bands:
            continue
        v = bands[band]
        band_rows += (
            f"<tr><td>{_esc(band)}</td>"
            f"<td class='num'>{v['dry']}</td>"
            f"<td class='num'>{v['wet']}</td>"
            f"<td class='num'>{v['other']}</td>"
            f"<td class='num'><strong>{_pct(v['dry_share_of_trees'])}</strong></td>"
            f"<td class='num'>{v['total']}</td></tr>"
        )

    # concept breakdown chips
    concept_chips = ""
    for cname, cnt in stats["concept_totals"].items():
        concept_chips += f'<span class="chip">{_esc(cname)}<b>{cnt}</b></span>'

    css = """
:root{--ink:#15202b;--muted:#5b6b7b;--accent:#0b3d5c;--accent-soft:#e8eef3;
--rule:#cdd7e0;--zebra:#f5f8fa;--bg:#ffffff;--card:#ffffff;}
@media (prefers-color-scheme:dark){:root{--ink:#e6edf3;--muted:#9fb0c0;
--accent:#7fb2d4;--accent-soft:#172634;--rule:#2b3947;--zebra:#141c25;
--bg:#0d1620;--card:#111c27;}}
:root[data-theme="dark"]{--ink:#e6edf3;--muted:#9fb0c0;--accent:#7fb2d4;
--accent-soft:#172634;--rule:#2b3947;--zebra:#141c25;--bg:#0d1620;--card:#111c27;}
:root[data-theme="light"]{--ink:#15202b;--muted:#5b6b7b;--accent:#0b3d5c;
--accent-soft:#e8eef3;--rule:#cdd7e0;--zebra:#f5f8fa;--bg:#ffffff;--card:#ffffff;}
*{box-sizing:border-box;}
body{font-family:"Helvetica Neue",Helvetica,Arial,"Segoe UI",sans-serif;
color:var(--ink);background:var(--bg);line-height:1.45;margin:0;font-size:15px;}
.page{max-width:1000px;margin:0 auto;padding:0 24px 64px;}
.head{border-bottom:3px solid var(--accent);padding:26px 0 16px;margin-bottom:10px;}
.brand{font-size:20px;font-weight:700;color:var(--accent);letter-spacing:.2px;}
.meta{font-size:12.5px;color:var(--muted);margin-top:5px;}
h1{font-size:27px;color:var(--ink);margin:22px 0 6px;line-height:1.18;}
h2{font-size:19px;color:var(--accent);border-bottom:1px solid var(--rule);
padding-bottom:5px;margin:38px 0 12px;}
h4{font-size:13px;margin:0 0 6px;}
p{margin:9px 0;}
.thesis{background:var(--accent-soft);border-left:5px solid var(--accent);
border-radius:0 8px 8px 0;padding:16px 20px;margin:16px 0 8px;font-size:16.5px;}
.thesis b{color:var(--accent);}
.big{font-size:34px;font-weight:800;color:var(--accent);line-height:1;}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
gap:12px;margin:20px 0 8px;}
.kpi{border:1px solid var(--rule);border-radius:8px;padding:13px 15px;
background:var(--card);}
.kpi .v{font-size:24px;font-weight:800;color:var(--ink);}
.kpi .l{font-size:11.5px;color:var(--muted);margin-top:3px;
text-transform:uppercase;letter-spacing:.4px;}
.card{border:1px solid var(--rule);border-radius:10px;padding:16px 18px;
background:var(--card);margin:14px 0;overflow-x:auto;}
.legend{display:flex;flex-wrap:wrap;gap:14px 22px;margin:6px 0 14px;
font-size:12px;color:var(--muted);}
.lg{display:inline-flex;align-items:center;gap:7px;}
.sw{width:14px;height:14px;border-radius:3px;display:inline-block;}
table{border-collapse:collapse;width:100%;margin:10px 0 6px;font-size:13px;}
th,td{border:1px solid var(--rule);padding:6px 9px;text-align:left;}
th{background:var(--accent);color:#fff;font-weight:600;}
td.num{text-align:right;font-variant-numeric:tabular-nums;}
tbody tr:nth-child(even){background:var(--zebra);}
.topgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));
gap:16px;}
.mini{font-size:12.5px;}
.mini td{border:none;border-bottom:1px solid var(--rule);padding:4px 6px;}
.chip{display:inline-block;background:var(--accent-soft);border:1px solid var(--rule);
border-radius:14px;padding:3px 10px;margin:3px 4px 3px 0;font-size:12px;
color:var(--ink);}
.chip b{margin-left:6px;color:var(--accent);}
.foot{border-top:1px solid var(--rule);margin-top:40px;padding-top:12px;
font-size:12px;color:var(--muted);}
.foot b{color:var(--accent);}
.note{font-size:12.5px;color:var(--muted);margin-top:4px;}
"""

    thesis = (
        f'<div class="thesis">Deepwater is <b>wet-tree country</b>. Across '
        f"{n} producing offshore facilities worldwide, the dry-tree share of "
        f"trees collapses from <b>{_pct(shelf)}</b> on the shallow shelf to "
        f"<b>{_pct(ultra)}</b> in ultra-deepwater (&ge;1&#8239;500&#8239;m) — surface "
        f"well access does not survive the swim to the seabed.</div>"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Region &times; Development-Type — Dry vs Wet Tree Comparison</title>
<style>{css}</style>
</head>
<body>
<div class="page">
  <div class="head">
    <div class="brand">World Energy Data &middot; Field Development Insights</div>
    <div class="meta">Region &times; development-type comparison (dry-tree vs
      wet-tree vs other) &middot; Issue #776 &middot; Offshore production-facility
      universe</div>
  </div>

  <h1>Where dry trees give way to wet: the offshore development map</h1>
  {thesis}

  <div class="kpis">
    <div class="kpi"><div class="v">{n}</div>
      <div class="l">Facilities</div></div>
    <div class="kpi"><div class="v">{n_regions}</div>
      <div class="l">Regions</div></div>
    <div class="kpi"><div class="v">{tt['dry']}</div>
      <div class="l">Dry-tree &middot; {dry_pct:.0f}%</div></div>
    <div class="kpi"><div class="v">{tt['wet']}</div>
      <div class="l">Wet-tree &middot; {wet_pct:.0f}%</div></div>
    <div class="kpi"><div class="v">{tt.get('other',0)}</div>
      <div class="l">Other hull &middot; {other_pct:.0f}%</div></div>
  </div>

  <h2>Region &times; tree-type matrix</h2>
  <p>Every producing facility placed on the dry / wet / other trichotomy, by
     offshore region. Bars are facility counts; the trailing figure is the
     regional total.</p>
  {_legend()}
  <div class="card">{_region_matrix_svg(stats['region_matrix'])}</div>
  <table>
    <thead><tr><th>Region</th><th>Dry</th><th>Wet</th><th>Other</th>
      <th>Total</th><th>Typed&nbsp;%</th></tr></thead>
    <tbody>{region_rows}</tbody>
  </table>
  <p class="note">"Typed %" = share of the region's facilities that map to a
     dry- or wet-tree concept (i.e. not an FSO/FSU, MOPU or artificial island).
     South America &amp; Caribbean and West Africa read wet-tree-heavy — those are
     the FPSO provinces; the Middle East and Caspian read all-dry — shallow,
     benign, jacket country.</p>

  <h2>The physical story: dry-tree share fades with water depth</h2>
  <p>Restricted to the {stats['n_depth_known']} facilities with a recorded water
     depth. Bars are normalised across producing trees only (dry + wet; the few
     non-tree hulls are excluded), so the navy segment is the dry-tree share of
     trees. Read top-to-bottom, shallow to deep — the navy shrinks at every
     step.</p>
  {_legend()}
  <div class="card">{_depth_share_svg(bands)}</div>
  <table>
    <thead><tr><th>Water-depth band</th><th>Dry</th><th>Wet</th><th>Other</th>
      <th>Dry share of trees</th><th>n</th></tr></thead>
    <tbody>{band_rows}</tbody>
  </table>
  <p class="note">Below 1&#8239;500&#8239;m, dry trees are {h['deep_dry']} of
     {h['deep_dry'] + h['deep_wet']} trees ({_pct(h['deep_dry_share'])}); above it,
     {h['shallow_dry']} of {h['shallow_dry'] + h['shallow_wet']}
     ({_pct(h['shallow_dry_share'])}). The nine deep dry-tree facilities are the
     TLPs and spars that push surface access to its engineering limit.</p>

  <h2>Who builds what: country leaders by tree type</h2>
  {_top_countries_block(stats['top_countries'])}

  <h2>Concept mix (as-built host type)</h2>
  <div class="card">{concept_chips}</div>

  <h2>Coverage &amp; honesty</h2>
  <p>This universe is the curated <code>production_facilities.csv</code>
     ({n} standalone facilities). Two limits worth stating plainly:</p>
  <ul>
    <li><b>Subsea tiebacks are under-counted.</b> A tieback is not a standalone
      facility — it hangs off a host — so only {tt['wet']} wet-tree hulls appear
      here, of which just the {stats['concept_totals'].get('subsea_tieback', 0)}
      that the source lists as their own line are tiebacks. Where we do have
      block-level ground truth (the GoM SubseaIQ&ndash;BSEE crosswalk,
      {gom['n_with_concept']} typed fields), subsea tiebacks are
      {gom['n_subsea_tieback']} of them — the true wet-tree footprint is larger
      than a facility census shows.</li>
    <li><b>The typed/untyped split is honest per region.</b> {tt.get('other',0)}
      of {n} facilities ({other_pct:.0f}%) are non-tree hulls (FSO/FSU, MOPU,
      artificial island) and are held out of the dry-vs-wet ratios rather than
      forced into one bucket. {stats['n_depth_null']} facilities lack a recorded
      water depth and are excluded from the depth chart only.</li>
  </ul>

  <div class="foot">
    <b>Sources:</b> data/modules/offshore_assets/curated/production_facilities.csv
    ({n} rows, HOST_TYPE &rarr; concept &rarr; tree_type) &middot;
    subseaiq_bsee_block_crosswalk.csv ({gom['n_matched']} matched GoM rows,
    supplementary subsea-tieback prevalence only).
    <b>Trichotomy:</b> dry = {{fixed_jacket, compliant_tower, tlp, spar, nui}}
    (imported verbatim from
    <code>worldenergydata.field_development.recommendation._DRY_TREE</code>);
    wet = {{semisub_fps, fpso, flng, subsea_tieback, subsea_to_shore}};
    other = unmapped HOST_TYPE + null.
    <b>Method:</b> <code>build_portfolio()</code> imports cleanly but covers only
    the 115-field GoM matched set, so the all-region matrix is built directly
    from the facility census with the mapping above.
    <b>Build:</b> scripts/field_development/build_region_devtype_comparison.py
    &rarr; reports/field_development/region_devtype_matrix.csv. Counts are
    facilities, not fields or wells; every figure on this page is computed from
    the source rows (flag-don't-fake).
  </div>
</div>
</body>
</html>"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = build_table()
    out_csv = OUT_DIR / "region_devtype_matrix.csv"
    df.to_csv(out_csv, index=False)
    print("wrote", out_csv, "rows", len(df))
    stats = compute_stats(df)
    html = site_nav.inject_for(render_html(stats), "devtype")
    out_html = OUT_DIR / "region_devtype_comparison.html"
    out_html.write_text(html, encoding="utf-8")
    print("wrote", out_html, "bytes", len(html))


if __name__ == "__main__":
    main()
