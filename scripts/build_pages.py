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
"""
from __future__ import annotations

import html
import re
import shutil
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
        if stripped.startswith("|") and i + 1 < n and re.match(r"^\s*\|[\s:\-|]+\|\s*$", lines[i + 1]):
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
            out.append("<ul>" + "".join(f"<li>{_inline(it)}</li>" for it in items) + "</ul>")
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

def page(title: str, subtitle: str, body: str, *, provenance: str, data_limits: str) -> str:
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


def build():
    PUBLIC.mkdir(exist_ok=True)
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / "style.css").write_text(STYLE, encoding="utf-8")

    # --- copy the self-contained viz HTML as assets ---
    # Prefer the committed site_assets/ copy (what CI publishes); fall back to the
    # gitignored reports/bsee/ scratch output for local-only rebuilds.
    viz_names = ["julia_well_path_plotly.html", "julia_well_path_threejs.html"]
    available_viz = {}
    for name in viz_names:
        for src in (SITE_ASSETS / name, REPORTS / "bsee" / name):
            if src.exists():
                shutil.copy2(src, ASSETS / name)
                available_viz[name] = True
                break

    # --- Economics page (sanctioned V30) ---
    econ_md = REPORTS / "lower_tertiary" / "field_economics_julia_v30.md"
    if econ_md.exists():
        body = md_to_html(econ_md.read_text(encoding="utf-8"))
        (PUBLIC / "economics.html").write_text(page(
            "Julia Field Economics",
            "Per-well and field-level NPV from the sanctioned V30 financial model.",
            body,
            provenance=(
                "Computed by the V30 cashflow model "
                "(<code>build_field_npv_timeline</code>), which reuses the same "
                "monthly cashflow and trimmed-discount formula as "
                "<code>reproduce_v30_financials</code>. Terminal NPV reconciles "
                "exactly to the sanctioned baseline (residual $0.0000)."
            ),
            data_limits=(
                "NPV is <strong>negative ($-530.6 M)</strong> &mdash; this is the "
                "sanctioned model truth and is presented as-is, not reframed as "
                "value-positive. Operation markers (drilling/completion dates) are "
                "annotations only and do not feed the cashflow model. OGOR-A "
                "production zips are pickled <code>.bin</code> DataFrames in this checkout."
            ),
        ), encoding="utf-8")

    # --- Well-path page ---
    if available_viz:
        links = []
        if "julia_well_path_plotly.html" in available_viz:
            links.append('<a href="assets/julia_well_path_plotly.html">Open Plotly version &rarr;</a>')
        if "julia_well_path_threejs.html" in available_viz:
            links.append('<a href="assets/julia_well_path_threejs.html">Open Three.js version &rarr;</a>')
        primary = "julia_well_path_plotly.html" if "julia_well_path_plotly.html" in available_viz else next(iter(available_viz))
        wp_body = (
            f'<iframe class="viz-frame" src="assets/{primary}" title="Julia well paths"></iframe>'
            f'<p class="viz-links">{" &middot; ".join(links)}</p>'
            '<p>3D directional surveys for the Julia (G20351) development wells, rendered '
            'from a frozen JSON contract by two independent renderers (Plotly &amp; Three.js).</p>'
        )
        (PUBLIC / "well-path.html").write_text(page(
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
        ), encoding="utf-8")

    # --- Landing page ---
    cards = []
    if (PUBLIC / "economics.html").exists():
        cards.append('<a class="card" href="economics.html"><h3>Julia Field Economics &rarr;</h3>'
                     '<p>Sanctioned V30 NPV: timeline, per-well stackup, and critical-operations annotations.</p></a>')
    if (PUBLIC / "well-path.html").exists():
        cards.append('<a class="card" href="well-path.html"><h3>Julia Well Paths (3D) &rarr;</h3>'
                     '<p>Interactive 3D directional surveys, two independent renderers from one data contract.</p></a>')
    landing = page(
        "Open Data Outputs",
        "Deterministic petroleum-engineering analyses on public US Gulf of Mexico data.",
        f'<div class="cards">{"".join(cards)}</div>'
        '<h2>How this works</h2>'
        '<p>Every analysis here is computed by unit-tested domain code, frozen into a '
        'report artifact, and rendered to static HTML. There is no server and no API '
        'key &mdash; the numbers are identical for everyone, every time. Where the '
        'underlying data is incomplete, each page says so explicitly rather than '
        'filling the gap with a guess.</p>',
        provenance="All figures trace to public BSEE filings; see each page for its specific model.",
        data_limits=(
            "Scope is currently the Julia (G20351) Lower-Tertiary subsea development. "
            "Water-depth and HPHT attributes are not present in the structured OGOR-A "
            "data and are therefore not shown."
        ),
    )
    (PUBLIC / "index.html").write_text(landing, encoding="utf-8")

    pages = sorted(p.name for p in PUBLIC.glob("*.html"))
    print(f"Built {len(pages)} pages into {PUBLIC.relative_to(ROOT)}/: {', '.join(pages)}")
    print(f"Copied {len(available_viz)} viz asset(s).")


if __name__ == "__main__":
    build()
