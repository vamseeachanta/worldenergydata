"""Direct-labelled monthly DCA panels, interactive and static.

Both renderers consume MonthlyDca arrays; no independent forecast or recovery
calculation is performed. See monthly_dca for equations, units and citations.
Blue shades encode observed/remaining volume; orange crosses encode zero oil.
Line styles and direct labels retain meaning without colour.
"""

from html import escape
from pathlib import Path

import numpy as np
import pandas as pd

from worldenergydata.bsee.analysis.forecasting.monthly_dca import DAYS_PER_YEAR

BLUE = "#0072B2"
ORANGE = "#D55E00"
GREY = "#4B5563"
OBSERVED_FILL = "#CAE4F1"
REMAINING_FILL = "#E7F3FA"


def _series(result):
    frame = result.history.frame
    # Month-end boundaries give each step exactly its calendar-day width.
    left = frame.index[0] - pd.Timedelta(days=frame.index[0].days_in_month)
    area_dates = pd.DatetimeIndex([left, *frame.index])
    area_rates = np.r_[frame.rate_bpd.to_numpy(), frame.rate_bpd.iloc[-1]]
    time = np.asarray(
        (result.fit_dates - result.origin) / pd.Timedelta(days=DAYS_PER_YEAR)
    )
    return area_dates, area_rates, result.model.rate(time)


def recovery_text(result):
    """State incomplete recovery explicitly instead of substituting zero."""
    eur = (
        f"EUR {result.eur_bbl / 1e6:,.2f} million bbl"
        if result.eur_bbl is not None
        else "EUR not established"
    )
    remaining = "Remaining" if result.limit_reached else "Remaining through horizon"
    return (
        f"Observed {result.observed_bbl / 1e6:,.2f} million bbl · "
        f"{remaining} {result.remaining_bbl / 1e6:,.2f} million bbl · {eur}"
    )


def _limit_text(result):
    years = (
        result.forecast_dates[-1] - result.history.frame.index[-1]
    ).days / DAYS_PER_YEAR
    return (
        f"Limit reached in {years:.1f} years"
        if result.limit_reached
        else f"Limit not reached within {years:.1f} years"
    )


