"""Render the two well life-cycle figures (PNG/SVG) from the derived CSVs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from plot_charts import COLORS, finish
from report_text import long_date

ROOT = Path(__file__).resolve().parent
# Two series from the article's ordered blues; hatching is the second cue.
DARK, LIGHT = COLORS[2], COLORS[0]
CHART_STAGES = [
    ("drilling", "Drilling (original hole)"),
    ("sidetrack or bypass", "Sidetrack or bypass"),
    ("light intervention", "Light intervention"),
    ("heavy intervention", "Heavy intervention"),
    (
        "intervention, light or heavy not established",
        "Intervention, unit not classified",
    ),
    ("temporary abandonment", "Temporary abandonment"),
    ("permanent abandonment", "Permanent abandonment"),
]


def style():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.hashsalt": "gom-interventions-life-cycle",
        }
    )


def life_figure(out, date):
    hist = pd.read_csv(out / "life_cycle_life_histogram.csv")
    life = pd.read_csv(out / "life_cycle_life_years.csv").set_index(["group", "status"])
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.4), sharey=False)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.80, bottom=0.27, wspace=0.22)
    bins = sorted(hist.bin_start_years.unique())
    x = np.arange(len(bins))
    for ax, kind in zip(axes, ["development", "exploration"]):
        bottom = np.zeros(len(bins))
        for status, color, hatch in [
            ("permanently abandoned", DARK, ""),
            ("standing", LIGHT, "//"),
        ]:
            vals = (
                hist[hist.well_type.eq(kind) & hist.status.eq(status)]
                .set_index("bin_start_years")
                .wells.reindex(bins, fill_value=0)
                .to_numpy()
            )
            ax.bar(
                x,
                vals,
                bottom=bottom,
                width=0.86,
                color=color,
                hatch=hatch,
                edgecolor="white",
                linewidth=0.6,
            )
            bottom += vals
        med = life.loc[(f"{kind} wells", "permanently abandoned"), "median_years"]
        n = int(
            life.loc[
                [(f"{kind} wells", s) for s in ["permanently abandoned", "standing"]],
                "wells",
            ].sum()
        )
        ax.set_title(f"{kind.capitalize()} wells ({n:,})", loc="left", fontsize=13)
        ax.text(
            0.98,
            0.95,
            f"Median life when abandoned:\n{med:.1f} years",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=10,
            color="#333333",
        )
        ax.set_xticks(x[::2], [str(b) for b in bins[::2]])
        ax.set_xlabel("Years from first spud (5-year bins, lower edge)")
        ax.set_ylim(bottom=0)
        ax.grid(axis="y", alpha=0.2)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Wells (count)")
    fig.suptitle(
        "How long Gulf of Mexico wells last", x=0.07, ha="left", y=0.97, fontsize=16
    )
    fig.legend(
        handles=[
            Patch(
                facecolor=DARK,
                label="Permanently abandoned: life from first spud to abandonment",
            ),
            Patch(
                facecolor=LIGHT,
                hatch="//",
                edgecolor="white",
                label=f"Still standing: age on {long_date(date)}",
            ),
        ],
        ncol=2,
        loc="upper center",
        bbox_to_anchor=(0.52, 0.91),
        frameon=False,
        fontsize=10,
    )
    finish(
        fig,
        out,
        "05_well_life",
        date,
        "One well is one API10; life runs from the first non-cancelled spud of any bore. Development and exploration follow\n"
        "the regulator's well type on the original hole. Abandonment date: every non-superseded bore is PA (the standing-well stock rule).",
    )


def stages_figure(out, date, first, last):
    reach = pd.read_csv(out / "life_cycle_stage_reach.csv")
    ages = pd.read_csv(out / "life_cycle_event_ages.csv")
    fig, (left, right) = plt.subplots(
        1, 2, figsize=(12, 7.2), sharey=True, gridspec_kw={"width_ratios": [1, 1]}
    )
    fig.subplots_adjust(left=0.24, right=0.98, top=0.80, bottom=0.22, wspace=0.08)
    y = np.arange(len(CHART_STAGES))
    series = [("development", DARK, "", -0.19), ("exploration", LIGHT, "//", 0.19)]
    for kind, color, hatch, dy in series:
        group = f"{kind} wells first drilled {first}-{last}"
        r = reach[reach.group.eq(group)].set_index("stage")
        vals = [r.loc[s, "share_percent"] for s, _ in CHART_STAGES]
        left.barh(
            y + dy,
            vals,
            height=0.36,
            color=color,
            hatch=hatch,
            edgecolor="white",
            linewidth=0.6,
        )
        for yi, v in zip(y + dy, vals):
            left.text(
                v + 1.5, yi, f"{v:.0f}%", va="center", fontsize=9, color="#333333"
            )
        a = ages[ages.well_type.eq(kind)].set_index("stage")
        for yi, (stage, _) in zip(y + dy, CHART_STAGES):
            if stage == "drilling":
                right.plot(
                    [0], [yi], "o", color=color, markeredgecolor="#333333", markersize=7
                )
                continue
            q1, med, q3 = a.loc[stage, ["q25_years", "median_years", "q75_years"]]
            right.plot(
                [q1, q3], [yi, yi], color=color, linewidth=4, solid_capstyle="round"
            )
            right.plot(
                [med], [yi], "o", color=color, markeredgecolor="#333333", markersize=7
            )
            right.text(
                q3 + 0.8, yi, f"{med:.1f}", va="center", fontsize=9, color="#333333"
            )
    left.set_yticks(y, [label for _, label in CHART_STAGES])
    left.invert_yaxis()
    left.set_xlim(0, 115)
    left.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    left.set_xlabel(
        f"Share of wells first drilled {first}-{last}\nwith at least one such event"
    )
    left.set_title("How many wells reach each stage", loc="left", fontsize=13)
    right.set_xlim(left=0)
    right.set_xlabel(
        f"Age of the well at the event, years\n(median and middle half, events {first}-{long_date(date)[-4:]})"
    )
    right.set_title("When it happens in the well's life", loc="left", fontsize=13)
    for ax in (left, right):
        ax.grid(axis="x", alpha=0.2)
        ax.set_axisbelow(True)
    n = {
        k: int(
            reach.loc[
                reach.group.eq(f"{k} wells first drilled {first}-{last}"), "wells"
            ].iloc[0]
        )
        for k in ["development", "exploration"]
    }
    fig.suptitle(
        "The life of a Gulf of Mexico well, stage by stage",
        x=0.07,
        ha="left",
        y=0.97,
        fontsize=16,
    )
    fig.legend(
        handles=[
            Patch(
                facecolor=DARK,
                label=f"Development wells ({n['development']:,} first drilled {first}-{last})",
            ),
            Patch(
                facecolor=LIGHT,
                hatch="//",
                edgecolor="white",
                label=f"Exploration wells ({n['exploration']:,} first drilled {first}-{last})",
            ),
        ],
        ncol=2,
        loc="upper center",
        bbox_to_anchor=(0.55, 0.91),
        frameon=False,
        fontsize=10,
    )
    finish(
        fig,
        out,
        "06_well_life_stages",
        date,
        "Drilling: bores with a spud date; other stages: approved permits to modify. Light: wireline, coiled tubing, vessel, liftboat or non-rig unit;\n"
        "heavy: platform rig, hydraulic workover or snubbing, jack-up, drillship or semi. Right panel: every event in the window; older wells add later events only.",
    )


def plot(out):
    style()
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    life = json.loads((out / "life_cycle_summary.json").read_text(encoding="utf-8"))
    if life["file_date"] != summary["file_date"]:
        raise ValueError("life-cycle tables come from a different snapshot")
    date = summary["file_date"]
    first, last = int(summary["first_full_year"]), int(summary["last_full_year"])
    life_figure(out, date)
    stages_figure(out, date, first, last)
    print(json.dumps({"charts": 2, "formats": ["png", "svg"]}))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=ROOT / "output")
    plot(p.parse_args().out)
