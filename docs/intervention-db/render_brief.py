#!/usr/bin/env python3
"""Render the generated intervention brief Markdown into a self-contained,
client-ready HTML deliverable (and, via headless Chrome, a PDF).

The Markdown at ``intervention-stats-brief.generated.md`` is the source of
truth (auto-generated from the committed source YAMLs). This script is a pure
presentation layer: it converts that Markdown to a single HTML file with
inline print CSS, a branded header/footer, and page-break-friendly tables.

Usage:
    python3 render_brief.py            # render default in/out paths
    python3 render_brief.py SRC.md OUT.html

No external assets are emitted: all CSS is inlined and the brief is text+tables
only (no images), so the HTML/PDF are fully portable.
"""

from __future__ import annotations

import datetime as _dt
import re
import subprocess
import sys
from pathlib import Path

import figures
import markdown

HEADER_TITLE = (
    "Frontier Deepwater / ACE Engineering "
    "— GoM Subsea Well Intervention &amp; Maintenance"
)
SOURCES_LINE = "sources: committed YAMLs #583/#586/#587/#596/#598/#629/#630/#638"

CSS = """
:root {
  --ink: #15202b;
  --muted: #5b6b7b;
  --accent: #0b3d5c;
  --accent-soft: #e8eef3;
  --rule: #cdd7e0;
  --zebra: #f5f8fa;
}
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  font-family: "Helvetica Neue", Helvetica, Arial, "Segoe UI", sans-serif;
  color: var(--ink);
  line-height: 1.45;
  margin: 0;
  font-size: 11pt;
}
.page { max-width: 980px; margin: 0 auto; padding: 0 28px 48px; }

.brief-header {
  border-bottom: 3px solid var(--accent);
  padding: 22px 0 14px;
  margin-bottom: 8px;
}
.brief-header .brand {
  font-size: 15pt;
  font-weight: 700;
  color: var(--accent);
  letter-spacing: 0.2px;
}
.brief-header .meta {
  font-size: 9pt;
  color: var(--muted);
  margin-top: 4px;
}

.brief-footer {
  border-top: 1px solid var(--rule);
  margin-top: 36px;
  padding-top: 10px;
  font-size: 8.5pt;
  color: var(--muted);
}
.brief-footer .sources { font-weight: 600; color: var(--accent); }

h1 {
  font-size: 18pt;
  color: var(--accent);
  margin: 18px 0 6px;
  line-height: 1.2;
}
h2 {
  font-size: 13.5pt;
  color: var(--accent);
  border-bottom: 1px solid var(--rule);
  padding-bottom: 4px;
  margin: 26px 0 10px;
  page-break-after: avoid;
}
h3 {
  font-size: 11.5pt;
  color: var(--ink);
  margin: 18px 0 6px;
  page-break-after: avoid;
}
p { margin: 8px 0; }
strong { color: var(--ink); }

ul { margin: 8px 0 8px 0; padding-left: 22px; }
li { margin: 3px 0; }

code {
  background: var(--accent-soft);
  padding: 1px 4px;
  border-radius: 3px;
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
  font-size: 9.5pt;
}

table {
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0 16px;
  font-size: 9.5pt;
  page-break-inside: avoid;
}
thead { display: table-header-group; }
tr { page-break-inside: avoid; }
th, td {
  border: 1px solid var(--rule);
  padding: 5px 8px;
  text-align: left;
  vertical-align: top;
}
th {
  background: var(--accent);
  color: #fff;
  font-weight: 600;
}
tbody tr:nth-child(even) { background: var(--zebra); }

figure.brief-fig {
  margin: 16px 0 18px;
  padding: 10px 12px 8px;
  border: 1px solid var(--rule);
  border-radius: 6px;
  background: #fff;
  page-break-inside: avoid;
}
figure.brief-fig svg { display: block; margin: 0 auto; }
figure.brief-fig figcaption {
  margin-top: 8px;
  font-size: 8.5pt;
  color: var(--muted);
  line-height: 1.35;
}
figure.brief-fig figcaption .cap { color: var(--ink); }
figure.brief-fig figcaption .src {
  color: var(--accent);
  font-weight: 600;
  white-space: nowrap;
}

@page {
  size: letter;
  margin: 14mm 12mm 14mm 12mm;
}
@media print {
  .page { max-width: none; padding: 0; }
}
"""


