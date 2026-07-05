# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Build a static GitHub Pages site from worldenergydata's deterministic outputs.

Practices borrowed (and adapted to a *static* site) from public upstream-data
copilots: deterministic core, no API key, public-data provenance, explicit
data-limit disclosure, and a feedback call-to-action.

The engineering numbers are computed elsewhere by unit-tested domain code and
frozen into `reports/`. This script is a pure presentation layer: it reads those
frozen artifacts and renders them to HTML. It performs NO calculation, so it can
never alter a sanctioned number. Run:

    uv run scripts/build_pages.py        # or: python scripts/build_pages.py

Output lands in `public/`, which the Pages workflow publishes verbatim.

Per-domain build isolation (P2, issue #528)
-------------------------------------------
Rendering is organised as a registry of per-domain builders (``DOMAINS``) plus
a small set of shared assets (CSS + viz HTML) and an always-regenerated landing
``index.html``. This lets CI rebuild only the domain(s) whose ``reports/<domain>/``
content changed, instead of re-rendering the whole site on every push:

    python scripts/build_pages.py                       # full build (all domains)
    python scripts/build_pages.py --domains lower_tertiary
    python scripts/build_pages.py --clean               # wipe public/ then full build

HONEST CONSTRAINT — GitHub Pages publishes exactly ONE artifact for the whole
site (``actions/deploy-pages`` replaces the entire published tree from a single
``upload-pages-artifact`` tarball). There is NO native per-domain *publish*: you
cannot deploy a partial artifact without clobbering the rest of the site.
Therefore P2 is per-domain *build* isolation (skip re-rendering untouched
domains) merged into ONE published tree, NOT separate per-domain Pages sites.
CI achieves the "merge" by restoring the previously-published ``public/`` from
the Actions cache, overwriting only the touched domain's files, and re-uploading
the full merged tree. A change to shared chrome (this script, the CSS, the page
template, or ``site_assets/``) affects every page and so forces a ``--clean``
full rebuild.

With no arguments the output is byte-for-byte identical to the pre-P2 monolithic
build — the refactor is presentation-preserving.
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
# Frozen, committed artifacts that the published site needs but that live under a
# gitignored scratch dir (reports/bsee/). Copied here so CI can publish them.
SITE_ASSETS = ROOT / "site_assets"
PUBLIC = ROOT / "public"
ASSETS = PUBLIC / "assets"

REPO = "vamseeachanta/worldenergydata"
ISSUES_URL = f"https://github.com/{REPO}/issues/new"
SOURCE_NOTE = (
    "Public BSEE OGOR-A production data and BSEE Well Activity Reports "
    "(US Gulf of Mexico / Gulf of America)."
)

# ---------------------------------------------------------------------------
# Minimal, dependency-free Markdown -> HTML for the exact constructs these
# reports use: ATX headings, GFM tables, blockquotes, fenced code, hr, bold,
# italics, inline code, links. Raw HTML entities/<br> pass through untouched.
# ---------------------------------------------------------------------------

_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC = re.compile(r"(?<![A-Za-z0-9_])_([^_]+)_(?![A-Za-z0-9_])")
_CODE = re.compile(r"`([^`]+)`")


def _inline(text: str) -> str:
    """Apply inline formatting. Text may already contain intentional raw HTML
    (e.g. &middot;, <br>), so we do NOT escape the whole string — only the
    contents of inline code spans, which should be literal."""
    text = _CODE.sub(lambda m: f"<code>{html.escape(m.group(1))}</code>", text)
    text = _BOLD.sub(r"<strong>\1</strong>", text)
    text = _ITALIC.sub(r"<em>\1</em>", text)
    text = _LINK.sub(r'<a href="\2">\1</a>', text)
    return text


def _table(rows: list[str]) -> str:
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    header, _align, *body = cells
    out = ["<div class='table-wrap'><table>", "<thead><tr>"]
    out += [f"<th>{_inline(c)}</th>" for c in header]
    out += ["</tr></thead>", "<tbody>"]
    for row in body:
        out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in row) + "</tr>")
    out += ["</tbody></table></div>"]
    return "\n".join(out)


def md_to_html(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i, n = 0, len(lines)
    para: list[str] = []

    def flush_para():
        if para:
            out.append(f"<p>{_inline(' '.join(para))}</p>")
            para.clear()

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # fenced code
        if stripped.startswith("```"):
            flush_para()
            i += 1
            code: list[str] = []
            while i < n and not lines[i].strip().startswith("```"):
                code.append(html.escape(lines[i]))
                i += 1
            i += 1
            out.append("<pre class='ascii'>" + "\n".join(code) + "</pre>")
            continue

        # table block (current line and next are pipe rows, next is a separator)
        if (
            stripped.startswith("|")
            and i + 1 < n
            and re.match(r"^\s*\|[\s:\-|]+\|\s*$", lines[i + 1])
        ):
            flush_para()
            block = [lines[i], lines[i + 1]]
            i += 2
            while i < n and lines[i].strip().startswith("|"):
                block.append(lines[i])
                i += 1
            out.append(_table(block))
            continue

        # headings
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_para()
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            i += 1
            continue

        # horizontal rule
        if stripped in ("---", "***", "___"):
            flush_para()
            out.append("<hr>")
            i += 1
            continue

        # blockquote (possibly multi-line)
        if stripped.startswith(">"):
            flush_para()
            quote: list[str] = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            out.append(f"<blockquote>{_inline(' '.join(quote))}</blockquote>")
            continue

        # unordered list block
        if re.match(r"^[-*]\s+", stripped):
            flush_para()
            items: list[str] = []
            while i < n and re.match(r"^[-*]\s+", lines[i].strip()):
                items.append(re.sub(r"^[-*]\s+", "", lines[i].strip()))
                i += 1
            out.append(
                "<ul>" + "".join(f"<li>{_inline(it)}</li>" for it in items) + "</ul>"
            )
            continue

        # blank line ends a paragraph
        if not stripped:
            flush_para()
            i += 1
            continue

        para.append(stripped)
        i += 1

    flush_para()
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Page template — the "good-practice" chrome wraps every page.
# ---------------------------------------------------------------------------


def page(
    title: str, subtitle: str, body: str, *, provenance: str, data_limits: str
) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} &middot; worldenergydata</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="site">
  <a class="home" href="index.html">&larr; worldenergydata &middot; open data outputs</a>
  <div class="badges">
    <span class="badge ok" title="Every number is precomputed by unit-tested domain code and frozen into the report this page renders.">Deterministic core</span>
    <span class="badge ok" title="Fully static. No server, no login, no API key.">No API key</span>
    <span class="badge" title="{html.escape(SOURCE_NOTE)}">Public BSEE data</span>
  </div>
