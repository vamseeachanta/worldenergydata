"""Render four publication-size PNG/SVG figures from derived CSVs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FormatStrFormatter
from report_text import (
    check_selection,
    coding_caption,
    long_date,
    permanent_caption,
    unit_panel_total,
)

BANDS = [
    "under 100 m",
    "100 to 500 m",
    "500 to 1500 m",
    "1500 m and deeper",
    "no depth",
]
# Ordered light-to-dark blues; even the lightest exceeds 3:1 on white.
COLORS = ["#6588a6", "#427298", "#245476", "#102e46", "#777777"]
MARKERS = ["o", "s", "^", "D", "x"]
STYLES = ["-", "--", "-.", ":", "--"]
BAND_LABELS = {
    "500 to 1500 m": "500 to 1,500 m",
    "1500 m and deeper": "1,500 m and deeper",
}
HATCHES = ["", "//", "..", "xx", "\\\\"]
# Inclusion basis per pricing method, shown beside each cost row.
COST_BASIS = {
    "spread scenario": "spread scenario; no allowances",
    "published total": "published total; includes allowances",
    "not priced": "",
}
COST_SOURCES = (
    "Sources: BSEE TAP-738, 2015; BOEM EIS 2016-018, 2016;\n"
    "BOEM MAG-PLAN Alaska update, 2012; BSEE Pacific cost update vol. 2, 2015."
)


def million(value):
    if pd.isna(value):
        return "not priced"
    x = value / 1e6
    return f"{x:.{max(0, 1-int(np.floor(np.log10(abs(x)))))}f}" if x else "0"


def finish(fig, out, stem, date, extra="", cost=False, eor=False):
    fig.text(0.07, 0.15 if cost else 0.10, extra, fontsize=9, color="#333333", va="top")
    source = (
        COST_SOURCES
        if cost
        else f"Source: BSEE BoreholeRawData.zip, eWellAPMRawData.zip{' and eWellEORRawData.zip' if eor else ''}; {date}."
    )
    fig.text(0.07, 0.025, source, fontsize=9, va="bottom")
    fig.savefig(out / (stem + ".png"), dpi=180, facecolor="white")
    fig.savefig(out / (stem + ".svg"), metadata={"Date": None}, facecolor="white")
    svg = out / (stem + ".svg")
    svg.write_text(
        "\n".join(
            line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    plt.close(fig)


def year_axis(axes, years, last):
    ticks = years[::2] + ([years[-1]] if years[-1] not in years[::2] else [])
    axes[-1].set_xticks(ticks)
    axes[-1].set_xticklabels([f"{y}\npartial" if y > last else str(y) for y in ticks])
    axes[-1].set_xlabel("Approval year")


def plot(out):
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.hashsalt": "gom-interventions-v2",
        }
    )
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    date, first = summary["file_date"], int(summary["first_full_year"])
    all_units = pd.read_csv(out / "unit_type_shares.csv")
    # Captions are derived from these tables; reject a mixed-year output set.
    last = check_selection(summary, {"unit_type_shares.csv": all_units.period})
    partial_year = int(summary["partial_year"])
    primary = pd.read_csv(out / "primary_code_by_year.csv")
    counts = pd.read_csv(out / "counts_by_year_band_group.csv")
    rates = pd.read_csv(out / "rates.csv")
    years = sorted(rates.year.unique())
    active = [b for b in BANDS if rates.loc[rates.band.eq(b), "permits"].sum() > 0]
    legend = [
        Line2D([], [], color=c, marker=m, linestyle=s, label=BAND_LABELS.get(b, b))
        for b, c, m, s in zip(BANDS, COLORS, MARKERS, STYLES)
        if b in active
    ]
    fig, axes = plt.subplots(2, 1, figsize=(12, 9), sharex=True)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.22, hspace=0.30)
    for ax, family in zip(axes, ["well work", "abandonment"]):
        frame = (
            rates[rates.family.eq(family)]
            .pivot(index="year", columns="band", values="permits")
            .reindex(years)
        )
        bottom = np.zeros(len(years))
        for band, color, hatch in zip(BANDS, COLORS, HATCHES):
            if band not in active:
                continue
            vals = frame[band].to_numpy()
            ax.bar(
                years,
                vals,
                bottom=bottom,
                color=color,
                edgecolor="#333333",
                linewidth=0.4,
                hatch=hatch,
                label=BAND_LABELS.get(band, band),
            )
            bottom += vals
        ax.axvspan(last + 0.5, last + 1.5, color="#cccccc", alpha=0.3)
        ax.set_title(f"Approved permits to modify: {family}", loc="left", fontsize=13)
        ax.set_ylabel("Approved permits (count)")
        ax.set_ylim(bottom=0)
        ax.grid(axis="y", alpha=0.2)
        ax.set_axisbelow(True)
        ax.set_xlim(min(years) - 0.7, max(years) + 0.6)
    fig.legend(
        *axes[0].get_legend_handles_labels(),
        ncol=len(active),
        loc="upper center",
        bbox_to_anchor=(0.51, 0.98),
        fontsize=9,
        frameon=False,
    )
    year_axis(axes, years, last)
    finish(
        fig,
        out,
        "01_approved_interventions",
        date,
        "Initial completions and new-hole preparation excluded; unspecified abandonment retained. "
        f"{partial_year} through {long_date(date, year=False)}.\n"
        + coding_caption(primary, first, last),
    )

    fig, axes = plt.subplots(2, 1, figsize=(12, 9), sharex=True)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.22, hspace=0.30)
    for ax, family in zip(axes, ["well work", "abandonment"]):
        for band, color, marker, style in zip(BANDS, COLORS, MARKERS, STYLES):
            if band not in active:
                continue
            f = rates[rates.family.eq(family) & rates.band.eq(band)].sort_values("year")
            full = f[f.year.le(last)]
            ax.plot(
                full.year,
                full.per_100_standing_wells,
                color=color,
                marker=marker,
                linestyle=style,
                markersize=4,
                markeredgecolor="#333333",
                markeredgewidth=0.5,
            )
            partial = f[f.year.gt(last)]
            ax.scatter(
                partial.year,
                partial.per_100_standing_wells,
                color=color,
                marker=marker,
                edgecolors="#333333",
                s=45,
            )
        ax.axvspan(last + 0.5, last + 1.5, color="#cccccc", alpha=0.3)
        ax.set_title(
            f"Approved permits to modify per 100 standing wells: {family}",
            loc="left",
            fontsize=13,
        )
        ax.set_ylabel("Permits / 100 standing wells")
        ax.yaxis.set_major_formatter(FormatStrFormatter("%.1f"))
        ax.set_ylim(bottom=0)
        ax.grid(axis="y", alpha=0.25)
        ax.set_xlim(min(years) - 0.5, max(years) + 0.6)
    fig.legend(
        handles=legend,
        ncol=len(active),
        loc="upper center",
        bbox_to_anchor=(0.51, 0.98),
        frameon=False,
        fontsize=9,
    )
    year_axis(axes, years, last)
    finish(
        fig,
        out,
        "02_rates_per_standing_well",
        date,
        f"Denominator: wells standing on 1 January, all non-cancelled bores per well; {partial_year} approvals are partial, not annualised.\n"
        "Approval intensity includes repeated permits; it is not the percentage of wells receiving work.",
    )

    costs = pd.read_csv(out / "cost_table.csv").set_index("scenario_id")
    order = [
        "platform_rigless_work",
        "platform_rigless_pa",
        "platform_casing_work",
        "platform_casing_pa",
        "deep_platform_work",
        "deep_platform_pa",
        "subsea_work",
        "subsea_pa",
        "subsea_pa_6000_9000ft",
    ]
    labels = [
        "Platform dry-tree / rigless: well work",
        "Platform dry-tree / rigless: permanent abandonment",
        "Platform dry-tree / casing jacks: well work",
        "Platform dry-tree / casing jacks: permanent abandonment",
        "Deepwater platform dry-tree: well work",
        "Deepwater platform dry-tree: permanent abandonment",
        "Subsea wet-tree / drillship or semi: well work",
        "Subsea wet-tree / drillship or semi: permanent abandonment\nstudy cases 3,000 ft (low/base); 6,000 ft (high)",
        "Subsea wet-tree / drillship or semi: permanent abandonment\nstudy cases 6,000 ft (low/base); 9,000 ft (high)",
    ]
    fig, ax = plt.subplots(figsize=(12, 9))
    fig.subplots_adjust(left=0.43, right=0.79, top=0.83, bottom=0.28)
    for y, key in enumerate(order):
        r = costs.loc[key]
        color = COLORS[1] if r.event == "well work" else COLORS[3]
        if pd.notna(r.low_usd):
            ax.plot(
                [r.low_usd / 1e6, r.high_usd / 1e6],
                [y, y],
                color=color,
                linewidth=6,
                solid_capstyle="butt",
            )
            ax.plot(r.base_usd / 1e6, y, marker="D", color="black", markersize=5)
        ax.text(
            1.04,
            y,
            (
                " / ".join(million(r[c]) for c in ["low_usd", "base_usd", "high_usd"])
                + "\n"
                + COST_BASIS[r.pricing_method]
                if pd.notna(r.low_usd)
                else "not priced"
            ),
            transform=ax.get_yaxis_transform(),
            va="center",
            fontsize=10 if pd.isna(r.low_usd) else 8.5,
        )
    ax.set_yticks(range(len(order)), labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xscale("log")
    ax.set_xlim(0.2, 25)
    ax.set_xticks(
        [0.2, 0.5, 1, 2, 5, 10, 20], ["0.20", "0.50", "1.0", "2.0", "5.0", "10", "20"]
    )
    ax.set_xlabel("USD million per well / event (2015; log scale)")
    ax.grid(axis="x", alpha=0.25)
    ax.text(
        1.04,
        1.05,
        "Low / base / high\nUSD million (2015); basis",
        transform=ax.transAxes,
        fontsize=10,
    )
    fig.suptitle(
        "Cost scenarios by well and access type", x=0.07, ha="left", fontsize=16, y=0.97
    )
    fig.text(
        0.07,
        0.90,
        "Rigless: source case 50-400 ft; casing jacks: above 400 ft. Deep platform: published cases at 1,700 / 3,000 / 5,000 ft water depth.\n"
        "Subsea wells have a wet tree on the seabed; depth alone does not select a spread.",
        fontsize=10,
    )
    finish(
        fig,
        out,
        "03_cost_per_event",
        date,
        "Well work: median 7 days / midpoint 10.5 days / two weeks 14 days; scenarios, not outcome quantiles.\n"
        + permanent_caption(counts, last)
        + "\nSubsea rig mobilisation excluded. Dry-tree conductor removal separate; "
        "spread rows exclude the source's allowances; published deep-platform totals include them.",
        cost=True,
    )

    units = all_units[all_units.period.astype(str).eq(str(last))]
    categories = [
        "wireline unit",
        "coiled tubing",
        "hydraulic workover / snubbing",
        "platform rig",
        "liftboat / jack-up",
        "intervention vessel",
        "drillship / semisubmersible",
        "non-rig operation (recorded)",
        "none named",
        "other",
    ]
    unit_colors = [
        "#376c9b",
        "#007c78",
        "#8c4b8e",
        "#9a5c1f",
        "#697725",
        "#aa4444",
        "#17364c",
        "#4d6570",
        "#777777",
        "#c9c3b8",
    ]
    active_units = [
        c
        for c in categories
        if units.loc[units.unit_category.eq(c), "approvals"].sum() > 0
    ]
    fig, axes = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
    fig.subplots_adjust(left=0.20, right=0.94, top=0.75, bottom=0.20, hspace=0.38)
    for ax, event in zip(axes, ["well work", "permanent abandonment"]):
        f = units[units.event.eq(event)]
        bands = [b for b in BANDS if f.loc[f.band.eq(b), "approvals"].sum() > 0]
        left = np.zeros(len(bands))
        for category, color in zip(categories, unit_colors):
            vals = (
                f[f.unit_category.eq(category)]
                .set_index("band")
                .reindex(bands)
                .share_percent.to_numpy()
            )
            ax.barh(
                bands,
                vals,
                left=left,
                color=color,
                edgecolor="white",
                linewidth=0.6,
                height=0.65,
            )
            for y, v in enumerate(vals):
                if v >= 7:
                    ax.text(
                        left[y] + v / 2,
                        y,
                        f"{v:.1f}%",
                        ha="center",
                        va="center",
                        color="#1f2328" if color == "#c9c3b8" else "white",
                        fontsize=9,
                    )
            left += vals
        for y, band in enumerate(bands):
            n = int(f[f.band.eq(band)].approvals.sum())
            ax.text(101, y, f"n={n:,}", va="center", fontsize=9)
        ax.set_yticks(range(len(bands)), [BAND_LABELS.get(b, b) for b in bands])
        ax.invert_yaxis()
        ax.set_title(event.capitalize(), loc="left", fontsize=13)
        ax.set_xlim(0, 100)
        ax.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
        ax.grid(axis="x", alpha=0.15)
        ax.set_axisbelow(True)
    axes[-1].set_xlabel("Share of approved permits (%)")
    fig.suptitle(
        f"Unit types named on approved permits to modify, {last}",
        x=0.07,
        ha="left",
        y=0.97,
        fontsize=16,
    )
    fig.legend(
        handles=[
            Patch(facecolor=c, label=k)
            for k, c in zip(categories, unit_colors)
            if k in active_units
        ],
        ncol=3,
        loc="upper center",
        bbox_to_anchor=(0.51, 0.92),
        frameon=False,
        fontsize=10,
    )
    finish(
        fig,
        out,
        "04_unit_types_by_depth",
        date,
        "Unit types follow the permit rig/unit lookup; they do not establish deployed equipment or access configuration.\n"
        f"Permanent-abandonment panel: {unit_panel_total(all_units, last):,} approvals; temporary and unspecified abandonment are excluded.",
    )
    print(json.dumps({"charts": 4, "formats": ["png", "svg"], "png_width_px": 2160}))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    plot(p.parse_args().out)
