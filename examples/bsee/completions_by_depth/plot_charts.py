"""Draw the completion charts as plain SVG from the output tables.

The yearly main figures read the chart values and moving averages from their
companion CSV files. The manifest identifies the cells behind each reading.

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
from worldenergydata.bsee.yearly_trend import BANDS as DEPTH_LABELS  # noqa: E402
from worldenergydata.bsee.yearly_trend import (  # noqa: E402
    depth_y_scale,
    render_svg,
    shared_depth_y_scales,
)

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


def legend(labels, colours, x, y, size=17, gap=26):
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
        parts.append(text(cx + 15, 64, dot_label, 17))
    for tick in range(0, y_max + 1, step):
        parts.append(line(left, y_of(tick), W - right, y_of(tick)))
        parts.append(
            text(left - 10, y_of(tick) + 6, f"{tick:,}", 17, "end", fill=MUTED)
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
                text(x + bar / 2, y_of(base) - 7, f"{base:,}", 17, "middle", fill=INK)
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
                text(x + bar / 2, top + plot_h + 24, label, 17, "middle", fill=MUTED)
            )
    parts.append(line(left, top + plot_h, W - right, top + plot_h, INK, 1.2))
    parts.append(
        f'<text x="20" y="{top + plot_h / 2:.1f}" font-size="17" fill="{MUTED}" '
        f'text-anchor="middle" transform="rotate(-90 20 {top + plot_h / 2:.1f})">'
        f"{escape(axis_title)}</text>"
    )
    if part_year:
        parts.append(
            text(
                W - right,
                H - 12,
                f"* {part_year} is a part year, to 23 Nov; dashed outline",
                17,
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


CHARTS = {
    "02_bores_first_completed": chart_bores,
    "03_fluid_by_year": chart_fluid,
}

CUTOFF = "Hollow markers show partial 2026 through 23 November. Averages end in 2025."
FIGURES = (
    (
        "1",
        "01_approvals_by_period",
        "Initial and other completion approvals",
        "How did initial and other completion approvals vary by depth and year?",
        "Completion approvals (permits per year)",
        "Calendar year of approval",
        CUTOFF,
    ),
    (
        "2",
        "02_recompletion_by_period",
        "Recompletion approvals",
        "Where and when did recompletions receive approval?",
        "Approved permits per year",
        "Calendar year of approval",
        CUTOFF,
    ),
    (
        "3",
        "03_perforation_flags",
        "Other completion approvals with perforation flags",
        "Where and when did other completion approvals carry perforation flags?",
        "Approved permits per year",
        "Calendar year of approval",
        CUTOFF
        + " The perforation flags apply to other completion approvals. One permit can carry both.",
    ),
    (
        "4",
        "04_drilled_to_completed",
        "Drilled wells with an initial completion approval",
        "What share of drilled wells had an initial completion approval by water "
        "depth, well type and year of first drilling?",
        "Share of drilled wells (%)",
        "Year of first drilling",
        "Approvals are observed through 23 November 2026. Later cohorts have had less "
        "time for approval. "
        "Hollow markers show partial 2026. Blank shares mean no wells were drilled. "
        "Equal shares overlap.",
    ),
    (
        "E3",
        "03_approvals_per_well",
        "Completion approvals per January well year",
        "How did completion approvals per January well year vary by depth and year?",
        "Completion approvals per well standing on 1 January",
        "Calendar year of approval",
        CUTOFF + " Approvals include wells drilled after 1 January.",
    ),
)


def figure_findings(stem, rows):
    cells = {(r["group"], int(r["year"]), r["band"]): r for r in rows}
    shallow, deep = DEPTH_LABELS[0], DEPTH_LABELS[-1]

    def reading(sentence, column, decimals, *keys):
        references, values = [], []
        for key in keys:
            row = cells[key]
            references.append(
                dict(
                    row={k: row[k] for k in ("group", "year", "band")},
                    column=column,
                    decimals=decimals,
                )
            )
            values.append(f"{float(row[column]):,.{decimals}f}")
        return dict(text=sentence.format(*values), cells=references)

    if stem == "01_approvals_by_period":
        initial, other = "Initial completion", "Other completion work"
        return [
            reading(
                "In 2025, initial approvals numbered {0} under 100 m and {1} at 1,500 "
                "m and deeper.",
                "value",
                0,
                (initial, 2025, shallow),
                (initial, 2025, deep),
            ),
            reading(
                "Under 100 m, the five year average for initial approvals fell from "
                "{0} per year in 2009 to {1} in 2025.",
                "moving_average",
                0,
                (initial, 2009, shallow),
                (initial, 2025, shallow),
            ),
            reading(
                "At 1,500 m and deeper, other approvals increased from a five year "
                "average of {0} per year in 2009 to {1} in 2025.",
                "moving_average",
                0,
                (other, 2009, deep),
                (other, 2025, deep),
            ),
        ]
    if stem == "03_perforation_flags":
        return [
            reading(
                "Under 100 m in 2025, {0} other approvals carried Modify Perforations "
                "and {1} carried Reperforation.",
                "value",
                0,
                ("Modify Perforations", 2025, shallow),
                ("Reperforation", 2025, shallow),
            ),
            reading(
                "Under 100 m in 2025, the five year average was {0} approvals per year "
                "for Modify Perforations and {1} for Reperforation.",
                "moving_average",
                0,
                ("Modify Perforations", 2025, shallow),
                ("Reperforation", 2025, shallow),
            ),
        ]
    if stem == "02_recompletion_by_period":
        zone = "Recompletion"
        return [
            reading(
                "At 1,500 m and deeper, there were {0} recompletion approvals in 2025.",
                "value",
                0,
                (zone, 2025, deep),
            ),
            reading(
                "Under 100 m, the five year average for recompletion approvals fell "
                "from {0} per year in 2009 to {1} in 2025.",
                "moving_average",
                0,
                (zone, 2009, shallow),
                (zone, 2025, shallow),
            ),
            reading(
                "At 1,500 m and deeper, the five year average for recompletion "
                "approvals reached {0} per year in 2019 and {1} in 2025.",
                "moving_average",
                0,
                (zone, 2019, deep),
                (zone, 2025, deep),
            ),
        ]
    if stem == "03_approvals_per_well":
        return [
            reading(
                "In 2025, approvals per January well were {0} under 100 m and {1} at "
                "1,500 m and deeper.",
                "value",
                3,
                ("", 2025, shallow),
                ("", 2025, deep),
            ),
            reading(
                "Under 100 m, the five year average fell from {0} approvals per "
                "January well in 2009 to {1} in 2025.",
                "moving_average",
                3,
                ("", 2009, shallow),
                ("", 2025, shallow),
            ),
            reading(
                "At 1,500 m and deeper, the five year average rose from {0} approvals "
                "per January well in 2009 to {1} in 2025.",
                "moving_average",
                3,
                ("", 2009, deep),
                ("", 2025, deep),
            ),
        ]
    exploratory, development = "Exploratory wells", "Development wells"
    return [
        reading(
            "At 1,500 m and deeper, {0}% of exploratory and {1}% of development wells "
            "first drilled in 2025 had an initial approval.",
            "value",
            0,
            (exploratory, 2025, deep),
            (development, 2025, deep),
        ),
        reading(
            "At 1,500 m and deeper, the five year average exploratory approval share "
            "rose from {0}% in 2009 to {1}% in 2025.",
            "moving_average",
            0,
            (exploratory, 2009, deep),
            (exploratory, 2025, deep),
        ),
        reading(
            "In the partial 2026 drilling cohort at 1,500 m and deeper, {0}% of "
            "exploratory and {1}% of development wells had an initial approval.",
            "value",
            0,
            (exploratory, 2026, deep),
            (development, 2026, deep),
        ),
    ]


def join_labels(labels):
    if len(labels) == 1:
        return labels[0]
    return f"{', '.join(labels[:-1])} and {labels[-1]}"


def add_scale_notes(figures):
    by_measure = {}
    for figure in figures:
        if "measure" in figure:
            by_measure.setdefault(figure["measure"], []).append(figure)
    for group in by_measure.values():
        by_scale = {}
        for figure in group:
            scale = figure["y_scale"]
            by_scale.setdefault((scale["max"], scale["step"]), []).append(figure)
        if len(by_scale) == 1:
            continue
        labels = {}
        for axis, members in by_scale.items():
            numbers = [member["figure_number"] for member in members]
            noun = "Figure" if len(numbers) == 1 else "Figures"
            labels[axis] = f"{axis[0]:,g} in {noun} {join_labels(numbers)}"
        for axis, members in by_scale.items():
            own = labels[axis] if len(members) > 1 else f"{axis[0]:,g}"
            others = join_labels(
                [label for key, label in labels.items() if key != axis]
            )
            for member in members:
                member["scale_note"] = (
                    f"Note the scale: y maximum {own}, against {others}."
                )


def yearly_figures(out):
    figures = []
    split_groups = {
        "02_recompletion_by_period": ["Recompletion"],
        "03_perforation_flags": ["Modify Perforations", "Reperforation"],
    }
    # Figures 2 and 3 read the same CSV but contribute separate plotted peaks.
    recompletions = table(out, "02_recompletion_by_period")
    permit_rows = {
        "01_approvals_by_period": table(out, "01_approvals_by_period"),
        **{
            stem: [row for row in recompletions if row["group"] in groups]
            for stem, groups in split_groups.items()
        },
    }
    permit_scales = shared_depth_y_scales(permit_rows)
    for number, stem, title, question, ylabel, xlabel, note in FIGURES:
        groups = split_groups.get(stem)
        source = "02_recompletion_by_period" if groups else stem
        rows = permit_rows[stem] if stem in permit_rows else table(out, source)
        if stem in permit_scales:
            scale, shared = permit_scales[stem], "measure:approvals_per_year"
        else:
            scale, shared = depth_y_scale(rows), "panels"
        chart = render_svg(
            rows, title=title, ylabel=ylabel, xlabel=xlabel, note=note, y_scale=scale
        )
        (out / f"{stem}.svg").write_text(chart, encoding="utf-8", newline="\n")
        figures.append(
            dict(
                figure_number=number,
                svg=f"{stem}.svg",
                csv=f"{source}.csv",
                role="appendix" if stem == "03_approvals_per_well" else "main",
                panel_by="depth_band",
                layout="4x1_shared_x",
                **({"measure": "approvals_per_year"} if stem in permit_rows else {}),
                y_scale=dict(max=scale[-1], step=scale[1] - scale[0], shared=shared),
                **({"groups": groups} if groups else {}),
                question=question,
                note=note,
                x_unit="year",
                trend="moving_average_5y_trailing",
                view="yearly",
                bullets=figure_findings(stem, rows),
            )
        )
    add_scale_notes(figures)
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
    yearly_figures(Path(out))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "output")
    main(parser.parse_args().out)
