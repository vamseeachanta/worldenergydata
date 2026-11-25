"""Article figures drawn exclusively from the five published figure tables."""

from pathlib import Path
from xml.etree import ElementTree

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import (
    MaxNLocator,
    MultipleLocator,
    PercentFormatter,
    StrMethodFormatter,
)

COLORS = {
    "<100 m": "#6588a6",
    "100–<500 m": "#427298",
    "500–<1,500 m": "#245476",
    "≥1,500 m": "#102e46",
}
BAND_LABELS = {
    "<100 m": "Under 100 m",
    "100–<500 m": "100 to 500 m",
    "500–<1,500 m": "500 to 1,500 m",
    "≥1,500 m": "1,500 m and deeper",
}
TEXT = "#333333"
RULE = "#c9c3b8"
GRID = "#efefef"
STYLE = {
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "text.color": TEXT,
    "axes.labelcolor": TEXT,
    "axes.edgecolor": RULE,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,
    "axes.facecolor": "white",
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
    "svg.fonttype": "none",
    "svg.hashsalt": "bsee-ogora-production",
}


def legend(fig, *, stacked=False):
    handles = [
        Patch(facecolor=color) if stacked else Line2D([], [], color=color, lw=2.8)
        for color in COLORS.values()
    ]
    fig.legend(
        handles=handles,
        labels=[BAND_LABELS[band] for band in COLORS],
        loc="upper center",
        bbox_to_anchor=(0.53, 1.0),
        ncol=4,
        frameon=False,
        handlelength=2.0,
        columnspacing=2.4,
    )


def axis_style(ax):
    ax.set_axisbelow(True)
    ax.grid(visible=True, axis="y", color=GRID)
    ax.tick_params(axis="both", which="both", length=0, pad=6)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5))


def label_panel(ax, text):
    ax.set_title(text, loc="left", fontsize=11, fontweight="bold", pad=7)


def caption(fig, title, note):
    lines = note.count("\n") + 1
    title_y = 0.021 + (lines * 0.17 + 0.085) / fig.get_figheight()
    fig.text(0.075, title_y, title, fontsize=13, fontweight="bold", va="bottom")
    fig.text(0.075, 0.021, note, fontsize=9, color=TEXT, va="bottom", linespacing=1.35)


def check_svg(path):
    raw = path.read_bytes()
    root = ElementTree.fromstring(raw)
    if b"clip-path" in raw:
        raise ValueError(f"{path} contains a prohibited clip-path")
    forbidden = {"pattern", "clipPath", "filter", "mask"}
    for elem in root.iter():
        tag = elem.tag.split("}")[-1]
        if tag in forbidden:
            raise ValueError(f"{path} contains prohibited SVG markup on {tag}")
    if not any(e.tag.endswith("}text") for e in root.iter()):
        raise ValueError(f"{path} contains no selectable chart text")


def save(fig, charts, name, title):
    # All lines and markers lie inside explicit axes bounds. Disable Matplotlib's
    # default clipping when rendering so that SVGs require no clipPath resources.
    for artist in fig.findobj():
        artist.set_clip_on(False)
    svg = charts / f"{name}.svg"
    png = charts / f"{name}.png"
    try:
        with svg.open("w", encoding="utf-8", newline="\n") as stream:
            fig.savefig(stream, format="svg", metadata={"Date": None, "Title": title})
        check_svg(svg)
        fig.savefig(png, dpi=170, metadata={"Title": title})
    finally:
        plt.close(fig)
    return [svg, png]


def monthly_figure(monthly, end_label):
    fig, axes = plt.subplots(2, 1, sharex=True, figsize=(10.4, 6.8))
    fig.subplots_adjust(left=0.085, right=0.975, bottom=0.185, top=0.88, hspace=0.39)
    legend(fig, stacked=True)
    data = monthly.loc[monthly.band.isin(COLORS)].copy()
    data["month"] = pd.to_datetime(data.month)
    for ax, field, units in zip(
        axes,
        ["oil_bbl", "gas_mcf"],
        ["Oil production (million barrels per month)", "Gas production (billion cubic feet per month)"],
    ):
        by_band = data.pivot(index="month", columns="band", values=field).sort_index()
        values = by_band.loc[:, list(COLORS)] / 1_000_000
        if values.isna().any().any() or values.lt(0).any().any():
            raise ValueError(f"Missing or negative band totals cannot be shown in the {field} stack")
        ax.stackplot(by_band.index, *values.to_numpy().T, colors=list(COLORS.values()), linewidth=0)
        ax.set_xlim(by_band.index.min(), by_band.index.max())
        ax.set_ylim(0, values.sum(axis=1).max() * 1.045)
        axis_style(ax)
        label_panel(ax, units)
    axes[-1].xaxis.set_major_locator(mdates.YearLocator(base=3))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    title = "Monthly oil and gas production by water depth"
    caption(
        fig,
        title,
        f"Federal Gulf of America wells with assigned depth • BSEE OGOR-A and borehole records • January 2005 through {end_label}.\n"
        "Latest-month volumes reflect reports available at extraction.",
    )
    return fig, title


