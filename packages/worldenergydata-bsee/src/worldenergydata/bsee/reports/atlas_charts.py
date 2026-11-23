"""Pure data-prep + Plotly figure builders for the all-fields atlas.

These functions take a per-field result DataFrame (as produced by
:class:`AllFieldsRunner` and enriched with geological era + water depth)
and return either a filtered DataFrame or a :class:`plotly.graph_objects.Figure`.

Design rules:
- Deterministic, no side effects, no I/O.
- Flag-don't-fake: rows lacking a required real value are dropped, never
  imputed; the figure builders surface counts so callers can log coverage.

Plotting the Lower-Tertiary "access / concentration" thesis: deepwater,
high-recovery-per-well hubs (few hard-to-reach wells) vs the shallow shelf.
"""

from __future__ import annotations

import pandas as pd

# Thresholds for the headline access/concentration scatter.
MIN_CUM_OIL_MMBBL = 1.0
MIN_WELL_COUNT = 3
# Minimum number of fields for a geological-era cohort to be charted.
MIN_COHORT_FIELDS = 3
# Deepwater / shelf cutoff (ft).
DEEPWATER_FT = 1000.0

_LT_COLOR = "#d62728"  # Lower Tertiary
_OTHER_COLOR = "#1f77b4"  # Other


def access_scatter_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Return the subset of fields plotted in the access/concentration scatter.

    Keeps only *material* fields with enough wells and a real water depth:
    ``CUM_OIL_MMBBL >= 1`` AND ``WELL_COUNT >= 3`` AND ``WATER_DEPTH_AVG``
    present.  Nulls/outliers are dropped honestly (never imputed).
    """
    required = {
        "WATER_DEPTH_AVG",
        "REC_PER_WELL_MMBBL",
        "WELL_COUNT",
        "CUM_OIL_MMBBL",
    }
    if df is None or df.empty or not required.issubset(df.columns):
        return pd.DataFrame()

    work = df.copy()
    mask = (
        (pd.to_numeric(work["CUM_OIL_MMBBL"], errors="coerce") >= MIN_CUM_OIL_MMBBL)
        & (pd.to_numeric(work["WELL_COUNT"], errors="coerce") >= MIN_WELL_COUNT)
        & work["WATER_DEPTH_AVG"].notna()
        & work["REC_PER_WELL_MMBBL"].notna()
    )
    return work[mask].reset_index(drop=True)


def rec_per_well_by_era(df: pd.DataFrame) -> pd.DataFrame:
    """Median REC_PER_WELL_MMBBL grouped by geological era cohort.

    Restricted to *material* fields (``CUM_OIL_MMBBL >= 1`` AND
    ``WELL_COUNT >= 3`` when those columns are present) so the comparison
    reflects producing fields' per-well recovery — otherwise the paleo-based
    era map tags many near-zero-production exploration fields, dragging a
    cohort's median to ~0 and obscuring the signal.

    Only cohorts with at least :data:`MIN_COHORT_FIELDS` fields and a real
    (non-``Unknown``) era are returned, sorted by median recovery descending.
    Columns: ``GEOLOGICAL_ERA``, ``MEDIAN_REC_PER_WELL``, ``FIELD_COUNT``,
    ``IS_LOWER_TERTIARY``.
    """
    needed = {"GEOLOGICAL_ERA", "REC_PER_WELL_MMBBL"}
    if df is None or df.empty or not needed.issubset(df.columns):
        return pd.DataFrame(
            columns=[
                "GEOLOGICAL_ERA",
                "MEDIAN_REC_PER_WELL",
                "FIELD_COUNT",
                "IS_LOWER_TERTIARY",
            ]
        )

    work = df.copy()
    work = work[work["GEOLOGICAL_ERA"].notna()]
    work = work[work["GEOLOGICAL_ERA"].astype(str).str.strip() != "Unknown"]
    work = work[work["REC_PER_WELL_MMBBL"].notna()]
    # Material-field filter (consistent with the access scatter's universe).
    if "CUM_OIL_MMBBL" in work.columns:
        work = work[
            pd.to_numeric(work["CUM_OIL_MMBBL"], errors="coerce") >= MIN_CUM_OIL_MMBBL
        ]
    if "WELL_COUNT" in work.columns:
        work = work[
            pd.to_numeric(work["WELL_COUNT"], errors="coerce") >= MIN_WELL_COUNT
        ]
    if work.empty:
        return pd.DataFrame(
            columns=[
                "GEOLOGICAL_ERA",
                "MEDIAN_REC_PER_WELL",
                "FIELD_COUNT",
                "IS_LOWER_TERTIARY",
            ]
        )

    has_lt = "IS_LOWER_TERTIARY" in work.columns
    rows = []
    for era, grp in work.groupby("GEOLOGICAL_ERA"):
        if len(grp) < MIN_COHORT_FIELDS:
            continue
        rows.append(
            {
                "GEOLOGICAL_ERA": era,
                "MEDIAN_REC_PER_WELL": float(grp["REC_PER_WELL_MMBBL"].median()),
                "FIELD_COUNT": int(len(grp)),
                "IS_LOWER_TERTIARY": (
                    bool(grp["IS_LOWER_TERTIARY"].any()) if has_lt else False
                ),
            }
        )
    out = pd.DataFrame(
        rows,
        columns=[
            "GEOLOGICAL_ERA",
            "MEDIAN_REC_PER_WELL",
            "FIELD_COUNT",
            "IS_LOWER_TERTIARY",
        ],
    )
    if out.empty:
        return out
    return out.sort_values("MEDIAN_REC_PER_WELL", ascending=False).reset_index(
        drop=True
    )


def water_depth_split(df: pd.DataFrame) -> dict:
    """Summarize the deepwater (>1000 ft) vs shelf water-depth split.

    Returns counts and medians over fields that have a real ``WATER_DEPTH_AVG``.
    """
    empty = {
        "n_with_depth": 0,
        "n_deepwater": 0,
        "n_shelf": 0,
        "deepwater_median_ft": None,
        "shelf_median_ft": None,
    }
    if df is None or df.empty or "WATER_DEPTH_AVG" not in df.columns:
        return empty

    wd = pd.to_numeric(df["WATER_DEPTH_AVG"], errors="coerce").dropna()
    if wd.empty:
        return empty

    deep = wd[wd > DEEPWATER_FT]
    shelf = wd[wd <= DEEPWATER_FT]
    return {
        "n_with_depth": int(wd.shape[0]),
        "n_deepwater": int(deep.shape[0]),
        "n_shelf": int(shelf.shape[0]),
        "deepwater_median_ft": float(deep.median()) if not deep.empty else None,
        "shelf_median_ft": float(shelf.median()) if not shelf.empty else None,
    }


def _empty_figure(title: str, note: str):
    import plotly.graph_objects as go

    fig = go.Figure()
    fig.update_layout(
        title=title,
        annotations=[
            dict(
                text=note,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
            )
        ],
    )
    return fig


def access_scatter_figure(sub: pd.DataFrame):
    """Headline scatter: REC_PER_WELL vs WATER_DEPTH, split by Lower Tertiary.

    ``sub`` should already be the output of :func:`access_scatter_frame`.
    Marker size ~ WELL_COUNT, color by IS_LOWER_TERTIARY.
    """
    import plotly.graph_objects as go

    title = "Recovery per Well vs Water Depth (Access / Concentration)"
    if sub is None or sub.empty:
        return _empty_figure(title, "No fields meet the material-field filter.")

    fig = go.Figure()
    has_lt = "IS_LOWER_TERTIARY" in sub.columns
    groups = (
        [(True, "Lower Tertiary", _LT_COLOR), (False, "Other", _OTHER_COLOR)]
        if has_lt
        else [(None, "Fields", _OTHER_COLOR)]
    )
    for flag, label, color in groups:
        part = sub[sub["IS_LOWER_TERTIARY"] == flag] if has_lt else sub
        if part.empty:
            continue
        wells = pd.to_numeric(part["WELL_COUNT"], errors="coerce").fillna(1.0)
        sizes = (wells.clip(lower=1) ** 0.5) * 4.0
        hover = [
            (
                f"{r.get('FIELD_NAME', r.get('FIELD_CODE', ''))}<br>"
                f"Water depth: {r['WATER_DEPTH_AVG']:,.0f} ft<br>"
                f"Rec/well: {r['REC_PER_WELL_MMBBL']:,.2f} MMBBL<br>"
                f"BOPD/well: {r.get('AVG_BOPD_PER_WELL', float('nan')):,.0f}<br>"
                f"Wells: {int(r['WELL_COUNT'])}<br>"
                f"Era: {r.get('GEOLOGICAL_ERA', 'Unknown')}"
            )
            for _, r in part.iterrows()
        ]
        fig.add_trace(
            go.Scatter(
                x=part["WATER_DEPTH_AVG"].tolist(),
                y=part["REC_PER_WELL_MMBBL"].tolist(),
                mode="markers",
                name=label,
                marker=dict(
                    size=sizes.tolist(),
                    color=color,
                    sizemode="diameter",
                    line=dict(width=0.5, color="#333"),
                    opacity=0.75,
                ),
                text=hover,
                hoverinfo="text",
            )
        )
    fig.update_layout(
        title=title,
        xaxis_title="Average Water Depth (ft)",
        yaxis_title="Recovery per Well (MMBBL)",
        legend_title="Geological group",
        height=560,
    )
    return fig


def rec_per_well_figure(cohorts: pd.DataFrame):
    """Bar of median recovery per well by era cohort (>=3 fields each)."""
    import plotly.graph_objects as go

    title = (
        "Median Recovery per Well by Geological Era "
        "(material fields: >=1 MMBBL, >=3 wells; cohorts >= 3 fields)"
    )
    if cohorts is None or cohorts.empty:
        return _empty_figure(title, "No era cohort has at least 3 fields.")

    colors = [
        _LT_COLOR if bool(lt) else _OTHER_COLOR
        for lt in cohorts["IS_LOWER_TERTIARY"].tolist()
    ]
    text = [
        f"n={n}" + (" (LT)" if bool(lt) else "")
        for n, lt in zip(
            cohorts["FIELD_COUNT"].tolist(), cohorts["IS_LOWER_TERTIARY"].tolist()
        )
    ]
    fig = go.Figure(
        data=[
            go.Bar(
                x=cohorts["GEOLOGICAL_ERA"].tolist(),
                y=cohorts["MEDIAN_REC_PER_WELL"].tolist(),
                marker_color=colors,
                text=text,
                textposition="outside",
            )
        ]
    )
    fig.update_layout(
        title=title,
        xaxis_title="Geological Era",
        yaxis_title="Median Recovery per Well (MMBBL)",
        height=460,
        annotations=[
            dict(
                text="Red = Lower Tertiary cohort; blue = Other.",
                xref="paper",
                yref="paper",
                x=0.0,
                y=1.08,
                showarrow=False,
                font=dict(size=11, color="#555"),
            )
        ],
    )
    return fig


def water_depth_figure(df: pd.DataFrame):
    """Histogram of field average water depth, with a deepwater/shelf cutline."""
    import plotly.graph_objects as go

    title = "Field Water Depth Distribution"
    if df is None or df.empty or "WATER_DEPTH_AVG" not in df.columns:
        return _empty_figure(title, "No water-depth data available.")

    wd = pd.to_numeric(df["WATER_DEPTH_AVG"], errors="coerce").dropna()
    if wd.empty:
        return _empty_figure(title, "No water-depth data available.")

    split = water_depth_split(df)
    fig = go.Figure(
        data=[go.Histogram(x=wd.tolist(), marker_color=_OTHER_COLOR, nbinsx=40)]
    )
    fig.add_vline(
        x=DEEPWATER_FT,
        line_width=1.5,
        line_dash="dash",
        line_color=_LT_COLOR,
        annotation_text="1000 ft (deepwater)",
        annotation_position="top",
    )
    fig.update_layout(
        title=(
            f"{title} - {split['n_deepwater']} deepwater (>1000 ft) "
            f"vs {split['n_shelf']} shelf of {split['n_with_depth']} fields"
        ),
        xaxis_title="Average Water Depth (ft)",
        yaxis_title="Number of Fields",
        height=420,
    )
    return fig
