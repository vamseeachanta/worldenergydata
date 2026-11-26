"""Render the Gulf well status, temporary-abandonment age and annual PA figures."""

import math
from pathlib import Path

import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.ticker import MaxNLocator
import pandas as pd


INK = "#333333"
GRID = "#efefef"
BAND_COLORS = ("#6588a6", "#427298", "#245476", "#102e46")
STATUS_COLORS = {
    "PA": "#245476", "TA": "#007c78", "COM": "#6588a6", "Other": "#c9c3b8",
}
DEPTH_LABELS = ("Under 100 m", "100 to 500 m", "500 to 1,500 m", "1,500 m and deeper")
NO_DEPTH_LABEL = "No reported depth"
ROW_Y = (0.60, 0.49, 0.38, 0.27)


def label(fig, x, y, value, size=12, *, bold=False, align="left"):
    fig.text(x, y, value, fontsize=size, color=INK, fontweight="bold" if bold else "normal",
             ha=align, va="center", clip_on=False, zorder=5)


def rect(fig, x, y, width, height, color, *, gid=None):
    fig.add_artist(Rectangle((x, y), width, height, transform=fig.transFigure,
                             facecolor=color, edgecolor="none", clip_on=False, zorder=2, gid=gid))


def line(fig, x, y, color, width=1, **kwargs):
    fig.add_artist(Line2D(x, y, transform=fig.transFigure, clip_on=False, color=color,
                          linewidth=width, solid_capstyle="round", **kwargs))


def figure(title, subtitle):
    fig = Figure(figsize=(11, 4.7), facecolor="white")
    label(fig, 0.035, 0.905, title, 24, bold=True)
    label(fig, 0.036, 0.808, subtitle, 12)
    label(fig, 0.036, 0.701, "Water depth (m)", 11, bold=True)
    for depth, y in zip(DEPTH_LABELS, ROW_Y):
        label(fig, 0.036, y, depth)
    return fig


def grid_ticks(fig, positions, labels):
    for x, text in zip(positions, labels):
        line(fig, (x, x), (0.211, 0.654), GRID, zorder=1)
        label(fig, x, 0.168, text, 10, align="center")


def status_figure(status):
    fig = figure("Current status of Gulf of America wells",
                 "Each bar represents all wells in its water depth band on 23 Nov 2026.")
    left, width = 0.241, 0.355
    ticks = (0, 25, 50, 75, 100)
    grid_ticks(fig, [left + width * tick / 100 for tick in ticks],
               [f"{tick}%" for tick in ticks])
    columns = (0.681, 0.769, 0.857, 0.945)
    for x, (status_code, color) in zip(columns, STATUS_COLORS.items()):
        rect(fig, x - 0.038, 0.686, 0.010, 0.030, color)
        label(fig, x - 0.022, 0.701, status_code, 11, bold=True)
    for (_, row), y in zip(status.iloc[:4].iterrows(), ROW_Y):
        offset = left
        for x, (status_code, color) in zip(columns, STATUS_COLORS.items()):
            share = row[f"{status_code}_pct"]
            if pd.isna(share):
                label(fig, x, y, "n/a", align="center")
                continue
            segment = width * share / 100
            rect(fig, offset, y - 0.027, segment, 0.054, color)
            label(fig, x, y, f"{share:.1f}%", align="center")
            offset += segment
    label(fig, 0.036, 0.094,
          "PA  Permanently abandoned     TA  Temporarily abandoned     COM  Completed", 10)
    missing = int(status.iloc[4]["wells"])
    label(fig, 0.036, 0.042,
          f"BSEE borehole file, 23 Nov 2026.  {missing:,} wells have no reported water depth.", 10)
    return fig