def build_dca_figure(result):
    """Build rate/date, rate/cumulative and withheld-actuals panels in Plotly."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=2,
        cols=2,
        specs=[[{"colspan": 2}, None], [{}, {}]],
        row_heights=[0.66, 0.34],
        vertical_spacing=0.20,
        horizontal_spacing=0.12,
        subplot_titles=(
            "",
            "Rate versus cumulative oil",
            "Historical forecast versus actuals",
        ),
    )
    frame = result.history.frame
    dates, rates, fitted = _series(result)

    def scatter(name, x, y, row=1, col=1, **kwargs):
        fig.add_trace(go.Scatter(name=name, x=x, y=y, **kwargs), row=row, col=col)

    scatter(
        "Produced oil",
        dates,
        rates,
        mode="lines",
        line={"width": 0, "shape": "hv"},
        fill="tozeroy",
        fillcolor=OBSERVED_FILL,
        hoverinfo="skip",
        connectgaps=False,
    )
    scatter(
        "Remaining oil",
        result.forecast_dates,
        result.forecast_rates,
        mode="lines",
        line={"width": 0},
        fill="tozeroy",
        fillcolor=REMAINING_FILL,
        hoverinfo="skip",
    )
    active = ~(frame.missing | frame.shut_in | frame.partial)
    scatter(
        "Reported oil",
        frame.index[active],
        frame.rate_bpd[active],
        mode="markers",
        marker={"size": 5, "color": GREY},
        hovertemplate="%{x|%b %Y}<br>%{y:,.0f} bbl/d<extra>Reported</extra>",
    )
    scatter(
        "Zero oil / shut-in",
        frame.index[frame.shut_in],
        frame.rate_bpd[frame.shut_in],
        mode="markers",
        marker={"size": 8, "symbol": "x", "color": ORANGE},
    )
    flagged = frame.missing | frame.partial
    scatter(
        "Missing / partial report",
        frame.index[flagged],
        np.zeros(flagged.sum()),
        mode="markers",
        marker={"size": 9, "symbol": "triangle-up-open", "color": GREY},
    )
    scatter(
        "Fitted Arps",
        result.fit_dates,
        fitted,
        mode="lines",
        line={"color": BLUE, "width": 2},
    )
    scatter(
        "Forecast",
        result.forecast_dates,
        result.forecast_rates,
        mode="lines",
        line={"color": BLUE, "width": 2, "dash": "dash"},
    )
    today = frame.index[-1]
    fig.add_shape(
        type="line",
        x0=today,
        x1=today,
        y0=0,
        y1=1,
        xref="x",
        yref="y domain",
        line={"color": GREY, "width": 1, "dash": "dot"},
    )
    fig.add_hline(
        y=result.economic_limit,
        line_dash="dash",
        line_color=GREY,
        line_width=1,
        row=1,
        col=1,
    )
    fig.add_annotation(
        x=today,
        y=1.04,
        xref="x",
        yref="y domain",
        showarrow=False,
        text=f"Today · {today:%b %Y}",
        font={"size": 11},
    )
    fig.add_annotation(
        x=0.99,
        y=0.98,
        xref="x domain",
        yref="y domain",
        showarrow=False,
        xanchor="right",
        text=recovery_text(result).replace(" · ", "<br>"),
        align="right",
    )
    fig.add_annotation(
        x=result.forecast_dates[-1],
        y=result.economic_limit,
        xref="x",
        yref="y",
        text=_limit_text(result),
        ax=-90,
        ay=-40,
        arrowwidth=0.7,
        arrowhead=0,
        bgcolor="rgba(255,255,255,0.9)",
    )
    fig.add_annotation(
        x=0.99,
        y=result.economic_limit,
        xref="x domain",
        yref="y",
        showarrow=False,
        xanchor="right",
        yanchor="top",
        text="Economic limit (scenario, bbl/d)",
        font={"size": 10},
    )
    mid = len(result.forecast_dates) // 3
    fig.add_annotation(
        x=result.forecast_dates[mid],
        y=result.forecast_rates[mid],
        text="DCA forecast",
        ax=35,
        ay=-45,
        arrowhead=0,
        arrowwidth=0.7,
    )
    idx = len(result.fit_dates) // 2
    fig.add_annotation(
        x=result.fit_dates[idx],
        y=fitted[idx],
        text=f"Fitted {result.model_name}",
        ax=65,
        ay=-55,
        arrowhead=0,
        arrowwidth=0.7,
    )
    first_active = frame.loc[active].index[0]
    fig.add_annotation(
        x=first_active,
        y=frame.loc[first_active, "rate_bpd"],
        text="Reported oil · dots",
        ax=-10,
        ay=-45,
        arrowhead=0,
        arrowwidth=0.7,
    )
    fig.add_annotation(
        x=0.40,
        y=0.93,
        xref="x domain",
        yref="y domain",
        showarrow=False,
        text="Shaded area = observed + remaining oil<br>EUR requires complete reporting",
        align="left",
        xanchor="left",
        font={"size": 11},
    )
    if frame.shut_in.any():
        fig.add_annotation(
            x=frame.index[frame.shut_in][0],
            y=0,
            text="Zero oil / shut-in · excluded from fit",
            ax=100,
            ay=-35,
            arrowhead=0,
            arrowwidth=0.7,
        )
    if flagged.any():
        fig.add_annotation(
            x=0.02,
            y=0.05,
            xref="x domain",
            yref="y domain",
            text="△ Missing / partial reports; EUR withheld",
            showarrow=False,
            xanchor="left",
        )
    cumulative = frame.oil_bbl.fillna(0).cumsum() / 1e6
    scatter(
        "Rate / observed cumulative",
        cumulative,
        frame.rate_bpd,
        row=2,
        mode="markers",
        marker={"size": 4, "color": GREY},
    )
    scatter(
        "Rate / forecast cumulative",
        result.forecast_cumulative_bbl / 1e6,
        result.forecast_rates,
        row=2,
        mode="lines",
        line={"color": BLUE, "dash": "dash"},
    )
    fig.add_annotation(
        x=0.98,
        y=0.95,
        xref="x2 domain",
        yref="y2 domain",
        showarrow=False,
        xanchor="right",
        text="Dots: reported<br>Dashed: forecast",
        font={"size": 10},
    )
    bt = result.backtest
    if bt is not None:
        scatter(
            "Withheld actuals",
            bt.dates,
            bt.actual,
            row=2,
            col=2,
            mode="markers",
            marker={"size": 4, "color": GREY},
        )
        scatter(
            "Old forecast",
            bt.dates,
            bt.predicted,
            row=2,
            col=2,
            mode="lines",
            line={"color": BLUE, "dash": "dash"},
        )
        text = f"Cutoff {bt.cutoff:%b %Y}<br>RMSE {bt.rmse_bpd:,.0f} bbl/d<br>Dots: actual · dashed: old forecast"
    else:
        text = "Back-test unavailable: insufficient training history"
    fig.add_annotation(
        x=0.02,
        y=0.05,
        xref="x3 domain",
        yref="y3 domain",
        text=text,
        xanchor="left",
        yanchor="bottom",
        showarrow=False,
        align="left",
        font={"size": 10},
    )
    fig.update_layout(
        title={
            "text": f"Decline Curve Analysis (DCA) · {escape(result.history.label)}<br>"
            "<sup>Public BSEE monthly oil · calendar-day rate · illustrative economic limit<br>"
            f"b={result.model.b:.2f} (cap ≤1) · terminal decline {result.model.terminal_decline:.1%} nominal/year</sup>"
        },
        template="plotly_white",
        showlegend=False,
        height=880,
        width=1250,
        margin={"t": 120, "b": 65, "l": 85, "r": 45},
        font={"size": 12, "color": GREY},
    )
    fig.update_xaxes(
        type="date", title_text="Reporting month / forecast date", row=1, col=1
    )
    fig.update_xaxes(title_text="Cumulative oil (million bbl)", row=2, col=1)
    fig.update_xaxes(type="date", title_text="Withheld reporting month", row=2, col=2)
    fig.update_yaxes(
        title_text="Oil rate (bbl/d)", rangemode="tozero", gridcolor="#EDF0F2"
    )
    return fig


def export_static(result, stem):
    """Write report SVG/PNG with matplotlib Agg; no browser dependency."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    from matplotlib.ticker import StrMethodFormatter

    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    dates, rates, fitted = _series(result)
    frame = result.history.frame
    with plt.rc_context({"font.size": 10, "svg.fonttype": "none"}):
        fig = plt.figure(figsize=(13, 9), layout="constrained")
        grid = fig.add_gridspec(2, 2, height_ratios=[2, 1])
        ax, cum, back = (
            fig.add_subplot(grid[0, :]),
            fig.add_subplot(grid[1, 0]),
            fig.add_subplot(grid[1, 1]),
        )
        ax.fill_between(dates, rates, step="post", color=OBSERVED_FILL)
        ax.fill_between(
            result.forecast_dates, result.forecast_rates, color=REMAINING_FILL
        )
        active = ~(frame.shut_in | frame.missing | frame.partial)
        ax.scatter(
            frame.index[active], frame.rate_bpd[active], s=12, color=GREY, zorder=3
        )
        ax.scatter(
            frame.index[frame.shut_in],
            frame.rate_bpd[frame.shut_in],
            marker="x",
            color=ORANGE,
            zorder=4,
        )
        flagged = frame.missing | frame.partial
        ax.scatter(
            frame.index[flagged],
            np.zeros(flagged.sum()),
            marker="^",
            facecolors="none",
            edgecolors=GREY,
            zorder=4,
        )
        ax.plot(result.fit_dates, fitted, color=BLUE, linewidth=1.6)
        ax.plot(
            result.forecast_dates,
            result.forecast_rates,
            "--",
            color=BLUE,
            linewidth=1.6,
        )
        ax.axvline(frame.index[-1], linestyle=":", color=GREY, linewidth=1)
        ax.axhline(result.economic_limit, linestyle="--", color=GREY, linewidth=1)
        ax.text(
            frame.index[-1],
            1.01,
            f"Today · {frame.index[-1]:%b %Y}",
            transform=ax.get_xaxis_transform(),
            ha="center",
        )
        ax.text(
            0.98,
            0.94,
            recovery_text(result).replace(" · ", "\n"),
            transform=ax.transAxes,
            ha="right",
            va="top",
        )
        ax.annotate(
            _limit_text(result),
            (result.forecast_dates[-1], result.economic_limit),
            xytext=(-115, 38),
            textcoords="offset points",
            arrowprops={"arrowstyle": "-", "lw": 0.7},
        )
        ax.text(
            0.98,
            result.economic_limit,
            "Economic limit (scenario)",
            transform=ax.get_yaxis_transform(),
            ha="right",
            va="top",
        )
        idx = len(result.fit_dates) // 2
        ax.annotate(
            f"Fitted {result.model_name}",
            (result.fit_dates[idx], fitted[idx]),
            xytext=(45, 40),
            textcoords="offset points",
            arrowprops={"arrowstyle": "-", "lw": 0.7},
        )
        mid = len(result.forecast_dates) // 3
        ax.annotate(
            "DCA forecast",
            (result.forecast_dates[mid], result.forecast_rates[mid]),
            xytext=(30, 55),
            textcoords="offset points",
            arrowprops={"arrowstyle": "-", "lw": 0.7},
        )
        first_active = frame.loc[active].index[0]
        ax.annotate(
            "Reported oil · dots",
            (first_active, frame.loc[first_active, "rate_bpd"]),
            xytext=(-10, 45),
            textcoords="offset points",
            arrowprops={"arrowstyle": "-", "lw": 0.7},
        )
        note = "Shaded area = observed + remaining oil\nUntil scenario economic limit"
        if frame.shut_in.any():
            note += "\nOrange ×: zero oil / shut-in; excluded from fit"
        if flagged.any():
            note += "\n△ Missing / partial reports; EUR withheld"
        ax.text(0.40, 0.93, note, transform=ax.transAxes, va="top", fontsize=10)
        cum.scatter(
            frame.oil_bbl.fillna(0).cumsum() / 1e6, frame.rate_bpd, s=10, color=GREY
        )
        cum.plot(
            result.forecast_cumulative_bbl / 1e6,
            result.forecast_rates,
            "--",
            color=BLUE,
        )
        cum.set(
            title="Rate versus cumulative oil", xlabel="Cumulative oil (million bbl)"
        )
        cum.text(
            0.98,
            0.94,
            "Dots: reported\nDashed: forecast",
            transform=cum.transAxes,
            ha="right",
            va="top",
            fontsize=9,
        )
        bt = result.backtest
        if bt is not None:
            back.scatter(bt.dates, bt.actual, s=12, color=GREY)
            back.plot(bt.dates, bt.predicted, "--", color=BLUE)
            back.text(
                0.02,
                0.05,
                f"Cutoff {bt.cutoff:%b %Y}\nRMSE {bt.rmse_bpd:,.0f} bbl/d\nDots: actual · dashed: old forecast",
                transform=back.transAxes,
                ha="left",
                va="bottom",
                fontsize=9,
            )
        else:
            back.text(
                0.5,
                0.5,
                "Back-test unavailable:\ninsufficient training history",
                transform=back.transAxes,
                ha="center",
            )
        back.set(
            title="Historical forecast versus actuals",
            xlabel="Withheld reporting month",
        )
        for panel in (ax, cum, back):
            panel.set_ylabel("Oil rate (bbl/d)")
            panel.set_ylim(bottom=0)
            panel.grid(axis="y", color="#EDF0F2")
            panel.set_axisbelow(True)
            panel.spines[["top", "right"]].set_visible(False)
            panel.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
        for panel in (ax, back):
            locator = mdates.AutoDateLocator(minticks=4, maxticks=7)
            panel.xaxis.set_major_locator(locator)
            panel.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        ax.set_xlabel("Reporting month / forecast date")
        fig.suptitle(
            f"Decline Curve Analysis (DCA) · {result.history.label}\n"
            "Public BSEE monthly oil · calendar-day rate · illustrative economic limit\n"
            f"b={result.model.b:.2f} (cap ≤1) · terminal decline {result.model.terminal_decline:.1%} nominal/year",
            fontsize=15,
        )
        try:
            for extension in ("svg", "png"):
                fig.savefig(stem.with_suffix(f".{extension}"), dpi=160)
        finally:
            plt.close(fig)