def annual_figure(annual, last_date):
    fig, axes = plt.subplots(2, 1, sharex=True, figsize=(10.4, 6.8))
    fig.subplots_adjust(left=0.095, right=0.975, bottom=0.175, top=0.875, hspace=0.38)
    legend(fig)
    latest_year = last_date.year
    partial = last_date.month < 12
    for band, color in COLORS.items():
        ax = axes[0] if band == "<100 m" else axes[1]
        rows = annual.loc[annual.band == band].sort_values("year")
        complete = rows.loc[rows.year < latest_year] if partial else rows
        ax.plot(complete.year, complete.producing_wells, color=color, lw=2.4)
        if partial:
            tail = rows.tail(2)
            ax.plot(tail.year, tail.producing_wells, color=color, lw=2, linestyle=":")
            ax.plot(
                rows.year.iloc[-1],
                rows.producing_wells.iloc[-1],
                "o",
                ms=6,
                color=color,
                markerfacecolor="white",
            )
    first_year = int(annual.year.min())
    ticks = sorted(set(range(first_year, latest_year, 3)) | {latest_year})
    for ax, heading in zip(axes, ["Under 100 m (wells)", "100 m and deeper (wells, expanded scale)"]):
        axis_style(ax)
        ax.set_ylim(bottom=0)
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
        ax.set_xlim(first_year - 0.18, latest_year + 0.18)
        ax.set_xticks(ticks)
        label_panel(ax, heading)
    axes[-1].tick_params(axis="x", pad=10)
    title = "Producing wells by calendar year and water depth"
    note = "A well contributes once per year when oil or gas production is positive."
    if partial:
        note += f" Open points show {latest_year} through {last_date:%B}."
    caption(fig, title, note)
    return fig, title


def lag_figure(table):
    data = table.loc[table.population.eq("ordered")].set_index("band").loc[list(COLORS)]
    fig, (ax, labels) = plt.subplots(1, 2, figsize=(10.4, 5.0), gridspec_kw={"width_ratios": [3, 1.45]})
    fig.subplots_adjust(left=0.16, right=0.975, bottom=0.24, top=0.865, wspace=0.12)
    axis_style(ax)
    ax.grid(False, axis="y")
    ax.grid(visible=True, axis="x", color=GRID)
    x_max = data.p75_months.max()
    ax.set_xlim(-0.025 * max(x_max, 1), max(x_max, 1) * 1.05)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=7))
    for y, (band, rec) in enumerate(data.iterrows()):
        color = COLORS[band]
        if rec.wells:
            lo, mid, hi = rec[["p25_months", "median_months", "p75_months"]]
            ax.hlines(y, lo, hi, color=color, lw=4)
            ax.plot([lo, hi], [y, y], linestyle="", marker="|", color=color, ms=12)
            ax.plot(mid, y, "o", ms=9, color=color, markeredgecolor="white", markeredgewidth=1.3)
            labels.text(0.0, y, f"{mid:g} ({lo:g} to {hi:g})", va="center", fontsize=11)
        labels.text(0.96, y, f"{int(rec.wells):,}", va="center", ha="right", fontsize=11)
    for panel in [ax, labels]:
        panel.set_ylim(3.55, -0.58)
    labels.set_xlim(0, 1)
    labels.set_axis_off()
    label_panel(ax, "Months to first production")
    labels.text(0, 1.05, "Median (Q1 to Q3)", weight="bold", transform=labels.transAxes)
    labels.text(0.96, 1.05, "Wells", ha="right", weight="bold", transform=labels.transAxes)
    ax.set_yticks(range(4), [BAND_LABELS[band] for band in COLORS])
    title = "Time from completion to the first producing month"
    caption(
        fig,
        title,
        "First completion in 2005 to 2025. The interval spans the middle half of wells whose first producing month was at or after completion.",
    )
    return fig, title


def supported_line(ax, x, y, count, color):
    # Hollow symbols identify every finite point supported by fewer than ten wells.
    ax.plot(x, y, color=color, lw=2, solid_capstyle="round")
    sparse = (count > 0) & (count < 10) & y.notna()
    ax.plot(
        x[sparse],
        y[sparse],
        linestyle="",
        marker="o",
        markersize=3.6,
        color=color,
        markerfacecolor="white",
        markeredgewidth=0.9,
    )