def age_figure(ta):
    fig = figure("Time in temporary abandonment",
                 "Years from the TA status date to 23 Nov 2026. Dots mark medians and bars span the middle 50%.")
    left, width = 0.241, 0.355
    upper = ta.iloc[:4]["q75_years"].max()
    limit = max(1, math.ceil(upper)) if pd.notna(upper) else 1
    ticks = MaxNLocator(nbins=5, steps=[1, 2, 5, 10]).tick_values(0, limit)

    def position(years):
        return left + width * years / ticks[-1]

    grid_ticks(fig, [position(value) for value in ticks], [f"{v:g}" for v in ticks])
    label(fig, 0.415, 0.701, "Years in TA", 11, bold=True, align="center")
    for x, name in ((0.672, "Median (yr)"), (0.804, "Middle 50% (yr)"), (0.943, "TA wells")):
        label(fig, x, 0.701, name, 11, bold=True, align="center")
    for row, y, color in zip(ta.iloc[:4].itertuples(), ROW_Y, BAND_COLORS):
        label(fig, 0.943, y, f"{row.ta_count:,}", align="center")
        if pd.isna(row.median_years):
            label(fig, 0.672, y, "n/a", align="center")
            label(fig, 0.804, y, "n/a", align="center")
            continue
        line(fig, (position(row.q25_years), position(row.q75_years)), (y, y),
             color, 4, zorder=2)
        line(fig, [position(row.median_years)], [y], color, marker="o", markersize=9,
             markeredgecolor="white", markeredgewidth=1.3, zorder=3)
        label(fig, 0.672, y, f"{row.median_years:.1f}", align="center")
        label(fig, 0.804, y, f"{row.q25_years:.1f} to {row.q75_years:.1f}", align="center")
    missing = int(ta.iloc[4]["ta_count"])
    label(fig, 0.036, 0.065,
          f"BSEE borehole file, 23 Nov 2026.  {missing:,} TA wells have no reported water depth.",
          10)
    return fig


def pa_figure(annual):
    colors = [*BAND_COLORS]
    if NO_DEPTH_LABEL in annual:
        colors.append("#c9c3b8")
    fig = Figure(figsize=(12, 5.6), facecolor="white")
    label(fig, 0.035, 0.927,
          "Gulf of America wells permanently abandoned per year, by water depth", 19, bold=True)
    for x, band, color in zip((0.055, 0.23, 0.42, 0.61, 0.81), annual.columns, colors):
        rect(fig, x, 0.824, 0.014, 0.027, color)
        label(fig, x + 0.021, 0.837, band, 11)

    left, right, bottom, top = 0.087, 0.965, 0.20, 0.728
    ticks = MaxNLocator(nbins=5, integer=True).tick_values(0, max(1, annual.sum(axis=1).max()))
    scale = (top - bottom) / ticks[-1]
    label(fig, left, top + 0.046, "Wells per year", 11, bold=True)
    for tick in ticks:
        y = bottom + tick * scale
        line(fig, (left, right), (y, y), GRID, zorder=1)
        label(fig, left - 0.012, y, f"{tick:,.0f}", 10, align="right")
    step = (right - left) / len(annual)
    for i, (year, row) in enumerate(annual.iterrows()):
        center = left + (i + 0.5) * step
        y = bottom
        for band_index, (count, color) in enumerate(zip(row, colors, strict=True)):
            if count:
                rect(fig, center - 0.41 * step, y, 0.82 * step, count * scale, color,
                     gid=f"pa-{year}-{band_index}")
                y += count * scale
        if year % 10 == 0 or year == annual.index[-1]:
            label(fig, center, bottom - 0.034, str(year), 10, align="center")
    label(fig, (left + right) / 2, 0.104, "Year the well became permanently abandoned", 11,
          align="center")
    label(fig, 0.035, 0.041,
          "BSEE borehole file, 23 Nov 2026. Wells with current PA status count once, in the year that status took effect.", 10)
    return fig


def render_charts(output_dir, status, ta, annual=None):
    """Input rows are the four series depth bands, the no-depth row and the total."""
    output_dir = Path(output_dir)
    bands = ["Under 100 m", "100 to under 500 m", "500 to under 1,500 m",
             "1,500 m and deeper", "No depth", "All depths"]
    if list(status.band) != bands or list(ta.band) != bands:
        raise ValueError("Chart tables require the same six depth rows in series order")
    style = {"svg.fonttype": "none", "svg.hashsalt": "w1-r5", "font.family": "DejaVu Sans",
             "text.usetex": False}
    with mpl.rc_context(style):
        figures = [("status_share_by_band", status_figure(status)), ("ta_age_by_band", age_figure(ta))]
        if annual is not None:
            figures.append(("pa_per_year_by_band", pa_figure(annual)))
        for name, fig in figures:
            fig.savefig(output_dir / f"{name}.svg", metadata={"Date": None})
            fig.savefig(output_dir / f"{name}.png", dpi=160)