def _figure_html(meta: dict, svg_markup: str) -> str:
    """Wrap one figure's inline SVG with a caption + source tag."""
    return (
        '<figure class="brief-fig">'
        f"{svg_markup}"
        "<figcaption>"
        f'<span class="cap">{meta["caption"]}</span> '
        f'<span class="src">source: {meta["source"]}</span>'
        "</figcaption></figure>"
    )


def insert_figures(body_html: str) -> str:
    """Append each registered figure's inline SVG to the end of its anchor
    brief section (matched on the <h2> heading text). Section-anchored so the
    auto-generated Markdown stays the untouched source of truth.
    """
    svgs = figures.build_all()
    by_section: dict[str, list[dict]] = {}
    for meta in figures.FIGURES:
        by_section.setdefault(meta["section"], []).append(meta)
    for metas in by_section.values():
        metas.sort(key=lambda m: m["order"])

    # split the body into chunks that each begin with an <h2> heading
    chunks = re.split(r"(?=<h2)", body_html)
    out: list[str] = []
    for chunk in chunks:
        m = re.match(r"<h2[^>]*>(.*?)</h2>", chunk, re.S)
        if m:
            heading = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            for section, metas in by_section.items():
                if section.lower() in heading.lower():
                    blocks = "".join(
                        _figure_html(meta, svgs[meta["key"]]) for meta in metas
                    )
                    chunk = chunk + blocks
                    break
        out.append(chunk)
    return "".join(out)


def write_pdf(html_path: Path) -> Path | None:
    """Render the HTML to PDF via headless Chrome (inline SVG prints as
    foreground vector markup, so it survives the print-to-pdf pipeline).
    """
    pdf_path = html_path.with_suffix(".pdf")
    chrome = next(
        (
            c
            for c in (
                "google-chrome",
                "google-chrome-stable",
                "chromium",
                "chromium-browser",
            )
            if _which(c)
        ),
        None,
    )
    if not chrome:
        print("WARNING: no Chrome binary found; skipped PDF", file=sys.stderr)
        return None
    subprocess.run(
        [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            html_path.as_uri(),
        ],
        check=True,
        capture_output=True,
    )
    return pdf_path


def _which(name: str) -> bool:
    from shutil import which

    return which(name) is not None


def render_html(md_text: str, generated_date: str) -> str:
    body = markdown.markdown(
        md_text,
        extensions=["tables", "sane_lists"],
        output_format="html5",
    )
    body = insert_figures(body)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GoM Subsea Well Intervention &amp; Maintenance — Brief</title>
<style>{CSS}</style>
</head>
<body>
<div class="page">
  <header class="brief-header">
    <div class="brand">{HEADER_TITLE}</div>
    <div class="meta">Client-ready brief &middot; generated {generated_date}</div>
  </header>
  <main>
{body}
  </main>
  <footer class="brief-footer">
    <div>Generated {generated_date}</div>
    <div class="sources">{SOURCES_LINE}</div>
  </footer>
</div>
</body>
</html>
"""


def main(argv: list[str]) -> int:
    here = Path(__file__).resolve().parent
    src = (
        Path(argv[1])
        if len(argv) > 1
        else (here / "intervention-stats-brief.generated.md")
    )
    out = Path(argv[2]) if len(argv) > 2 else (here / "intervention-stats-brief.html")
    md_text = src.read_text(encoding="utf-8")
    generated_date = _dt.date.today().isoformat()
    html = render_html(md_text, generated_date)
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    # refresh the standalone reusable SVG assets alongside the brief
    figures.write_standalone(here / "figures")
    pdf = write_pdf(out)
    if pdf is not None:
        print(f"wrote {pdf} ({pdf.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