</header>
<main>
  <h1 class="page-title">{html.escape(title)}</h1>
  <p class="subtitle">{subtitle}</p>
  <p class="provenance"><strong>Provenance.</strong> {provenance}</p>
  <details class="limits" open>
    <summary>Data limits &amp; honest caveats</summary>
    <p>{data_limits}</p>
  </details>
  <section class="content">
  {body}
  </section>
</main>
<footer class="site">
  <p>{html.escape(SOURCE_NOTE)}</p>
  <p>This page is a presentation layer over frozen, unit-tested outputs &mdash; it performs no calculation and cannot alter a sanctioned number.</p>
  <p><a href="{ISSUES_URL}">Found an error or want a missing view? Open an issue.</a> &middot; <a href="https://github.com/{REPO}">Source on GitHub</a></p>
</footer>
</body>
</html>
"""


STYLE = """:root{--fg:#1a2230;--muted:#5b6675;--bg:#f7f8fa;--card:#fff;--line:#e2e6ec;--accent:#0a5;--blue:#1763c7}
*{box-sizing:border-box}
body{margin:0;font:16px/1.6 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--fg);background:var(--bg)}
header.site,footer.site{padding:14px 22px;background:var(--card);border-bottom:1px solid var(--line)}
footer.site{border-top:1px solid var(--line);border-bottom:0;color:var(--muted);font-size:14px;margin-top:48px}
header.site{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between}
.home{color:var(--blue);text-decoration:none;font-weight:600}
.badges{display:flex;gap:8px;flex-wrap:wrap}
.badge{font-size:12px;font-weight:600;padding:3px 10px;border-radius:999px;background:#eef1f5;color:var(--muted);border:1px solid var(--line);cursor:help}
.badge.ok{background:#e7f7ef;color:#0a6b46;border-color:#bce8d3}
main{max-width:960px;margin:0 auto;padding:28px 22px}
.page-title{font-size:30px;margin:.2em 0 .1em}
.subtitle{color:var(--muted);margin:.2em 0 1.2em;font-size:17px}
.provenance{background:#eef4fc;border-left:4px solid var(--blue);padding:10px 14px;border-radius:0 6px 6px 0;font-size:14px}
.limits{background:#fff8ec;border:1px solid #f1ddb3;border-radius:8px;padding:10px 14px;margin:14px 0 24px;font-size:14px}
.limits summary{cursor:pointer;font-weight:600;color:#8a5a00}
.content h2{margin-top:1.6em;border-bottom:1px solid var(--line);padding-bottom:.2em}
.content h3{margin-top:1.4em}
blockquote{margin:1em 0;padding:.6em 1em;background:#f0f3f7;border-left:4px solid var(--muted);border-radius:0 6px 6px 0;color:#374050}
.table-wrap{overflow-x:auto;margin:1em 0}
table{border-collapse:collapse;width:100%;font-size:14px;background:var(--card)}
th,td{border:1px solid var(--line);padding:6px 10px;text-align:left}
th{background:#f0f3f7;font-weight:600}
td:not(:first-child){font-variant-numeric:tabular-nums}
pre.ascii{background:#0f1722;color:#cfe3ff;padding:14px;border-radius:8px;overflow-x:auto;font-size:13px;line-height:1.35}
code{background:#eef1f5;padding:1px 5px;border-radius:4px;font-size:.92em}
a{color:var(--blue)}
hr{border:0;border-top:1px solid var(--line);margin:1.6em 0}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px;margin:24px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;text-decoration:none;color:inherit;transition:.15s;display:block}
.card:hover{border-color:var(--blue);box-shadow:0 4px 16px rgba(23,99,199,.1);transform:translateY(-2px)}
.card h3{margin:.1em 0 .4em;color:var(--blue)}
.card p{color:var(--muted);font-size:14px;margin:0}
.viz-frame{width:100%;height:640px;border:1px solid var(--line);border-radius:10px;margin:1em 0;background:var(--card)}
.viz-links{font-size:14px;margin:.4em 0 1.4em}
"""


# ---------------------------------------------------------------------------
# Shared assets — written on every build regardless of which domains are
# selected, because they are the chrome every domain page links to.
# ---------------------------------------------------------------------------


def build_shared_assets() -> dict[str, bool]:
    """Write the stylesheet and copy the shared viz assets. Returns the set of
    viz assets that are available (used by domain builders that embed them)."""
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "style.css").write_text(STYLE, encoding="utf-8")

    # --- copy the self-contained viz HTML as assets ---
    # Prefer the committed site_assets/ copy (what CI publishes); fall back to the
    # gitignored reports/bsee/ scratch output for local-only rebuilds.
    viz_names = ["julia_well_path_plotly.html", "julia_well_path_threejs.html"]
    available_viz: dict[str, bool] = {}
    for name in viz_names:
        for src in (SITE_ASSETS / name, REPORTS / "bsee" / name):
            if src.exists():
                shutil.copy2(src, ASSETS / name)
                available_viz[name] = True
                break
    return available_viz


# ---------------------------------------------------------------------------
# Per-domain builders. Each one writes ONLY its own output files into public/
# and returns whatever the landing-page builder needs from it. A domain builder
# never wipes public/, so it composes cleanly over a cache-restored tree.
# ---------------------------------------------------------------------------


def build_lower_tertiary(available_viz: dict[str, bool]) -> list[tuple]:
    """Render the Lower-Tertiary surface: per-field economics, benchmark,
    portfolio summary, and the Julia 3D well-path page. Returns the list of
    ``(slug, display, filename, npv_str, npv_value)`` tuples the landing page
    uses to build its economics table."""
    # --- Field life-cycle "page 1" gallery (stage-gate posters) ---
    # Self-contained HTML built by scripts/lower_tertiary/build_lifecycle_posters.py.
    # Publish the 10 per-field posters + the gallery index (skip the template + _facts.json).
    lifecycle_src = REPORTS / "lower_tertiary" / "lifecycle"
    if (lifecycle_src / "index.html").exists():
        lifecycle_dst = PUBLIC / "lifecycle"
        lifecycle_dst.mkdir(parents=True, exist_ok=True)
        for html in sorted(lifecycle_src.glob("*_lifecycle.html")):
            shutil.copy2(html, lifecycle_dst / html.name)
        shutil.copy2(lifecycle_src / "index.html", lifecycle_dst / "index.html")
        # Per-well granular timelines (the fractal well-level deep-dive) nest under wells/.
        wells_src = lifecycle_src / "wells"
        if (wells_src / "index.html").exists():
            wells_dst = lifecycle_dst / "wells"
            wells_dst.mkdir(parents=True, exist_ok=True)
            for html in sorted(wells_src.glob("*_well.html")):
                shutil.copy2(html, wells_dst / html.name)
            shutil.copy2(wells_src / "index.html", wells_dst / "index.html")
        # Per-field asset drill-downs (field → facility → asset → component → engineering).
        assets_src = lifecycle_src / "assets"
        if assets_src.exists():
            assets_dst = lifecycle_dst / "assets"
            assets_dst.mkdir(parents=True, exist_ok=True)
            for html in sorted(assets_src.glob("*_assets.html")):
                shutil.copy2(html, assets_dst / html.name)

    # --- Drilling learning-curve front door (issue #775) ---
    # Self-contained HTML (inline CSS + inline-SVG charts) built by
    # scripts/lower_tertiary/build_drilling_insights.py; copied verbatim so its
    # thesis page is reachable at /drilling-insights.html.
    drill_src = REPORTS / "lower_tertiary" / "drilling_insights.html"
    if drill_src.exists():
        shutil.copyfile(drill_src, PUBLIC / "drilling-insights.html")

    # --- Economics pages (sanctioned V30), one per Lower-Tertiary field ---
    field_names = {
        "anchor": "Anchor",
        "big_foot": "Big Foot",
        "cascade_chinook": "Cascade&ndash;Chinook",
        "jack_st_malo": "Jack / St. Malo",
        "julia": "Julia",
        "shenandoah": "Shenandoah",
        "stones": "Stones",
    }
    npv_re = re.compile(r"Terminal cumulative NPV = \*\*([^*]+)\*\*")
    fields = []  # (slug, display, page_filename, npv_str, npv_value)
    for md in sorted((REPORTS / "lower_tertiary").glob("field_economics_*_v30.md")):
        slug = md.name[len("field_economics_") : -len("_v30.md")]
        display = field_names.get(slug, slug.replace("_", " ").title())
        text = md.read_text(encoding="utf-8")
        m = npv_re.search(text)
        npv_str = m.group(1).strip() if m else "&mdash;"
        try:
            npv_val = float(
                npv_str.replace("$", "").replace(",", "").replace("M", "").strip()
            )
        except ValueError:
            npv_val = 0.0
        fname = f"economics-{slug}.html"
        (PUBLIC / fname).write_text(
            page(
                f"{display} Field Economics",
                "Per-well and field-level NPV from the sanctioned V30 financial model.",
                md_to_html(text),
                provenance=(
                    "Computed by the V30 cashflow model "
                    "(<code>build_field_npv_timeline</code>), which reuses the same "
                    "monthly cashflow and trimmed-discount formula as "
                    "<code>reproduce_v30_financials</code>. Terminal NPV reconciles to "
                    "the sanctioned V30 baseline."
                ),
                data_limits=(
                    "The NPV shown is the <strong>sanctioned V30 model truth, presented "
                    "as-is</strong> &mdash; not reframed as value-positive. Every Lower-"
                    "Tertiary field here is NPV-negative at a 10% discount rate life-to-date. "
                    "Operation markers (drilling/completion dates) are annotations only and "
                    "do not feed the cashflow model."
                ),
            ),
            encoding="utf-8",
        )
        fields.append((slug, display, fname, npv_str, npv_val))

    # --- Benchmark page ---
    bench_md = (
        REPORTS / "lower_tertiary" / "lt_well_benchmark_lower_tertiary_2010_latest.md"
    )
    if bench_md.exists():
        (PUBLIC / "benchmark.html").write_text(
            page(
                "Lower Tertiary Well Benchmarking",
                "Cross-field well performance benchmarking (2010&ndash;latest).",
                md_to_html(bench_md.read_text(encoding="utf-8")),
                provenance=(
                    "Derived deterministically from BSEE OGOR-A production across the "
                    "Lower-Tertiary fields; same frozen data window as the V30 economics."
                ),
                data_limits=(
                    "Benchmarks reflect only wells with reported OGOR-A production; wells "
                    "absent from the structured data are excluded rather than estimated."
                ),
            ),
            encoding="utf-8",
        )

    # --- Portfolio summary page ---
    summ_md = REPORTS / "lower_tertiary_field_summary.md"
    if summ_md.exists():
        (PUBLIC / "portfolio.html").write_text(
            page(
                "Lower Tertiary Portfolio Summary",
                "Field-by-field roll-up of the Lower-Tertiary play.",
                md_to_html(summ_md.read_text(encoding="utf-8")),
                provenance="Aggregated from the per-field sanctioned V30 economics reports.",
                data_limits=(
                    "Roll-up inherits each field's data limits; see the individual field "
                    "pages for per-field caveats."
                ),
            ),
            encoding="utf-8",
        )

    # --- Well-path page ---
    if available_viz:
        links = []
        if "julia_well_path_plotly.html" in available_viz:
            links.append(
                '<a href="assets/julia_well_path_plotly.html">Open Plotly version &rarr;</a>'
            )
        if "julia_well_path_threejs.html" in available_viz:
            links.append(
                '<a href="assets/julia_well_path_threejs.html">Open Three.js version &rarr;</a>'
            )
        primary = (
            "julia_well_path_plotly.html"
            if "julia_well_path_plotly.html" in available_viz
            else next(iter(available_viz))
        )
        wp_body = (
            f'<iframe class="viz-frame" src="assets/{primary}" title="Julia well paths"></iframe>'
            f'<p class="viz-links">{" &middot; ".join(links)}</p>'
            "<p>3D directional surveys for the Julia (G20351) development wells, rendered "
            "from a frozen JSON contract by two independent renderers (Plotly &amp; Three.js).</p>"
        )
        (PUBLIC / "well-path.html").write_text(
            page(
                "Julia Well Paths (3D)",
                "Directional survey geometry for the Julia subsea development.",
                wp_body,
                provenance=(
                    "Geometry derived deterministically from BSEE directional-survey "
                    "records via <code>prepare_well_paths</code>; both renderers consume "
                    "one shared frozen JSON contract."
                ),
                data_limits=(
                    "Coordinate axis convention: <code>x_coor</code> is NORTHING, not "
                    "easting. Surveys cover Julia development wells (lease G20351); "
                    "wells without survey records are omitted rather than interpolated."
                ),
            ),
            encoding="utf-8",
        )

    return fields


def build_field_development(available_viz: dict[str, bool]) -> list[tuple]:
    """Publish the field-development playbook surface.

    These artifacts are already **self-contained** HTML (inline SVG schematics,
    CSS and JS — no external assets), so the playbook is published as-is: the
    single-page surfaces are copied flat and the multi-page report sets (a landing
    index plus one page per field) are copied as whole trees so their internal
    links keep working. Returns ``[]`` — the landing index keys off what exists in
    ``public/`` (see :func:`build_index`)."""
    src = REPORTS / "field_development"
    dst = PUBLIC / "field-development"
    dst.mkdir(parents=True, exist_ok=True)

    # Single self-contained pages.
    for rel, out in (
        ("showcase/index.html", "showcase.html"),
        ("interactive/playbook.html", "playbook.html"),
    ):
        if (src / rel).exists():
            shutil.copyfile(src / rel, dst / out)

    # Cross-cutting comparison front doors (issues #776, #779). These are
    # self-contained thesis pages (inline CSS + inline-SVG). They are published
    # flat at the site root (not under /field-development/) so they read as
    # orthogonal, whole-atlas comparisons rather than one field's page.
    for rel, out in (
        ("region_devtype_comparison.html", "region-devtype-comparison.html"),
        ("all_regions_atlas.html", "all-regions-atlas.html"),
    ):
        if (src / rel).exists():
            shutil.copyfile(src / rel, PUBLIC / out)

    # Multi-page report sets (index + per-field pages) — copy the whole tree so
    # the relative links between the index and its field pages survive.
    for sub, out in (("portfolio", "portfolio"), ("bsee_matched", "bsee-matched")):
        if (src / sub).exists():
            shutil.copytree(
                src / sub,
                dst / out,
                ignore=shutil.ignore_patterns("*.json"),
                dirs_exist_ok=True,
            )
    return []


def build_capabilities(available_viz: dict[str, bool]) -> list[tuple]:
    """Publish the self-contained capabilities overview at ``/capabilities/``.

    The page is a hand-authored, fully self-contained HTML file (inline CSS, no
    external assets) that summarises what the repo can do and links the live
    dashboards. Like the field-development surfaces it is copied verbatim &mdash; no
    template wrapping &mdash; so its internal ``../`` links to the sibling dashboards
    resolve against the site root. Returns ``[]``; the landing index keys off the
    file existing in ``public/`` (see :func:`build_index`)."""
    src = REPORTS / "capabilities" / "index.html"
    if not src.exists():
        return []
    dst = PUBLIC / "capabilities"
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst / "index.html")
    # Life-cycle Insights HUB (self-contained, hand-authored). Copied verbatim so
    # its sibling link (index.html) and its ../ links to the published front
    # doors resolve under /capabilities/.
    insights = REPORTS / "capabilities" / "insights.html"
    if insights.exists():
        shutil.copyfile(insights, dst / "insights.html")
    # Publish the intervention-serviceability brief (lives under docs/) so the
    # Insights hub's Workover front-door link resolves in the published tree at
    # /intervention-db/intervention-stats-brief.html. Self-contained (inline
    # CSS + inline-SVG), copied verbatim.
    brief = ROOT / "docs" / "intervention-db" / "intervention-stats-brief.html"
    if brief.exists():
        brief_dst = PUBLIC / "intervention-db"
        brief_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(brief, brief_dst / "intervention-stats-brief.html")
    # Per-capability client one-pager PDFs and self-contained workflow-API
    # artifacts, generated by scripts/capabilities/build_onepagers.py and
    # committed as frozen artifacts; copied verbatim so the page's pdf/ and api/
    # links resolve under /capabilities/.
    for sub in ("pdf", "api"):
        srcdir = REPORTS / "capabilities" / sub
        if srcdir.exists():
            shutil.copytree(srcdir, dst / sub, dirs_exist_ok=True)
    return []


def build_completion(available_viz: dict[str, bool]) -> list[tuple]:
    """Publish the well drilling-&-completion-days report at ``/completion/``.

    The page is a self-contained HTML artifact (inline CSS, no external assets)
    generated by ``scripts/completion/build_completion_report.py`` from a frozen
    BSEE WAR-derived reference workbook; here it is copied verbatim so its ``../``
    link back to the capabilities page resolves against the site root. Returns
    ``[]`` &mdash; the landing index keys off what exists in ``public/``."""
    src = REPORTS / "completion" / "index.html"
    if not src.exists():
        return []
    dst = PUBLIC / "completion"
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst / "index.html")
    return []


def build_marine_safety(available_viz: dict[str, bool]) -> list[tuple]:
    """Publish the marine-safety analytics surface.

    These artifacts are already **self-contained** HTML (inline CSS/JS, Plotly
    from CDN). The ``marine_safety/`` set is a small report tree whose pages link
    to one another with relative hrefs (the executive summary links the fatality,
    foundering and hatch analyses), so the whole tree is copied to preserve those
    links. The IMO GISIS executive report is a single top-level file copied flat.
    Only real-data reports are published; the synthetic ``*_demo`` page is not.
    Returns ``[]`` &mdash; the landing index keys off what exists in ``public/``."""
    src = REPORTS / "marine_safety"
    if src.exists():
        dst = PUBLIC / "marine_safety"
        dst.mkdir(parents=True, exist_ok=True)
        for f in src.glob("*.html"):
            shutil.copyfile(f, dst / f.name)
    imo = REPORTS / "IMO_GISIS_Executive_Report.html"
    if imo.exists():
        shutil.copyfile(imo, PUBLIC / imo.name)
    return []


def build_hse(available_viz: dict[str, bool]) -> list[tuple]:
    """Publish the HSE surface: self-contained offshore-incident report cards
    (e.g. the mooring-fatigue grounded card). Only ``*.html`` is published; the
    Markdown/JSON working notes under ``reports/hse/`` stay out of the site.
    Returns ``[]`` &mdash; the landing index keys off what exists in ``public/``."""
    src = REPORTS / "hse"
    if not src.exists():
        return []
    dst = PUBLIC / "hse"
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.glob("*.html"):
        shutil.copyfile(f, dst / f.name)
    return []


def build_field_atlas(available_viz: dict[str, bool]) -> list[tuple]:
    """Publish the field-atlas browse page (Country→Domain→Region→Play→Field).

    Self-contained HTML built by ``scripts/field_atlas/build_field_atlas.py`` from
    ``reports/field-atlas/_roster.json`` (120 concept-matched GoM fields, tiered).
    Returns ``[]`` — the landing index keys off what exists in ``public/``."""
    src = REPORTS / "field-atlas" / "index.html"
    if not src.exists():
        return []
    dst = PUBLIC / "field-atlas"
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst / "index.html")
    return []


def build_decommissioning(available_viz: dict[str, bool]) -> list[tuple]:
    """Publish the decommissioning surface: the GoM P&A liability-wave front door
    (issue #777). The page is a self-contained HTML artifact (inline CSS +
    inline-SVG charts) built by ``scripts/decommissioning/build_pa_liability_wave.py``
    from the frozen BSEE well inventory; copied verbatim into
    ``public/decommissioning/pa-liability-wave.html``. Returns ``[]`` &mdash; the
    landing index keys off what exists in ``public/``."""
    dst = PUBLIC / "decommissioning"
    pages = {
        "pa_liability_wave.html": "pa-liability-wave.html",
        "regional_liability.html": "regional-liability.html",
    }
    made = False
    for src_name, dst_name in pages.items():
        src = REPORTS / "decommissioning" / src_name
        if not src.exists():
            continue
        if not made:
            dst.mkdir(parents=True, exist_ok=True)
            made = True
        shutil.copyfile(src, dst / dst_name)
    return []


def build_field_benchmark(available_viz: dict[str, bool]) -> list[tuple]:
    """Publish the cross-country field-development benchmark at ``/field_benchmark/``.

    The page is a self-contained HTML artifact (inline CSS, no external assets)
    generated by
    ``worldenergydata.production.unified.benchmark_report.generate_report`` from
    the unified production adapters. Every row is provenance-badged (real vs
    illustrative-seed), so no synthetic row is ever presented as real. The whole
    ``reports/field_benchmark/`` dir is copied verbatim (the ``_facts.json`` is
    the structured evidence behind the table). Returns ``[]`` &mdash; the landing
    index keys off what exists in ``public/``."""
    src = REPORTS / "field_benchmark" / "index.html"
    if not src.exists():
        return []
    dst = PUBLIC / "field_benchmark"
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst / "index.html")
    facts = REPORTS / "field_benchmark" / "_facts.json"
    if facts.exists():
        shutil.copyfile(facts, dst / "_facts.json")
    return []


# Registry of per-domain builders. Add new domains here (key == reports/<domain>/
# subdir name) as their surfaces come online. ``build(domains=...)`` iterates this.
DOMAINS = {
    "lower_tertiary": build_lower_tertiary,
    "field_development": build_field_development,
    "completion": build_completion,
    "marine_safety": build_marine_safety,
    "hse": build_hse,
    "decommissioning": build_decommissioning,
    "capabilities": build_capabilities,
    "field-atlas": build_field_atlas,
    "field_benchmark": build_field_benchmark,
}


# ---------------------------------------------------------------------------
# Landing page — ALWAYS regenerated. It indexes whatever exists in public/ (so a
# partial build still produces a correct landing page over the restored tree)
# and derives the economics table straight from the source reports so it stays
# correct even when the lower_tertiary domain was not part of this build.
# ---------------------------------------------------------------------------


def _lower_tertiary_fields() -> list[tuple]:
    """Parse per-field NPV out of the source reports — independent of whether the
    lower_tertiary domain pages were (re)built this run. Mirrors the parse in
    build_lower_tertiary so the landing economics table is always accurate."""
    field_names = {
        "anchor": "Anchor",
        "big_foot": "Big Foot",
        "cascade_chinook": "Cascade&ndash;Chinook",
        "jack_st_malo": "Jack / St. Malo",
        "julia": "Julia",
        "shenandoah": "Shenandoah",
        "stones": "Stones",
    }
    npv_re = re.compile(r"Terminal cumulative NPV = \*\*([^*]+)\*\*")
    fields = []
    for md in sorted((REPORTS / "lower_tertiary").glob("field_economics_*_v30.md")):
        slug = md.name[len("field_economics_") : -len("_v30.md")]
        display = field_names.get(slug, slug.replace("_", " ").title())
        text = md.read_text(encoding="utf-8")
        m = npv_re.search(text)
        npv_str = m.group(1).strip() if m else "&mdash;"
        try:
            npv_val = float(
                npv_str.replace("$", "").replace(",", "").replace("M", "").strip()
            )
        except ValueError:
            npv_val = 0.0
        fields.append((slug, display, f"economics-{slug}.html", npv_str, npv_val))
    return fields


def _field_development_section() -> str:
    """Prominent landing section for the field-development playbook (cards link the
    self-contained surfaces published by :func:`build_field_development`)."""
    fd = PUBLIC / "field-development"
    cards = []
    if (fd / "showcase.html").exists():
        cards.append(
            '<a class="card" href="field-development/showcase.html">'
            "<h3>Capability Showcase &rarr;</h3><p>What the playbook produces "
            "end-to-end, with generated subsea schematics for real fields across "
            "every major offshore region.</p></a>"
        )
    if (fd / "playbook.html").exists():
        cards.append(
            '<a class="card" href="field-development/playbook.html">'
            "<h3>Interactive Playbook &rarr;</h3><p>Move the sliders (water depth, "
            "reserves, tieback distance) and watch the recommended development "
            "concept and its schematic update live.</p></a>"
        )
    if (fd / "portfolio" / "index.html").exists():
        cards.append(
            '<a class="card" href="field-development/portfolio/index.html">'
            "<h3>Deepwater Portfolio &rarr;</h3><p>Full field-development plans for "
            "a 10-field deepwater Gulf of Mexico portfolio.</p></a>"
        )
    if (fd / "bsee-matched" / "index.html").exists():
        cards.append(
            '<a class="card" href="field-development/bsee-matched/index.html">'
            "<h3>BSEE-Matched Fields &rarr;</h3><p>Recommended vs as-built concept, "
            "with schematics, across 115 BSEE-cross-referenced Gulf of Mexico "
            "fields.</p></a>"
        )
    if not cards:
        return ""
    return (
        "<h2>Offshore Field-Development Playbook</h2>"
        "<p>From a field's parameters to a ranked development concept, a to-scale "
        "subsea schematic, indicative economics, flow-assurance flags and 3D "
        "hardware &mdash; generated deterministically. Coverage spans ~2,150 "
        "fields across every major offshore region (333 in the Gulf of Mexico).</p>"
        f'<div class="cards">{"".join(cards)}</div>'
    )


def _safety_section() -> str:
    """Landing section for the offshore-safety / HSE surfaces published by
    :func:`build_marine_safety` and :func:`build_hse`. Cards link only the pages
    that exist on disk, so a partial build still produces a correct section."""
    cards = []
    if (PUBLIC / "marine_safety" / "executive_summary.html").exists():
        cards.append(
            '<a class="card" href="marine_safety/executive_summary.html">'
            "<h3>Marine Safety Analytics &rarr;</h3><p>Cross-database casualty "
            "analysis &mdash; foundering, fatality and hatch breakdowns over "
            "102,618 incident records (Canadian TSB, IMO GISIS, UK MAIB).</p></a>"
        )
    if (PUBLIC / "IMO_GISIS_Executive_Report.html").exists():
        cards.append(
            '<a class="card" href="IMO_GISIS_Executive_Report.html">'
            "<h3>IMO GISIS Casualties &rarr;</h3><p>13,338 marine casualties "
            "(1900&ndash;2025) by severity, vessel type and flag state, from the "
            "IMO GISIS public database.</p></a>"
        )
    if (PUBLIC / "hse" / "mooring-fatigue-grounded-card.html").exists():
        cards.append(
            '<a class="card" href="hse/mooring-fatigue-grounded-card.html">'
            "<h3>Mooring-Fatigue Grounded Card &rarr;</h3><p>Fatigue-life screening "
            "anchored to real BSEE mooring-failure incidents (DNV-OS-E301 T-N "
            "curves).</p></a>"
        )
    if not cards:
        return ""
    return (
        "<h2>Offshore safety &amp; HSE</h2>"
        "<p>Public marine-casualty and offshore-incident data, normalized and "
        "analysed deterministically &mdash; incident classification, cause-event "
        "breakdowns, and engineering screens anchored to real failures.</p>"
        f'<div class="cards">{"".join(cards)}</div>'
    )


def _insights_section() -> str:
    """Landing section for the life-cycle Insights hub + its front doors (issues
    #775/#776/#777/#779). Cards link only pages that exist on disk, so a partial
    build still produces a correct section."""
    cards = []
    if (PUBLIC / "capabilities" / "insights.html").exists():
        cards.append(
            '<a class="card" href="capabilities/insights.html">'
            "<h3>Life-cycle Insights hub &rarr;</h3><p>Every insight arranged along "
            "the well life-cycle spine &mdash; Drill &rarr; Complete &rarr; Produce "
            "&rarr; Workover &rarr; Decommission &mdash; plus the cross-cutting "
            "comparisons.</p></a>"
        )
    if (PUBLIC / "drilling-insights.html").exists():
        cards.append(
            '<a class="card" href="drilling-insights.html">'
            "<h3>Drilling learning curve &rarr;</h3><p>184 GoM Lower-Tertiary "
            "development wellbores burned 11,124 rig-days; depth explains only 11% "
            "of the spread &mdash; execution, not geology, drives the curve.</p></a>"
        )
    if (PUBLIC / "region-devtype-comparison.html").exists():
        cards.append(
            '<a class="card" href="region-devtype-comparison.html">'
            "<h3>Region &times; development-type &rarr;</h3><p>Deepwater is wet-tree "
            "country: past ~1500 m the dry-tree share of producing trees collapses "
            "from 80% on the shelf to 20% in ultra-deepwater.</p></a>"
        )
    if (PUBLIC / "all-regions-atlas.html").exists():
        cards.append(
            '<a class="card" href="all-regions-atlas.html">'
            "<h3>All-regions field atlas &rarr;</h3><p>205 countries at reference "
            "depth, the Gulf of Mexico at full life-cycle depth &mdash; the honest "
            "coverage map with RICH / SAMPLE / ROADMAP density badges.</p></a>"
        )
    if (PUBLIC / "decommissioning" / "pa-liability-wave.html").exists():
        cards.append(
            '<a class="card" href="decommissioning/pa-liability-wave.html">'
            "<h3>P&amp;A liability wave &rarr;</h3><p>8,161 GoM boreholes drilled but "
            "not permanently plugged &mdash; $65&ndash;73B of latent P&amp;A "
            "liability, with 3,288 temporarily-abandoned wells the imminent "
            "crest.</p></a>"
        )
    if not cards:
        return ""
    return (
        "<h2>Life-cycle insights</h2>"
        "<p>Front-door analyses along the offshore well life-cycle &mdash; drilling "
        "performance, development-concept mix, and the decommissioning liability "
        "wave &mdash; each a single thesis backed by a number, computed "
        "deterministically from public BSEE data.</p>"
        f'<div class="cards">{"".join(cards)}</div>'
    )


def build_index() -> None:
    cards = []
    if (PUBLIC / "portfolio.html").exists():
        cards.append(
            '<a class="card" href="portfolio.html"><h3>Portfolio Summary &rarr;</h3>'
            "<p>Field-by-field roll-up of the Lower-Tertiary play.</p></a>"
        )
    if (PUBLIC / "benchmark.html").exists():
        cards.append(
            '<a class="card" href="benchmark.html"><h3>Well Benchmarking &rarr;</h3>'
            "<p>Cross-field well performance, 2010&ndash;latest.</p></a>"
        )
    if (PUBLIC / "well-path.html").exists():
        cards.append(
            '<a class="card" href="well-path.html"><h3>Julia Well Paths (3D) &rarr;</h3>'
            "<p>Interactive 3D directional surveys, two renderers from one data contract.</p></a>"
        )
    if (PUBLIC / "completion" / "index.html").exists():
        cards.append(
            '<a class="card" href="completion/"><h3>Drilling &amp; Completion Days &rarr;</h3>'
            "<p>WAR-derived drilling and completion durations for 217 wells across "
            "the 12 Lower-Tertiary fields.</p></a>"
        )

    # Portfolio economics table, worst NPV first. Only list fields whose page
    # exists on disk, so the index stays consistent with the published tree.
    rows = []
    for slug, display, fname, npv_str, npv_val in sorted(
        _lower_tertiary_fields(), key=lambda f: f[4]
    ):
        if not (PUBLIC / fname).exists():
            continue
        rows.append(
            f'<tr><td><a href="{fname}">{display}</a></td>'
            f'<td style="text-align:right">{npv_str}</td></tr>'
        )
    econ_table = ""
    if rows:
        econ_table = (
            "<h2>Field economics (sanctioned V30 NPV)</h2>"
            "<p>Terminal life-to-date NPV at a 10% discount rate. Every field links to its "
            "full per-well stackup, NPV timeline, and critical-operations detail.</p>"
            '<div class="table-wrap"><table><thead><tr><th>Field</th>'
            '<th style="text-align:right">Terminal NPV</th></tr></thead><tbody>'
            + "".join(rows)
            + "</tbody></table></div>"
        )

    capabilities_section = ""
    if (PUBLIC / "capabilities" / "index.html").exists():
        capabilities_section = (
            "<h2>Capabilities overview</h2>"
            "<p>A single-page tour of every analytical surface in this repo &mdash; "
            "BSEE field economics, the field-development playbook, and multi-region "
            "production &amp; safety data &mdash; with the sanctioned figures it is "
            "validated against.</p>"
            '<div class="cards"><a class="card" href="capabilities/">'
            "<h3>Engineering Capabilities &rarr;</h3><p>What worldenergydata does, "
            "the governing data source behind each surface, and the live dashboards "
            "&mdash; in one page.</p></a></div>"
        )

    landing = page(
        "Open Data Outputs",
        "Deterministic petroleum-engineering analyses + an offshore "
        "field-development playbook on public data.",
        capabilities_section
        + _insights_section()
        + _field_development_section()
        + _safety_section()
        + f'<h2>Lower-Tertiary economics &amp; benchmarking</h2><div class="cards">'
        f'{"".join(cards)}</div>' + econ_table + "<h2>How this works</h2>"
        "<p>Every analysis here is computed by unit-tested domain code, frozen into a "
        "report artifact, and rendered to static HTML. There is no server and no API "
        "key &mdash; the numbers are identical for everyone, every time. Where the "
        "underlying data is incomplete, each page says so explicitly rather than "
        "filling the gap with a guess.</p>",
        provenance="All figures trace to public BSEE filings; see each page for its specific model.",
        data_limits=(
            "Two surfaces: (1) sanctioned Lower-Tertiary economics on US Gulf of "
            "Mexico BSEE data; (2) the field-development playbook over the SubseaIQ "
            "field catalog (~2014). Playbook concept recommendations are heuristic "
            "(Concept-Select / FEL-1 fidelity), reported in-sample, and are not a "
            "sanctioned design. Schematics are deterministic, generated from each "
            "field concept."
        ),
    )
    (PUBLIC / "index.html").write_text(landing, encoding="utf-8")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def build(domains: list[str] | None = None, *, clean: bool = False) -> None:
    """Build the site. ``domains=None`` (default) builds every registered domain,
    reproducing the pre-P2 monolithic output byte-for-byte. Pass a subset to do an
    incremental per-domain build over an existing (e.g. cache-restored) public/.
    The shared assets and the landing index are ALWAYS regenerated.
    ``clean=True`` wipes public/ first for a guaranteed-fresh full rebuild."""
    if clean and PUBLIC.exists():
        shutil.rmtree(PUBLIC)

    selected = list(DOMAINS) if domains is None else domains
    unknown = [d for d in selected if d not in DOMAINS]
    if unknown:
        raise SystemExit(
            f"Unknown domain(s): {', '.join(unknown)}. "
            f"Known domains: {', '.join(DOMAINS)}."
        )

    PUBLIC.mkdir(parents=True, exist_ok=True)
    available_viz = build_shared_assets()

    for name in selected:
        DOMAINS[name](available_viz)

    # Landing index always reflects the full on-disk tree.
    build_index()

    pages = sorted(p.name for p in PUBLIC.glob("*.html"))
    scope = "all domains" if domains is None else f"domains: {', '.join(selected)}"
    try:
        where = f"{PUBLIC.relative_to(ROOT)}/"
    except ValueError:  # PUBLIC redirected outside the repo (e.g. under test)
        where = str(PUBLIC)
    print(f"Built {len(pages)} page(s) into {where} ({scope}): {', '.join(pages)}")
    print(f"Copied {len(available_viz)} viz asset(s).")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--domains",
        help="Comma-separated list of domains to (re)build (default: all). "
        f"Known domains: {', '.join(DOMAINS)}.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Wipe public/ before building (full fresh rebuild).",
    )
    parser.add_argument(
        "--list-domains",
        action="store_true",
        help="Print the known domain keys (one per line) and exit.",
    )
    args = parser.parse_args(argv)

    if args.list_domains:
        for name in DOMAINS:
            print(name)
        return

    # ``--domains`` absent → None (full build). ``--domains ""`` (explicitly empty)
    # → build no domain pages but still regenerate shared assets + landing index
    # over the existing public/ tree.
    domains = None
    if args.domains is not None:
        domains = [d.strip() for d in args.domains.split(",") if d.strip()]
    build(domains=domains, clean=args.clean)


if __name__ == "__main__":
    main(sys.argv[1:])
