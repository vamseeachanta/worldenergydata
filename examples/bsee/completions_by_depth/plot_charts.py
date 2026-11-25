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
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
# Keep the standalone chart command usable from a source checkout.
sys.path.insert(0, str(ROOT.parents[2] / "packages/worldenergydata-bsee/src"))
from worldenergydata.bsee.half_decade import PERIODS, render_svg  # noqa: E402

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


def svg(parts, title, height=H, font=FONT):
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}" '
        f'width="{W}" height="{height}" role="img" aria-label="{escape(title)}" '
        f'font-family="{font}">'
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
        for key, colour in zip(series, colours):
            v = series[key][i]
            parts.append(rect(x, y_of(base + v), bar, plot_h * v / y_max, colour))
            base += v
        if year == part_year:
            # A dashed outline marks the part year; the colours stay as in
            # the legend, so a faded band is not read as another band.
            parts.append(
                f'<rect x="{x - 3:.1f}" y="{y_of(base) - 3:.1f}" '
                f'width="{bar + 6:.1f}" height="{plot_h * base / y_max + 3:.1f}" '
                f'fill="none" stroke="{INK}" stroke-width="1.5" '
                f'stroke-dasharray="5 4"/>'
            )
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
                f"* {part_year} is a part year, to 23 Nov; dashed outline",
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
        "Bores with a first completion record by year and water depth: first "
        "initial completion approval (bars) and first completion report (circles)"
    )
    return svg(
        stacked_years(
            series,
            years,
            BAND_LABELS,
            BAND_COLOURS,
            "Bores with a first completion record",
            part,
            dots,
            "All water depths, by first completion report (earliest status date)",
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
        "Bores with a first completion report by year, "
        "by the fluid their completion status codes name"
    )
    return svg(
        stacked_years(
            series,
            years,
            FLUID_LABELS,
            FLUID_COLOURS,
            "Bores with a first completion report",
            part,
        ),
        title,
    )


DRILLED_NOTE = (
    "Shares count wells with an initial completion approval recorded by 23 November 2026. "
    "Later cohorts have had less time for approval, especially wells first drilled in "
    "2025 to 2026 (partial). Equal shares have overlapping markers. "
    "Some groups contain only one or two wells. The table gives the counts. "
    "An empty share means no wells were drilled in that group."
)


def chart_drilled(out):
    rows = table(out, "04_drilled_to_completed")
    return render_svg(
        [dict(row, value=row["share_percent"]) for row in rows],
        ylabel="Share of drilled wells (%)",
        xlabel="Period of first drilling",
        note=DRILLED_NOTE,
    )


CHARTS = {
    "01_completion_approvals": chart_approvals,
    "02_bores_first_completed": chart_bores,
    "03_fluid_by_year": chart_fluid,
    "04_drilled_to_completed": chart_drilled,
}


def finding(sentence, rows, column, decimals):
    return finding_from_cells(sentence, [(row, column, decimals) for row in rows])


def finding_from_cells(sentence, readings):
    """Keep the CSV coordinates and display precision of each quoted value."""
    cells = []
    values = []
    for row, column, decimals in readings:
        cells.append(
            dict(
                row={k: row[k] for k in ("group", "period", "band")},
                column=column,
                decimals=decimals,
            )
        )
        values.append(f"{float(row[column]):,.{decimals}f}")
    return dict(text=sentence.format(*values), cells=cells)


def complete_period_comparison(cells, band, group, metric, column, decimals):
    first = cells[group, "2005 to 2009", band]
    last = cells[group, "2020 to 2024", band]
    start, end = float(first[column]), float(last[column])
    direction = "went"
    if end != start:
        direction = "rose" if end > start else "fell"
    return finding(
        f"In the {band.lower()} band, {metric} {direction} from {{0}} in {first['period']} "
        f"to {{1}} in {last['period']}.",
        [first, last],
        column,
        decimals,
    )


def recompletion_findings(cells):
    shallow, deep = BAND_LABELS[0], BAND_LABELS[3]
    first, peak, last = "2005 to 2009", "2015 to 2019", "2020 to 2024"
    groups = ("Recompletion", "Modify Perforations", "Reperforation")
    early = [cells[group, first, shallow] for group in groups]
    return [
        finding(
            "Under 100 m in 2005 to 2009, annual approvals reached full period highs of "
            "{0} for recompletion, {1} for other approvals flagged Modify Perforations "
            "and {2} for other approvals flagged Reperforation.",
            early,
            "value",
            1,
        ),
        finding(
            "The under 100 m band in 2005 to 2009 accounted for {0}% of all recompletion approvals, "
            "{1}% of other completion approvals flagged Modify Perforations and {2}% of "
            "those flagged Reperforation.",
            early,
            "cell_share_of_group_percent",
            1,
        ),
        finding(
            "Across all periods, the under 100 m band accounted for {0}% of recompletion "
            "approvals, {1}% of other completion approvals flagged Modify Perforations "
            "and {2}% of those flagged Reperforation.",
            early,
            "band_share_of_group_percent",
            1,
        ),
        finding(
            "At 1,500 m and deeper, annual recompletion approvals rose from {0} in 2005 to "
            "2009 to {1} in 2015 to 2019, then fell to {2} in 2020 to 2024. Other "
            "completion approvals flagged Modify Perforations fell from {3} to {4} per "
            "year between the first and last of those periods.",
            [cells["Recompletion", p, deep] for p in (first, peak, last)]
            + [cells["Modify Perforations", p, deep] for p in (first, last)],
            "value",
            1,
        ),
    ]


def pilot_figures(out):
    figures = []
    annual_note = (
        "Final bin uses two calendar years. The BSEE file covers 2026 to 23 November."
    )
    for stem, question, ylabel, note in [
        (
            "01_approvals_by_period",
            "How did initial and other completion approvals vary by depth and period?",
            "Approvals per calendar year",
            annual_note,
        ),
        (
            "02_recompletion_by_period",
            "Where and when did recompletions and perforation work receive approval?",
            "Approvals per calendar year",
            annual_note
            + " Perforation flags are counted among other completion approvals. "
            "One approval can carry both flags.",
        ),
        (
            "03_approvals_per_well",
            "How did completion approvals per January well year vary by depth and period?",
            "Approvals per January well year",
            "Total initial and other completion approvals are divided by the sum of the "
            "1 January standing well inventories. Approvals include wells drilled after "
            "1 January. The snapshot ends on 23 November 2026.",
        ),
    ]:
        rows = table(out, stem)
        cells = {(r["group"], r["period"], r["band"]): r for r in rows}
        chart_rows = rows
        if stem == "01_approvals_by_period":
            bullets = [
                complete_period_comparison(cells, band, group, metric, "value", 1)
                for group, metric in (
                    ("Initial completion", "initial completion approvals per year"),
                    ("Other completion work", "other completion approvals per year"),
                )
                for band in (BAND_LABELS[0], BAND_LABELS[3])
            ]
        elif stem == "02_recompletion_by_period":
            bullets = recompletion_findings(cells)
        else:
            rate = "approvals_per_january_well_year"
            chart_rows = [dict(r, value=r[rate]) for r in rows]
            bullets = [
                complete_period_comparison(
                    cells,
                    band,
                    "",
                    "completion approvals per January well year",
                    rate,
                    2,
                )
                for band in (BAND_LABELS[0], BAND_LABELS[3])
            ]
            bullets.append(
                finding(
                    "Completion approvals per January well year were higher at 1,500 m "
                    "and deeper than under 100 m in both 2005 to 2009 ({0} versus {1}) "
                    "and 2020 to 2024 ({2} versus {3}).",
                    [
                        cells["", period, band]
                        for period in ("2005 to 2009", "2020 to 2024")
                        for band in (BAND_LABELS[3], BAND_LABELS[0])
                    ],
                    rate,
                    2,
                )
            )
        chart = render_svg(chart_rows, ylabel=ylabel, note=note)
        (out / f"{stem}.svg").write_text(chart, encoding="utf-8", newline="\n")
        figures.append(
            dict(
                svg=f"{stem}.svg",
                csv=f"{stem}.csv",
                question=question,
                note=note,
                bullets=bullets,
            )
        )

    drilled = {
        (r["group"], r["band"], r["period"]): r
        for r in table(out, "04_drilled_to_completed")
    }
    exploratory, development = "Exploratory wells", "Development wells"
    shallow, deep = BAND_LABELS[0], BAND_LABELS[-1]
    first, last_full, partial = PERIODS[0], PERIODS[-2], PERIODS[-1]
    early_shallow = drilled[exploratory, shallow, first]
    late_shallow = drilled[exploratory, shallow, last_full]
    bullets = [
        finding_from_cells(
            f"Under 100 m, {{0}} of {{1}} exploratory wells first drilled in {first} "
            f"had an initial approval, compared with {{2}} of {{3}} in {last_full}.",
            [
                (row, column, 0)
                for row in (early_shallow, late_shallow)
                for column in (
                    "with_initial_completion_approval",
                    "wells_first_drilled",
                )
            ],
        ),
        finding(
            f"At 1,500 m and deeper, {{0}}% of exploratory wells first drilled in "
            f"{first} had an initial approval, compared with {{1}}% in {last_full}.",
            [drilled[exploratory, deep, period] for period in (first, last_full)],
            "share_percent",
            1,
        ),
        finding(
            f"Comparing {first} with {last_full}, the share of development wells with an "
            "initial approval rose from {0}% to {1}% under 100 m. At 1,500 m and deeper "
            "the shares were {2}% and {3}%.",
            [
                drilled[development, band, period]
                for band in (shallow, deep)
                for period in (first, last_full)
            ],
            "share_percent",
            1,
        ),
        finding(
            f"At 1,500 m and deeper in {partial}, {{0}}% of exploratory wells "
            "and {1}% of development wells had an initial approval by the snapshot.",
            [drilled[group, deep, partial] for group in (exploratory, development)],
            "share_percent",
            1,
        ),
    ]
    figures.append(
        dict(
            svg="04_drilled_to_completed.svg",
            csv="04_drilled_to_completed.csv",
            question="What share of drilled wells had an initial completion approval "
            "by water depth, well type and period of first drilling?",
            note=DRILLED_NOTE,
            bullets=bullets,
        )
    )
    (out / "figures.json").write_text(
        json.dumps(figures, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def main(out):
    for name, draw in CHARTS.items():
        content = draw(out)
        for banned in ("<pattern", "clipPath", "clip-path", "<filter", "<mask"):
            if banned in content:
                raise ValueError(f"{name}: {banned} is not portable")
        (Path(out) / f"{name}.svg").write_text(content, encoding="utf-8")
        print(name)
    pilot_figures(Path(out))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "output")
    main(parser.parse_args().out)
