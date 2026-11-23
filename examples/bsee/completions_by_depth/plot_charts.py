"""Draw the completion charts as plain SVG from the output tables.

The charts are written without a plotting library: rectangles, lines and real
text only, with no pattern, clip path, filter or mask, so they render the same
in every viewer and the words stay editable. Each chart reads one or two of
the small CSV tables beside it and adds no number of its own.

Usage: python plot_charts.py [--out output]
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
BANDS = ["under 100 m", "100 to 500 m", "500 to 1500 m", "1500 m and deeper"]
BAND_LABELS = ["Under 100 m", "100 to 500 m", "500 to 1,500 m", "1,500 m and deeper"]
BAND_COLOURS = ["#a8ddd6", "#2BB2A6", "#0e7e88", "#0b3d5c"]  # shallow to deep
FLUIDS = ["oil", "gas", "oil and gas", "injection or source", "not reported"]
FLUID_LABELS = [
    "Oil",
    "Gas",
    "Oil and gas",
    "Injection or source",
    "No interval reported",
]
FLUID_COLOURS = ["#0b3d5c", "#2BB2A6", "#7fa3b5", "#9aa7b0", "#d5dde5"]
INK, MUTED, GRID = "#26323a", "#5a6b76", "#d0d7de"
FONT = "'Segoe UI',Helvetica,Arial,sans-serif"
W, H = 960, 540


def table(out, name):
    with open(Path(out) / f"{name}.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def text(x, y, words, size=16, anchor="start", weight="400", fill=INK):
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}" text-anchor="{anchor}">{escape(str(words))}</text>'
    )


def rect(x, y, w, h, fill, opacity=1.0, stroke="none"):
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w, 0):.1f}" '
        f'height="{max(h, 0):.1f}" fill="{fill}" fill-opacity="{opacity}" '
        f'stroke="{stroke}"/>'
    )


def line(x1, y1, x2, y2, stroke=GRID, width=1.0):
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="{width}"/>'
    )


def svg(parts, title, height=H):
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}" '
        f'width="{W}" height="{height}" role="img" aria-label="{escape(title)}" '
        f'font-family="{FONT}">'
    )
    return (
        "\n".join(
            [head, f"<title>{escape(title)}</title>", rect(0, 0, W, height, "#ffffff")]
            + parts
            + ["</svg>"]
        )
        + "\n"
    )


def legend(labels, colours, x, y, size=16, gap=26):
    parts = []
    for label, colour in zip(labels, colours):
        parts.append(rect(x, y - 13, 16, 16, colour))
        parts.append(text(x + 23, y + 1, label, size))
        x += 23 + len(label) * size * 0.56 + gap
    return parts


def nice_step(top):
    for step in (10, 20, 25, 50, 100, 200, 250, 500):
        if top / step <= 7:
            return step
    return 1000


def stacked_years(
    series, years, labels, colours, axis_title, part_year, dots=None, dot_label=""
):
    """Stacked bars by year; series maps a key to a list aligned with years."""
    left, right, top, bottom = 76, 24, 96, 62
    plot_w, plot_h = W - left - right, H - top - bottom
    totals = [sum(series[k][i] for k in series) for i in range(len(years))]
    peak = max(totals + (dots or [0]))
    step = nice_step(peak)
    y_max = step * (int(peak / step) + 1)
    slot = plot_w / len(years)
    bar = slot * 0.72

    def y_of(v):
        return top + plot_h - plot_h * v / y_max

    parts = legend(labels, colours, left, 34)
    if dots:
        cx = left + 8
        parts.append(
            f'<circle cx="{cx}" cy="58" r="5.5" fill="#ffffff" stroke="{INK}" stroke-width="2"/>'
        )
        parts.append(text(cx + 15, 64, dot_label, 16))
    for tick in range(0, y_max + 1, step):
        parts.append(line(left, y_of(tick), W - right, y_of(tick)))
        parts.append(
            text(left - 10, y_of(tick) + 6, f"{tick:,}", 16, "end", fill=MUTED)
        )
    for i, year in enumerate(years):
        x = left + i * slot + (slot - bar) / 2
        base = 0
        faded = 0.45 if year == part_year else 1.0
        for key, colour in zip(series, colours):
            v = series[key][i]
            parts.append(
                rect(x, y_of(base + v), bar, plot_h * v / y_max, colour, faded)
            )
            base += v
        if not dots:  # circles would sit on the totals
            parts.append(
                text(x + bar / 2, y_of(base) - 7, f"{base:,}", 13, "middle", fill=INK)
            )
        if dots:
            parts.append(
                f'<circle cx="{x + bar / 2:.1f}" cy="{y_of(dots[i]):.1f}" r="5.5" '
                f'fill="#ffffff" stroke="{INK}" stroke-width="2"/>'
            )
        # The tick beside a part year is left out so the two labels stay apart.
        if (year % 5 == 0 and year + 1 != part_year) or year == part_year:
            label = f"{year}*" if year == part_year else str(year)
            parts.append(
                text(x + bar / 2, top + plot_h + 24, label, 16, "middle", fill=MUTED)
            )
    parts.append(line(left, top + plot_h, W - right, top + plot_h, INK, 1.2))
    parts.append(
        f'<text x="20" y="{top + plot_h / 2:.1f}" font-size="16" fill="{MUTED}" '
        f'text-anchor="middle" transform="rotate(-90 20 {top + plot_h / 2:.1f})">'
        f"{escape(axis_title)}</text>"
    )
    if part_year:
        parts.append(
            text(
                W - right,
                H - 12,
                f"* {part_year} is a part year, to 23 Nov; bars are lighter",
                14,
                "end",
                fill=MUTED,
            )
        )
    return parts


def by_year_band(rows, value, years, where=lambda r: True):
    series = {b: [0] * len(years) for b in BANDS}
    for r in rows:
        if r["band"] in series and where(r):
            series[r["band"]][years.index(int(r["year"]))] += int(r[value])
    return series


def chart_approvals(out):
    rows = table(out, "completion_approvals_by_year_band")
    years = sorted({int(r["year"]) for r in rows})
    part = next((int(r["year"]) for r in rows if r["partial_year"] == "True"), None)
    series = by_year_band(rows, "approvals", years)
    title = "Completion approvals by year and water depth, stacked bars"
    return svg(
        stacked_years(
            series,
            years,
            BAND_LABELS,
            BAND_COLOURS,
            "Approved completion permits",
            part,
        ),
        title,
    )


def chart_bores(out):
    rows = table(out, "bores_first_completed_by_year_band")
    years = sorted({int(r["year"]) for r in rows})
    part = next((int(r["year"]) for r in rows if r["partial_year"] == "True"), None)
    series = by_year_band(rows, "bores", years, lambda r: r["basis"] == "approval")
    report = by_year_band(rows, "bores", years, lambda r: r["basis"] == "report")
    dots = [sum(report[b][i] for b in BANDS) for i in range(len(years))]
    title = (
        "Bores first completed by year and water depth, "
        "from approvals (bars) and from reports (circles)"
    )
    return svg(
        stacked_years(
            series,
            years,
            BAND_LABELS,
            BAND_COLOURS,
            "Bores first completed",
            part,
            dots,
            "All water depths, by the End of Operations Report (status date)",
        ),
        title,
    )


def chart_fluid(out):
    rows = table(out, "fluid_by_year")
    years = sorted({int(r["year"]) for r in rows})
    part = next((int(r["year"]) for r in rows if r["partial_year"] == "True"), None)
    series = {f: [0] * len(years) for f in FLUIDS}
    for r in rows:
        key = r["fluid"] if r["fluid"] in series else "not reported"
        series[key][years.index(int(r["year"]))] += int(r["bores"])
    title = (
        "Bores first reported completed by year, "
        "by the fluid their completion status codes name"
    )
    return svg(
        stacked_years(
            series,
            years,
            FLUID_LABELS,
            FLUID_COLOURS,
            "Bores first reported completed",
            part,
        ),
        title,
    )


def chart_drilled(out):
    rows = table(out, "drilled_to_completed")
    kinds = [
        ("development", "Development wells", "#0b3d5c"),
        ("exploration", "Exploration wells", "#2BB2A6"),
    ]
    groups = BANDS + ["all water depths"]
    labels = BAND_LABELS + ["All water depths"]
    left, right, top, row_h = 208, 150, 70, 78
    height = top + row_h * len(groups) + 56
    plot_w = W - left - right
    parts = legend([k[1] for k in kinds], [k[2] for k in kinds], left, 34)
    for tick in range(0, 101, 20):
        x = left + plot_w * tick / 100
        parts.append(line(x, top, x, top + row_h * len(groups)))
        parts.append(
            text(x, top + row_h * len(groups) + 24, f"{tick}", 16, "middle", fill=MUTED)
        )
    parts.append(
        text(
            left + plot_w / 2,
            height - 8,
            "Wells with an initial completion approval (%)",
            16,
            "middle",
            fill=MUTED,
        )
    )
    for g, (band, label) in enumerate(zip(groups, labels)):
        y0 = top + g * row_h
        weight = "600" if band == "all water depths" else "400"
        parts.append(text(left - 12, y0 + row_h / 2 + 6, label, 16, "end", weight))
        for k, (kind, _, colour) in enumerate(kinds):
            r = next(x for x in rows if x["well_type"] == kind and x["band"] == band)
            share = float(r["share_percent"])
            y = y0 + 12 + k * 28
            parts.append(rect(left, y, plot_w * share / 100, 24, colour))
            note = (
                f"{share:.0f} %  ({int(r['with_initial_completion_approval']):,} "
                f"of {int(r['wells_first_drilled']):,})"
            )
            x = left + plot_w * share / 100 + 8
            parts.append(rect(x - 4, y, len(note) * 8.4 + 8, 24, "#ffffff"))
            parts.append(text(x, y + 18, note, 15))
    parts.append(line(left, top, left, top + row_h * len(groups), INK, 1.2))
    title = (
        "Share of wells first drilled 2005 to 2025 with an initial completion "
        "approval, by well type and water depth"
    )
    return svg(parts, title, height)


CHARTS = {
    "01_completion_approvals": chart_approvals,
    "02_bores_first_completed": chart_bores,
    "03_fluid_by_year": chart_fluid,
    "04_drilled_to_completed": chart_drilled,
}


def main(out):
    for name, draw in CHARTS.items():
        content = draw(out)
        for banned in ("<pattern", "clipPath", "clip-path", "<filter", "<mask"):
            if banned in content:
                raise ValueError(f"{name}: {banned} is not portable")
        (Path(out) / f"{name}.svg").write_text(content, encoding="utf-8")
        print(name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "output")
    main(parser.parse_args().out)
