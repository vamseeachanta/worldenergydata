"""Render three publication-size PNG/SVG figures from committed CSVs."""

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

BANDS = [
    "under 100 m",
    "100 to 500 m",
    "500 to 1500 m",
    "1500 m and deeper",
    "no depth",
]
COLORS = ["#d9e6f2", "#91b8d5", "#397da8", "#123b56", "#888888"]
MARKERS = ["o", "s", "^", "D", "x"]
STYLES = ["-", "--", "-.", ":", "--"]
HATCHES = ["", "//", "..", "xx", "\\\\"]


def finish(fig, out, stem, date, extra=""):
    fig.text(0.07, 0.075, extra, fontsize=10, color="#333333")
    fig.text(
        0.07,
        0.035,
        f"Source: BSEE Data Center raw data, files of {date}; cost basis: see cost_basis.yml",
        fontsize=9,
    )
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


def plot(out):
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.hashsalt": "gom-interventions-v1",
        }
    )
    summary = json.loads((out / "summary.json").read_text())
    date, last = summary["file_date"], summary["last_full_year"]
    rates = pd.read_csv(out / "rates.csv")
    years = sorted(rates.year.unique())
    legend = [
        Line2D([], [], color=c, marker=m, linestyle=s, label=b)
        for b, c, m, s in zip(BANDS, COLORS, MARKERS, STYLES)
    ]
    fig, axes = plt.subplots(2, 1, figsize=(12, 9), sharex=True)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.18, hspace=0.28)
    for ax, family in zip(axes, ["well work", "abandonment"]):
        frame = (
            rates[rates.family.eq(family)]
            .pivot(index="year", columns="band", values="permits")
            .reindex(years)
        )
        bottom = np.zeros(len(years))
        for band, color, hatch in zip(BANDS, COLORS, HATCHES):
            vals = frame[band].to_numpy()
            ax.bar(
                years,
                vals,
                bottom=bottom,
                color=color,
                edgecolor="#454545",
                linewidth=0.4,
                hatch=hatch,
                label=band,
            )
            bottom += vals
        ax.axvspan(last + 0.5, last + 1.5, color="#cccccc", alpha=0.3)
        ax.set_title(f"APM approvals: {family}", loc="left", fontsize=13)
        ax.set_ylabel("Approved permits (count)")
        ax.grid(axis="y", alpha=0.2)
        ax.set_axisbelow(True)
        ax.set_xlim(min(years) - 0.7, max(years) + 0.6)
    fig.legend(
        *axes[0].get_legend_handles_labels(),
        ncol=5,
        loc="upper center",
        bbox_to_anchor=(0.51, 0.98),
        fontsize=9,
        frameon=False,
    )
    axes[1].set_xticks(
        years[::2] + ([years[-1]] if years[-1] not in years[::2] else [])
    )
    axes[1].set_xticklabels(
        [f"{y}\npartial" if y > last else str(y) for y in axes[1].get_xticks()]
    )
    axes[1].set_xlabel("Approval year")
    finish(
        fig,
        out,
        "01_approved_interventions",
        date,
        "Initial completions and new-hole preparation excluded. Unspecified abandonment retained. 2026 through 12 November.",
    )

    fig, axes = plt.subplots(2, 1, figsize=(12, 9), sharex=True)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.18, hspace=0.30)
    for ax, family in zip(axes, ["well work", "abandonment"]):
        for band, color, marker, style in zip(BANDS, COLORS, MARKERS, STYLES):
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
            if partial.per_100_standing_wells.notna().any():
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
            f"APM approvals per standing well: {family}", loc="left", fontsize=13
        )
        ax.set_ylabel("Permits / 100 standing wells")
        ax.grid(axis="y", alpha=0.25)
        ax.set_xlim(min(years) - 0.5, max(years) + 0.6)
    fig.legend(
        handles=legend,
        ncol=5,
        loc="upper center",
        bbox_to_anchor=(0.51, 0.97),
        frameon=False,
        fontsize=9,
    )
    axes[1].set_xticks(
        years[::2] + ([years[-1]] if years[-1] not in years[::2] else [])
    )
    axes[1].set_xticklabels(
        [
            f"{int(y)}\npartial" if y > last else str(int(y))
            for y in axes[1].get_xticks()
        ]
    )
    axes[1].set_xlabel("Approval year")
    finish(
        fig,
        out,
        "02_rates_per_standing_well",
        date,
        "Original-hole year-end inventory proxy; 2026 uses the file date and is not annualised. No-depth rate is missing.",
    )

    costs = pd.read_csv(out / "cost_table.csv")
    fig, axes = plt.subplots(1, 2, figsize=(12, 6), sharey=True)
    fig.subplots_adjust(left=0.18, right=0.98, top=0.80, bottom=0.24, wspace=0.32)
    for ax, kind in zip(axes, ["well work", "permanent abandonment"]):
        f = costs[costs.event.eq(kind)].set_index("band").reindex(BANDS[:-1])
        for y, (band, r) in enumerate(f.iterrows()):
            ax.plot(
                [r.low_usd / 1e6, r.high_usd / 1e6],
                [y, y],
                color=COLORS[y],
                linewidth=7,
                solid_capstyle="butt",
            )
            ax.plot(r.base_usd / 1e6, y, marker="D", color="black", markersize=6)
        ax.set_title(kind.capitalize(), fontsize=13)
        ax.set_xlabel("Cost per event\n(million 2015 USD; log scale)")
        ax.set_yticks(range(4), BANDS[:-1])
        ax.grid(axis="x", alpha=0.25)
        ax.set_xscale("log")
        ax.set_xlim(0.2, 25)
        ax.set_xticks(
            [0.2, 0.5, 1, 2, 5, 10, 20], ["0.2", "0.5", "1", "2", "5", "10", "20"]
        )
    axes[0].invert_yaxis()
    axes[0].set_ylabel("Water-depth band")
    fig.suptitle("Indicative heavy-work cost scenarios", x=0.18, ha="left", fontsize=15)
    fig.legend(
        handles=[
            Line2D([], [], color="#397da8", lw=6, label="Low–high scenario"),
            Line2D(
                [],
                [],
                color="black",
                marker="D",
                linestyle="None",
                label="Base scenario",
            ),
        ],
        loc="upper right",
        bbox_to_anchor=(0.98, 0.96),
        frameon=False,
    )
    finish(
        fig,
        out,
        "03_cost_per_event",
        date,
        "Platform casing-jack proxy / deepwater MODU. Unescalated source-year USD; floating-unit mobilisation excluded.",
    )
    print(json.dumps({"charts": 3, "formats": ["png", "svg"], "png_width_px": 2160}))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    plot(p.parse_args().out)