def decline_figure(table):
    data = table.loc[table.band.isin(COLORS)]
    groups = list(data.completion_type.unique())
    groups = [t for t in ["All", "Subsea", "No subsea flag (NO)", "Unknown"] if t in groups] + sorted(
        set(groups).difference({"All", "Subsea", "No subsea flag (NO)", "Unknown"})
    )
    cols = 2 if len(groups) > 1 else 1
    rows = (len(groups) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, squeeze=False, sharex=True, figsize=(10.4, 4.35 + 2.25 * rows))
    fig.subplots_adjust(left=0.083, bottom=0.19, top=0.87, right=0.97, wspace=0.22, hspace=0.46)
    legend(fig)
    # The unknown-type curve can exceed the range for wells with a recorded type.
    # Keep the known types and pooled data comparable; widen only where needed.
    known_peak = max(1, data.loc[data.completion_type.ne("Unknown"), "median_relative_rate"].max())
    wider_unknown = data.loc[data.completion_type.eq("Unknown"), "median_relative_rate"].max() > known_peak
    for ax, group in zip(axes.flat, groups):
        selected = data.loc[data.completion_type == group]
        for band, color in COLORS.items():
            s = selected.loc[selected.band == band].sort_values("age_month")
            supported_line(ax, s.age_month, s.median_relative_rate, s.wells, color)
        axis_style(ax)
        group_labels = {
            "All": "All completion types",
            "Subsea": "Subsea completion recorded",
            "No subsea flag (NO)": "Subsea flag recorded as NO",
            "Unknown": "Unknown completion type" + (" (wider scale)" if wider_unknown else ""),
        }
        label_panel(ax, group_labels.get(group, group))
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
        ax.set_xticks([1, 12, 24, 36, 48, 60])
        ax.set_xlim(0, 61)
        peak = max(known_peak, selected.median_relative_rate.max())
        ax.set_ylim(0, peak * 1.05)
        if peak <= 1.5:
            ax.yaxis.set_major_locator(MultipleLocator(0.25))
        ax.tick_params(labelbottom=True)
    for ax in list(axes.flat)[len(groups) :]:
        ax.set_axis_off()
    fig.text(0.526, 0.132, "Months since first observed oil or gas production", ha="center")
    title = "Median oil rate as a share of each well’s early peak"
    caption(
        fig,
        title,
        "First observed production in 2005 to 2020. Oil per producing day is divided by the best rate in calendar months 1 to 3.\n"
        "Open markers indicate fewer than 10 contributing wells at that age and depth.",
    )
    return fig, title


def intervention_figure(table):
    measures = [
        ("Post-completion WAR", "First post-completion WAR"),
        ("Intervention approval", "First intervention approval"),
    ]
    fig, axes = plt.subplots(1, 2, sharex=True, sharey=True, figsize=(10.4, 5.6))
    fig.subplots_adjust(left=0.074, right=0.97, bottom=0.28, top=0.83, wspace=0.17)
    legend(fig)
    for ax, (measure, title) in zip(axes, measures):
        data = table.loc[table.measure.eq(measure) & table.band.isin(COLORS)]
        if data.empty:
            raise ValueError(f"Missing intervention measure {measure}")
        for band, color in COLORS.items():
            s = data.loc[data.band == band].sort_values("age_year")
            supported_line(ax, s.age_year, s.share, s.eligible_wells, color)
        label_panel(ax, title)
        axis_style(ax)
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
        ax.xaxis.set_major_locator(MaxNLocator(nbins=6, integer=True))
        ax.set_xlim(data.age_year.min() - 0.22, data.age_year.max() + 0.22)
        ax.set_ylim(0, 1.02)
    fig.text(0.52, 0.178, "Years since first observed production", ha="center")
    title = "Producing wells with a recorded event by each anniversary"
    caption(
        fig,
        title,
        "WARs record work after completion. Approvals cover classified well work. Age zero includes earlier qualifying events.\n"
        "Each age uses wells with sufficient follow-up. Open markers indicate fewer than 10 eligible wells.",
    )
    return fig, title


def render_charts(output: Path, charts: Path):
    """Write and validate one SVG and one PNG for each figure table."""
    charts.mkdir(parents=True, exist_ok=True)
    monthly = pd.read_csv(output / "monthly_production.csv")
    last_date = pd.to_datetime(monthly.month).max()
    outputs = []
    with plt.rc_context(STYLE):
        for name, build in [
            ("monthly_production", lambda: monthly_figure(monthly, last_date.strftime("%B %Y"))),
            ("annual_wells", lambda: annual_figure(pd.read_csv(output / "annual_wells.csv"), last_date)),
            ("completion_lag", lambda: lag_figure(pd.read_csv(output / "completion_lag.csv"))),
            (
                "decline",
                lambda: decline_figure(
                    pd.read_csv(output / "decline.csv", keep_default_na=False, na_values=[""])
                ),
            ),
            ("interventions", lambda: intervention_figure(pd.read_csv(output / "interventions.csv"))),
        ]:
            fig, title = build()
            outputs.extend(save(fig, charts, name, title))
    return outputs
