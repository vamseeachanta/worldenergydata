"""Lease cohort tables, chart rendering and reconciliation against BSEE records."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
from source_inputs import BORE, OWNERS, PRODUCTION, REPOSITORY, TAPE

BANDS = [
    "Under 100 m",
    "100 to 500 m",
    "500 to 1,500 m",
    "1,500 m and deeper",
    "Unknown",
]
ALL = "All bands"
YEARS = list(range(2005, 2027))
ALL_YEARS = "All years"
BAND_COLORS = ["#6588a6", "#427298", "#245476", "#102e46", "#c9c3b8"]
TEAL, GREY, SAND, INK, GRID = "#007c78", "#777777", "#c9c3b8", "#333333", "#efefef"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def depth_band(metres):
    require(not metres.lt(0).any(), "Negative maximum block depth")
    return (
        pd.cut(metres, [0, 100, 500, 1500, np.inf], right=False, labels=BANDS[:4])
        .astype("string")
        .fillna("Unknown")
    )


def month_lag(effective, event):
    return (
        (event.dt.year - effective.dt.year) * 12 + event.dt.month - effective.dt.month
    )


def groups(frame, years):
    """Actual lease records for each margin; do not sum percentages or quartiles."""
    for y in [*years, ALL_YEARS]:
        yr = frame if y == ALL_YEARS else frame.loc[frame.issue_year.eq(y)]
        by_band = dict(tuple(yr.groupby("depth_band", sort=False)))
        empty = yr.iloc[:0]
        for band in [*BANDS, ALL]:
            yield str(y), band, yr if band == ALL else by_band.get(band, empty)


def pct(count, denominator):
    return 100 * count / denominator if denominator else np.nan


def issue_table(frame):
    return pd.DataFrame(
        [
            {"issue_year": y, "depth_band": b, "leases": len(g)}
            for y, b, g in groups(frame, YEARS)
        ]
    )


def status_table(frame):
    legend = (
        frame[["status_code", "status_label"]]
        .drop_duplicates()
        .set_index("status_code")
    )
    require(legend.index.is_unique, "Multiple meanings for the same status code")
    rows = []
    for year, band, g in groups(frame, YEARS):
        counts = g.status_code.value_counts()
        for code, label in legend.status_label.sort_index().items():
            n = int(counts.get(code, 0))
            rows.append(
                {
                    "issue_year": year,
                    "depth_band": band,
                    "status_code": code,
                    "status_label": label,
                    "leases": n,
                    "cohort_leases": len(g),
                    "share_pct": pct(n, len(g)),
                }
            )
    return pd.DataFrame(rows)


def quartiles(series, name):
    sample = series.dropna()
    values = (
        sample.quantile([0.25, 0.5, 0.75]).tolist() if len(sample) else [np.nan] * 3
    )
    return dict(zip([f"{name}_p25", f"{name}_median", f"{name}_p75"], values))


COHORT_START, COHORT_END = 2005, 2020
FOLLOWUP_YEARS = 5
WINDOW_MONTHS = 12 * FOLLOWUP_YEARS
DAYS_PER_YEAR = 365.25
MATURE_PERIODS = {
    "2005 to 2009": (2005, 2009),
    "2010 to 2014": (2010, 2014),
    "2015 to 2019": (2015, 2019),
    "2020 only": (2020, 2020),
}
MATURE_TOTAL = f"{COHORT_START} to {COHORT_END}"


def period_groups(frame):
    years = frame.effective_date.dt.year
    for period, (start, end) in MATURE_PERIODS.items():
        yield period, frame.loc[years.between(start, end)]
    yield MATURE_TOTAL, frame


OPEN_STATUSES = {"PRIMRY", "SOP", "OPERNS", "PROD", "UNIT"}
ENDED_STATUSES = {"EXPIR", "RELINQ", "TERMIN", "CANCEL"}


def open_at_file_date(status):
    unclassified = status[~status.isin(OPEN_STATUSES | ENDED_STATUSES)].unique()
    if len(unclassified):
        raise ValueError(f"Unclassified lease status at file date: {unclassified}")
    return status.isin(OPEN_STATUSES)


def open_counts(group, no_event):
    codes = group.loc[no_event & group.open_lease, "status_code"]
    return dict(
        open_without_observed_event=len(codes),
        primry_sop_operns_without_event=int(
            codes.isin(["PRIMRY", "SOP", "OPERNS"]).sum()
        ),
        prod_without_event=int(codes.eq("PROD").sum()),
        unit_without_event=int(codes.eq("UNIT").sum()),
    )


def exploration_table(frame):
    frame = frame.assign(open_lease=open_at_file_date(frame.status_code))
    rows = []
    for year, band, g in groups(frame, range(COHORT_START, COHORT_END + 1)):
        wells = int(g.exploration_wells.sum())
        explored = int(g.exploration_wells.gt(0).sum())
        any_bore = int(g.has_any_e_bore.sum())
        days = (g.exploration_spud - g.effective_date).dt.days
        bore_days = (g.any_e_bore_spud - g.effective_date).dt.days
        within_five = int(
            (
                g.exploration_spud
                <= g.effective_date + pd.DateOffset(years=FOLLOWUP_YEARS)
            ).sum()
        )
        rows.append(
            dict(
                issue_year=year,
                depth_band=band,
                leases=len(g),
                explored_leases=explored,
                **open_counts(g, g.exploration_spud.isna()),
                exploration_wells=wells,
                share_pct=pct(explored, len(g)),
                leases_with_any_e_bore=any_bore,
                any_e_bore_share_pct=pct(any_bore, len(g)),
                explored_within_five_years=within_five,
                five_year_share_pct=pct(within_five, len(g)),
                timed_leases=int(days.count()),
                **quartiles(days, "days_to_spud"),
                **quartiles(bore_days, "days_to_any_e_bore"),
            )
        )
    return pd.DataFrame(rows)


EVENTS = {"Crude oil": "first_oil_month", "Any hydrocarbon": "first_production_month"}


def production_table(frame, audits=None, *, last_source_month):
    """The first 60 reporting months are lags 0 through 59 for month-start leases."""
    require(
        frame.effective_date.dt.is_month_start.all(),
        "Monthly production cannot resolve the window of a mid-month lease",
    )
    mature = frame.effective_date.dt.year.between(COHORT_START, COHORT_END)
    cohort = frame.loc[mature].assign(
        open_lease=open_at_file_date(frame.loc[mature, "status_code"])
    )
    require(
        (
            cohort.effective_date.dt.to_period("M") + WINDOW_MONTHS - 1
            <= pd.Period(last_source_month, freq="M")
        ).all(),
        "Insufficient follow-up in production detail",
    )
    rows = []
    for event, col in EVENTS.items():
        elapsed = month_lag(cohort.effective_date, cohort[col])
        qualified = elapsed.between(0, WINDOW_MONTHS - 1)
        sample = cohort.assign(elapsed=elapsed, timed=elapsed.where(qualified))
        if audits is not None:
            name = event.lower()
            observed = int(elapsed.count())
            timed = int(qualified.sum())
            with_term = int((qualified & cohort.primary_term_years.gt(0)).sum())
            audits.extend(
                [
                    dict(
                        stage=f"Matured observed {name} leases",
                        read=int(frame[col].count()),
                        kept=observed,
                        drops={
                            "outside_mature_cohort": int(
                                frame.loc[~mature, col].count()
                            )
                        },
                    ),
                    dict(
                        stage=f"Timed {name} leases",
                        read=observed,
                        kept=timed,
                        drops={
                            "pre_effective_event": int(elapsed.lt(0).sum()),
                            "after_window": int(elapsed.ge(WINDOW_MONTHS).sum()),
                        },
                    ),
                    dict(
                        stage=f"Timed {name} leases with positive primary term",
                        read=timed,
                        kept=with_term,
                        drops={
                            "missing_or_nonpositive_primary_term": timed - with_term
                        },
                    ),
                ]
            )
        for period, pool in period_groups(sample):
            for band in [*BANDS, ALL]:
                g = pool if band == ALL else pool.loc[pool.depth_band.eq(band)]
                term = g.primary_term_years.where(g.primary_term_years.gt(0))
                ratios = 100 * g.timed / (12 * term)
                n = int(g.timed.count())
                rows.append(
                    dict(
                        period=period,
                        depth_band=band,
                        event=event,
                        leases=len(g),
                        observed_leases=int(g.elapsed.count()),
                        without_observed_event=int(g.elapsed.isna().sum()),
                        **open_counts(g, g.elapsed.isna()),
                        timed_leases=n,
                        pre_effective_leases=int(g.elapsed.lt(0).sum()),
                        after_window_leases=int(g.elapsed.ge(WINDOW_MONTHS).sum()),
                        share_pct=pct(n, len(g)),
                        median_years=g.timed.median() / 12 if n else np.nan,
                        term_leases=int(ratios.count()),
                        over_term_leases=int(g.timed.ge(12 * term).sum()),
                        **quartiles(g.timed, "months"),
                        **quartiles(ratios, "primary_term_pct"),
                        eligible_effective_years=MATURE_TOTAL,
                    )
                )
    return pd.DataFrame(rows)


def equal_counts(left, right, message):
    a, b = left.sort_index(), right.sort_index()
    require(
        a.index.equals(b.index) and np.array_equal(a.to_numpy(), b.to_numpy()), message
    )


def validate_margins(table, columns, years):
    """Cover every count column. Including the all-year/all-band corners tests both margins."""
    detailed = table.loc[table.depth_band.ne(ALL)]
    equal_counts(
        detailed.groupby("issue_year")[columns].sum(),
        table.loc[table.depth_band.eq(ALL)].set_index("issue_year")[columns],
        "Depth rows disagree with an independently tabulated all-band margin",
    )
    detailed = table.loc[table.issue_year.ne(ALL_YEARS)]
    require(set(detailed.issue_year) == {str(y) for y in years}, "Year grid incomplete")
    equal_counts(
        detailed.groupby("depth_band")[columns].sum(),
        table.loc[table.issue_year.eq(ALL_YEARS)].set_index("depth_band")[columns],
        "Annual rows disagree with an independently tabulated all-year margin",
    )


def validate_issues(table, frame):
    validate_margins(table, ["leases"], YEARS)
    grand = table.loc[table.issue_year.eq(ALL_YEARS) & table.depth_band.eq(ALL)]
    require(
        len(grand) == 1 and grand.leases.item() == frame.lease_id.nunique(),
        "Grand total disagrees with distinct source lease identities",
    )


def select_one(table, filters):
    selected = table
    for col, value in filters.items():
        selected = selected.loc[selected[col].eq(value)]
    require(len(selected) == 1, f"Expected one row for {filters}, got {len(selected)}")
    return selected.iloc[0]


def audit_upstreams():
    """Expected data flow, including independent source roots and reused subsets."""
    dated = "BoreholeRawData, dated Gulf bore records"
    assigned = "Original-spud API10s attributable to effective cohort leases"
    matched = "ProductionRawData monthly detail matched to issuance cohort"
    chains = [
        (
            "LSETAPE effective Gulf lease cohort",
            "Exploration cohort effective through 2020",
        ),
        (
            "ProductionRawData depth lookup matched to cohort for unit comparison",
            "Matched lease depths comparable across sources",
        ),
        (
            "BoreholeRawData site depth cleaning",
            dated,
            "Dated Gulf bore records at earliest API10 spud",
            "Earliest-spud bore records grouped into distinct Gulf API10s",
            assigned,
            "Cohort API10s originally spudded as exploratory",
        ),
        (dated, "All dated Gulf bores for E-bore lease sensitivity"),
        (
            assigned,
            "Original-spud API10s for well-site exploration timing",
            "First exploration spud on each lease at measured well site",
            "First-spud exploratory API10s grouped into distinct timed leases",
            "Timed leases classified by measured site band",
        ),
        ("LeaseOwnerRawData current assignments on cohort leases",),
    ]
    for event in EVENTS:
        name = event.lower()
        chains.append(
            (
                matched,
                f"Matched lease-month rows with positive {name}",
                f"Distinct observed {name} leases",
                f"Matured observed {name} leases",
                f"Timed {name} leases",
                f"Timed {name} leases with positive primary term",
            )
        )
    parents = {}
    for chain in chains:
        parents.setdefault(chain[0], "")
        parents.update({child: parent for parent, child in zip(chain, chain[1:])})
    return parents


def audit_table(audits):
    parents = audit_upstreams()
    rows = pd.DataFrame(
        [
            {
                "stage": a["stage"],
                "upstream_stage": parents[a["stage"]],
                "rows_read": a["read"],
                "rows_kept": a["kept"],
                "rows_dropped": sum(a["drops"].values()),
                **{f"drop__{k}": v for k, v in a["drops"].items()},
                **{f"flag__{k}": v for k, v in a.get("flags", {}).items()},
            }
            for a in audits
        ]
    ).fillna(0)
    counts = rows.columns.drop(["stage", "upstream_stage"])
    return rows.astype({col: "int64" for col in counts})


def compare_native_depths(leases, production_zip):
    """The BSEE production product labels its integer lease maximum in metres."""
    with (
        ZipFile(production_zip) as archive,
        archive.open("ProductionRawData/mv_production_waterdepth.txt") as member,
    ):
        rows = pd.read_csv(
            member,
            usecols=["LEASE_NUMBER", "MAX_WTR_DPTH"],
            dtype=str,
            keep_default_na=False,
        )
    rows["LEASE_NUMBER"] = rows.LEASE_NUMBER.str.strip()
    rows["MAX_WTR_DPTH"] = pd.to_numeric(
        rows.MAX_WTR_DPTH.str.strip().replace("", pd.NA)
    )
    selected = rows[rows.LEASE_NUMBER.isin(leases.lease_id)]
    joined = leases.set_index("lease_id")[["lease_depth_m", "block_max_depth_ft"]].join(
        selected.set_index("LEASE_NUMBER").MAX_WTR_DPTH,
        how="inner",
        validate="one_to_one",
    )
    comparable = joined.dropna()
    if comparable.empty:
        raise ValueError("No matched maximum depths for independent unit comparison")
    converted = (comparable.lease_depth_m - comparable.MAX_WTR_DPTH).abs()
    unconverted = (comparable.block_max_depth_ft - comparable.MAX_WTR_DPTH).abs()
    require(
        converted.sum() < unconverted.sum(),
        "Converted block depths disagree with the native metre scale",
    )
    require(
        converted.le(1).all(),
        "A matched maximum differs by more than one unit of the whole-metre lookup",
    )
    audit = {
        "stage": "ProductionRawData depth lookup matched to cohort for unit comparison",
        "read": len(rows),
        "kept": len(selected),
        "drops": {
            "lease_outside_cohort": int(
                (~rows.LEASE_NUMBER.isin(leases.lease_id)).sum()
            )
        },
    }
    return {
        "compared_block_depths": len(comparable),
        "depths_within_one_metre": int(converted.le(1).sum()),
    }, [
        audit,
        {
            "stage": "Matched lease depths comparable across sources",
            "read": len(joined),
            "kept": len(comparable),
            "drops": {"missing_comparison_depth": int(joined.isna().any(axis=1).sum())},
        },
    ]


def read_table(output, stem):
    return pd.read_csv(
        output / f"{stem}.csv",
        dtype={"issue_year": str, "status_code": str},
        keep_default_na=True,
    )


def validate_status(table, frame):
    codes = frame.status_code.unique()
    require(set(table.status_code) == set(codes), "Status codes lost in output")
    for code in codes:
        sub = table[table.status_code.eq(code)]
        validate_margins(sub, ["leases"], YEARS)
        total = select_one(sub, {"issue_year": ALL_YEARS, "depth_band": ALL}).leases
        require(
            total == frame.status_code.eq(code).sum(),
            f"{code} disagrees with source count",
        )
    ix = ["issue_year", "depth_band"]
    sums = table.groupby(ix).leases.sum()
    den = table.drop_duplicates(ix).set_index(ix).cohort_leases
    equal_counts(sums, den, "Statuses do not exhaust cohort")
    expected = (
        table.leases.div(table.cohort_leases.where(table.cohort_leases.gt(0))) * 100
    )
    require(
        np.allclose(expected, table.share_pct, equal_nan=True),
        "Incorrect status denominator",
    )


def validate_exploration(table, frame, assignments):
    cols = [
        "leases",
        "explored_leases",
        "open_without_observed_event",
        "primry_sop_operns_without_event",
        "prod_without_event",
        "unit_without_event",
        "exploration_wells",
        "leases_with_any_e_bore",
        "timed_leases",
        "explored_within_five_years",
    ]
    validate_margins(table, cols, range(COHORT_START, COHORT_END + 1))
    grand = select_one(table, {"issue_year": ALL_YEARS, "depth_band": ALL})
    require(
        grand.leases == len(frame)
        and grand.exploration_wells
        == assignments.loc[
            assignments.lease_id.isin(frame.lease_id) & assignments.well_type.eq("E"),
            "api10",
        ].nunique(),
        "Exploration well count disagrees with API10 assignments",
    )
    require(
        (table.explored_leases <= table.leases_with_any_e_bore).all()
        and (table.leases_with_any_e_bore <= table.leases).all()
        and (table.timed_leases == table.explored_leases).all()
        and (
            table.explored_leases + table.open_without_observed_event <= table.leases
        ).all()
        and (table.explored_within_five_years <= table.explored_leases).all(),
        "Exploration counts not nested",
    )
    for numerator, percentage in [
        ("explored_leases", "share_pct"),
        ("leases_with_any_e_bore", "any_e_bore_share_pct"),
        ("explored_within_five_years", "five_year_share_pct"),
    ]:
        require(
            np.allclose(
                table[percentage], table[numerator] / table.leases * 100, equal_nan=True
            ),
            f"Exploration {percentage} disagrees with numerator and denominator",
        )


def validate_production(table, frame):
    cols = [
        "leases",
        "observed_leases",
        "without_observed_event",
        "open_without_observed_event",
        "primry_sop_operns_without_event",
        "prod_without_event",
        "unit_without_event",
        "timed_leases",
        "pre_effective_leases",
        "after_window_leases",
        "term_leases",
        "over_term_leases",
    ]
    equal_counts(
        table[table.depth_band.ne(ALL)].groupby(["period", "event"])[cols].sum(),
        table[table.depth_band.eq(ALL)].set_index(["period", "event"])[cols],
        "Production count margins disagree",
    )
    equal_counts(
        table[table.period.ne(MATURE_TOTAL)]
        .groupby(["depth_band", "event"])[cols]
        .sum(),
        table[table.period.eq(MATURE_TOTAL)].set_index(["depth_band", "event"])[cols],
        "Production periods disagree with the full matured cohort",
    )
    require(
        (table.observed_leases + table.without_observed_event == table.leases).all()
        and (table.open_without_observed_event <= table.without_observed_event).all()
        and (
            table.timed_leases + table.pre_effective_leases + table.after_window_leases
            == table.observed_leases
        ).all()
        and (table.term_leases <= table.timed_leases).all()
        and (table.over_term_leases <= table.term_leases).all(),
        "Invalid production sample sizes",
    )
    for event, col in EVENTS.items():
        row = select_one(
            table, {"period": MATURE_TOTAL, "depth_band": ALL, "event": event}
        )
        require(
            row.observed_leases == frame[col].count() and row.leases == len(frame),
            f"{event} grand count disagrees with matched source",
        )
    both = frame.loc[frame.first_oil_month.notna()]
    require(
        (both.first_production_month <= both.first_oil_month).all(),
        "Oil precedes all hydrocarbons",
    )


def validate_wells(assignments, frame):
    merged = assignments.merge(
        frame[["lease_id", "depth_band"]],
        how="left",
        on="lease_id",
        validate="many_to_one",
    )
    require(
        merged.depth_band.notna().all()
        and merged.api10.str.fullmatch(r"[0-9]{10}").all(),
        "Unmatched well or invalid API10",
    )
    require(
        merged.groupby("api10").depth_band.nunique().le(1).all()
        and merged.api10.is_unique,
        "API10 repeats or spans bands",
    )


def validate_audit(table):
    reasons = table.filter(like="drop__")
    require(
        table.stage.is_unique and table.stage.notna().all(),
        "Audit stage repeats or is empty",
    )
    require(
        (table.rows_read == table.rows_kept + table.rows_dropped).all()
        and (reasons.sum(axis=1) == table.rows_dropped).all(),
        "Read, kept and drop reasons disagree",
    )
    parents = audit_upstreams()
    require(set(table.stage) == set(parents), "Audit stages missing or unexpected")
    ledger = table.set_index("stage")
    require(
        ledger.upstream_stage.fillna("").to_dict() == parents,
        "Incorrect upstream stage in audit",
    )
    for stage, upstream in parents.items():
        if upstream:
            require(
                ledger.at[stage, "rows_read"] == ledger.at[upstream, "rows_kept"],
                f"Audit continuity failure: {upstream} -> {stage}",
            )
    flags = table.filter(like="flag__")
    require(
        flags.le(table.rows_kept, axis="index").all().all(),
        "Flag count exceeds retained rows",
    )
    values = table.drop(columns=["stage", "upstream_stage"]).to_numpy(dtype=float)
    require(
        np.isfinite(values).all() and (values >= 0).all() and (values % 1 == 0).all(),
        "Invalid count in audit",
    )


BOUND_VARIANTS = {
    "original": "original rule",
    "a": "a any type bottom",
    "b": "b any type surface",
    "c": "c bottom or surface",
    "d": "d type E bottom or surface",
    "e": "e any spud date",
}


def write_lease_match_bounds(output, check, counts_by_group):
    rows = []
    for year, cohort in [(ALL_YEARS, "2005 to 2020"), ("2005", "2005")]:
        require(
            counts_by_group[year, "Unknown"]["n"] == 0,
            f"Unallocated lease depth in {cohort}",
        )
        for band in [*BANDS[:4], ALL]:
            counts = counts_by_group[year, band]
            for key, variant in BOUND_VARIANTS.items():
                rows.append(
                    {
                        "variant": variant,
                        "cohort": cohort,
                        "band": "All" if band == ALL else band,
                        "leases": counts["n"],
                        "matched_leases": counts[key],
                        "share_pct": pct(counts[key], counts["n"]),
                    }
                )
    path = output / "lease_match_bounds.csv"
    pd.DataFrame(rows).to_csv(
        path, index=False, float_format="%.2f", lineterminator="\n"
    )
    saved = pd.read_csv(path, dtype={"cohort": str})

    def check_anchor(variant, expected):
        row = select_one(
            saved, {"variant": variant, "cohort": "2005 to 2020", "band": "All"}
        )
        require(
            (row.matched_leases, row.leases) == (expected, 7126),
            f"Read back {row.matched_leases:,} of {row.leases:,}",
        )

    for key, expected in [("original", 432), ("d", 477)]:
        variant = BOUND_VARIANTS[key]
        check(
            f"Lease match bounds, 2005 to 2020, All, {variant}: {expected} of 7,126",
            lambda: check_anchor(variant, expected),
        )
    return saved


def draw_charts(output, lease_last, bore_cutoff):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.artist import Artist
    from matplotlib.patches import Patch, Rectangle
    from matplotlib.ticker import StrMethodFormatter

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "text.color": INK,
            "axes.labelcolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "axes.edgecolor": SAND,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "svg.fonttype": "none",
            "svg.hashsalt": "bsee-lease-part-1",
        }
    )

    def prepare(ax, grid_axis="x"):
        ax.set_axisbelow(True)
        ax.grid(axis=grid_axis, color=GRID, linewidth=1)
        ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
        ax.tick_params(length=0, pad=6)

    def heading(fig, title, subtitle):
        fig.text(0.045, 0.965, title, fontsize=21, weight="bold", va="top")
        fig.text(0.045, 0.90, subtitle, fontsize=11, va="top")

    def save(fig, stem):
        # All marks are drawn within the explicit plotted limits. Write native
        # unclipped geometry so the vector and raster versions use the same marks.
        for artist in fig.findobj(match=Artist):
            artist.set_clip_on(False)
        fig.savefig(output / f"{stem}.svg", metadata={"Date": None})
        fig.savefig(output / f"{stem}.png", dpi=150)
        plt.close(fig)

    data = read_table(output, "issuance")
    issued = data[data.issue_year.ne(ALL_YEARS) & data.depth_band.ne(ALL)].pivot(
        index="issue_year", columns="depth_band", values="leases"
    )
    fig, ax = plt.subplots(figsize=(11, 5.6))
    fig.subplots_adjust(left=0.085, right=0.98, top=0.72, bottom=0.20)
    heading(
        fig,
        "Gulf leases by effective year",
        "Each lease is counted once at the maximum water depth reported for its block.",
    )
    bottom = np.zeros(len(issued))
    x = np.arange(len(issued))
    for band, color in zip(BANDS, BAND_COLORS):
        counts = issued[band].to_numpy()
        if counts.sum():
            ax.bar(
                x,
                counts,
                width=0.76,
                bottom=bottom,
                color=color,
                label=band,
            )
            bottom += counts
    prepare(ax, "y")
    ax.set_xlim(-0.7, len(x) - 0.3)
    ax.set_ylabel("Leases")
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    ax.set_xticks(x, [str(y)[-2:] for y in issued.index])
    ax.legend(
        loc="lower left",
        bbox_to_anchor=(0, 1.01),
        frameon=False,
        ncols=5,
        borderaxespad=0,
    )
    fig.text(
        0.085,
        0.07,
        f"2026 is partial, to the latest effective month ({lease_last[:7]}). Source: BSEE/BOEM LSETAPE.",
        fontsize=9,
    )
    save(fig, "issuance")

    statuses = read_table(output, "current_status")
    labels = (
        statuses[statuses.issue_year.eq(ALL_YEARS) & statuses.depth_band.eq(ALL)]
        .sort_values("leases", ascending=False)
        .status_code.tolist()
    )
    present_bands = [b for b in BANDS if issued[b].sum()]
    panels = [ALL, *present_bands]
    fig, axes = plt.subplots(
        (len(panels) + 1) // 2, 2, figsize=(13, 9.3), squeeze=False
    )
    fig.subplots_adjust(
        left=0.098, right=0.98, top=0.815, bottom=0.115, hspace=0.55, wspace=0.24
    )
    fig.text(
        0.045,
        0.975,
        "Current lease status by effective year",
        fontsize=21,
        weight="bold",
        va="top",
    )
    fig.text(
        0.045,
        0.912,
        "Within each depth band and year, the shares across status codes sum to 100%.",
        fontsize=11,
    )
    cats = [
        "No leases",
        "0%",
        ">0% to <10%",
        "10% to <30%",
        "30% to <60%",
        "60% to 100%",
    ]
    from matplotlib.colors import to_rgb

    # Blend the categorical teal with the white ground for an ordered share scale.
    teal = np.asarray(to_rgb(TEAL))
    shades = [
        GREY,
        "white",
        *[(1 - alpha) + alpha * teal for alpha in (0.20, 0.45, 0.70, 1.0)],
    ]

    def shade_for(value):
        if pd.isna(value):
            return shades[0]
        return shades[
            1 + int(value > 0) + int(value >= 10) + int(value >= 30) + int(value >= 60)
        ]

    for ax, band in zip(axes.flat, panels):
        ax.set_title(band, loc="left", fontsize=12, weight="bold", pad=4)
        grid = (
            statuses[(statuses.depth_band == band) & (statuses.issue_year != ALL_YEARS)]
            .pivot(index="status_code", columns="issue_year", values="share_pct")
            .reindex(labels)
        )
        for row, entries in enumerate(grid.itertuples(index=False, name=None)):
            for col, value in enumerate(entries):
                ax.add_patch(
                    Rectangle(
                        (col - 0.5, row - 0.5),
                        1,
                        1,
                        facecolor=shade_for(value),
                        edgecolor=GRID,
                        linewidth=0.45,
                    )
                )
        ax.set(xlim=(-0.5, len(YEARS) - 0.5), ylim=(len(labels) - 0.5, -0.5))
        ax.set_yticks(range(len(labels)), labels, fontsize=8)
        ticks = [0, 3, 6, 9, 12, 15, 18, 21]
        ax.set_xticks(ticks, [YEARS[t] for t in ticks], fontsize=8)
        ax.tick_params(length=0, pad=3)
        ax.spines[:].set_visible(False)
    for ax in list(axes.flat)[len(panels) :]:
        ax.set_visible(False)
    fig.legend(
        [Patch(facecolor=c, edgecolor=SAND, linewidth=0.6) for c in shades],
        cats,
        loc="lower left",
        bbox_to_anchor=(0.084, 0.046),
        ncols=6,
        frameon=False,
        fontsize=9,
    )
    fig.text(
        0.09,
        0.024,
        "Source: BSEE/BOEM LSETAPE. Literal tape codes are preserved. 2026 is partial.",
        fontsize=9,
    )
    save(fig, "current_status")

    def labels_and_axis(ax, bands):
        prepare(ax)
        ax.set_yticks(np.arange(len(bands)), bands)
        ax.set_ylim(len(bands) - 0.45, -0.55)
        ax.set_xlim(left=0)

    exp = read_table(output, "exploration")
    exp = exp[exp.issue_year.eq(ALL_YEARS)].set_index("depth_band")
    bands = [*present_bands, ALL]
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 5.8))
    fig.subplots_adjust(left=0.16, right=0.94, top=0.72, bottom=0.23, wspace=0.63)
    heading(
        fig,
        "From lease to first exploratory spud",
        f"Gulf leases effective in 2005 to 2020, observed through the {bore_cutoff:%B %Y} borehole file.",
    )
    a.set_title(
        "Share with an exploratory well", loc="left", fontsize=12, weight="bold"
    )
    b.set_title(
        "Years to the first exploratory well", loc="left", fontsize=12, weight="bold"
    )
    for i, band in enumerate(bands):
        row = exp.loc[band]
        c = TEAL if band == ALL else BAND_COLORS[BANDS.index(band)]
        a.barh(i, row.share_pct, height=0.46, color=c)
        tick = INK if row.explored_within_five_years == row.explored_leases else "white"
        a.plot(
            row.five_year_share_pct,
            i,
            "|",
            color=tick,
            ms=12,
            markeredgewidth=2,
        )
        a.text(
            row.share_pct + 0.15, i, f"{row.share_pct:.1f}%", va="center", fontsize=9
        )
        if row.timed_leases:
            b.plot(
                [
                    row.days_to_spud_p25 / DAYS_PER_YEAR,
                    row.days_to_spud_p75 / DAYS_PER_YEAR,
                ],
                [i, i],
                color=c,
                lw=3,
                solid_capstyle="round",
            )
            b.plot(row.days_to_spud_median / DAYS_PER_YEAR, i, "o", color=c, ms=7)
    labels_and_axis(a, bands)
    labels_and_axis(b, bands)
    b.tick_params(labelleft=False)
    a.set_xlim(0, exp.loc[bands].share_pct.max() * 1.32)
    b.set_xlim(0, exp.loc[bands].days_to_spud_p75.max() / DAYS_PER_YEAR * 1.08)
    a.set_xlabel("Percent of all leases in band")
    b.set_xlabel("Years since lease effective date")
    fig.text(
        0.045,
        0.085,
        "Bars show the observed share. Ticks mark the five-year share. Dots and lines show the median and middle 50%.",
        fontsize=9,
    )
    fig.text(
        0.045,
        0.045,
        "Medians use observed spuds and are biased low by leases still open without a spud. Sources: BSEE boreholes and LSETAPE.",
        fontsize=9,
    )
    save(fig, "exploration")

    site = read_table(output, "exploration_site_depth")
    site = site[site.timed_leases.gt(0)]
    fig, ax = plt.subplots(figsize=(9.5, 5.4))
    fig.subplots_adjust(left=0.18, right=0.92, top=0.72, bottom=0.23)
    heading(
        fig,
        "Time to spud by well-site water depth",
        "One first exploratory spud per lease effective in 2005 to 2020. Depth is measured at the borehole.",
    )
    for i, row in enumerate(site.itertuples(index=False)):
        color = (
            TEAL if row.depth_band == ALL else BAND_COLORS[BANDS.index(row.depth_band)]
        )
        ax.plot(
            [
                row.days_to_spud_p25 / DAYS_PER_YEAR,
                row.days_to_spud_p75 / DAYS_PER_YEAR,
            ],
            [i, i],
            color=color,
            lw=3,
        )
        ax.plot(row.days_to_spud_median / DAYS_PER_YEAR, i, "o", color=color, ms=7)
    labels_and_axis(ax, site.depth_band.tolist())
    ax.set_xlabel("Years from lease effective date to first exploratory spud")
    fig.text(
        0.045,
        0.08,
        "Dots and lines show the median and middle 50% among observed spuds.",
        fontsize=9,
    )
    fig.text(
        0.045,
        0.04,
        "Medians are biased low by leases still open without a spud. Sources: BSEE boreholes and LSETAPE.",
        fontsize=9,
    )
    save(fig, "exploration_site_depth")

    prod = read_table(output, "first_production")
    prod = prod.loc[prod.period.eq(MATURE_TOTAL)].set_index(["depth_band", "event"])
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 6.1))
    fig.subplots_adjust(left=0.16, right=0.95, top=0.70, bottom=0.24, wspace=0.58)
    heading(
        fig,
        "From lease to first oil and first production",
        "Leases effective in 2005 to 2020. Each lease contributes its first 60 reporting months.",
    )
    a.set_title("Elapsed time", loc="left", fontsize=12, weight="bold")
    b.set_title("Original primary term elapsed", loc="left", fontsize=12, weight="bold")
    for ax, metric, label, divisor in [
        (a, "months", "Elapsed years", 12),
        (b, "primary_term_pct", "Percent of original term", 1),
    ]:
        for i, band in enumerate(bands):
            for event, offset, c, marker in [
                ("Crude oil", -0.12, TEAL, "o"),
                ("Any hydrocarbon", 0.12, GREY, "s"),
            ]:
                row = prod.loc[(band, event)]
                med = row[metric + "_median"] / divisor
                if pd.notna(med):
                    ax.plot(
                        [
                            row[metric + "_p25"] / divisor,
                            row[metric + "_p75"] / divisor,
                        ],
                        [i + offset] * 2,
                        color=c,
                        lw=2,
                    )
                    ax.plot(med, i + offset, marker, color=c, ms=6)
        labels_and_axis(ax, bands)
        ax.set_xlabel(label)
    b.tick_params(labelleft=False)
    a.legend(
        handles=[
            plt.Line2D([], [], color=TEAL, marker="o", label="Crude oil"),
            plt.Line2D([], [], color=GREY, marker="s", label="Any hydrocarbon"),
        ],
        loc="upper left",
        bbox_to_anchor=(0, -0.18),
        ncol=2,
        frameon=False,
    )
    fig.text(
        0.045,
        0.072,
        "Markers and lines show the median and middle 50% among observed events. Elapsed time includes suspension.",
        fontsize=9,
    )
    fig.text(
        0.045,
        0.035,
        "Medians describe only leases reaching the event within five years. Sources: BSEE monthly lease production and LSETAPE.",
        fontsize=9,
    )
    save(fig, "first_production")


def coverage_table(frame, lm, bm, pm, om, pooled_bounds):
    rows = []

    def fact(metric, value, source, meaning):
        text = value if isinstance(value, str) else None
        number = None if isinstance(value, str) else int(value)
        rows.append(
            {
                "metric": metric,
                "number": number,
                "text": text,
                "source": source,
                "meaning": meaning,
            }
        )

    for key, meaning in [
        ("tape_file_date", "LSETAPE.DAT member date in the supplied ZIP"),
        ("first_effective_date", "Earliest cohort effective date"),
        ("last_effective_date", "Latest cohort effective date"),
        (
            "straddling_ranges",
            "Block minimum and maximum lie in different series bands",
        ),
        ("missing_ranges", "At least one block-depth endpoint missing"),
        ("invalid_ranges", "Inconsistent block-depth range"),
        ("no_sale_number", "Cohort leases without sale number"),
        (
            "suspensions_with_ordered_dates",
            "Cohort leases with a recorded start and end in order",
        ),
        (
            "primary_term_missing_or_nonpositive",
            "Cohort leases without a positive original primary term",
        ),
        (
            "tape_first_production_date_present",
            "Cohort leases with LSETAPE first continuous production date",
        ),
    ]:
        fact(key, lm[key], "LSETAPE.DAT", meaning)
    for key, meaning in [
        ("compared_block_depths", "Lease maxima comparable in both sources"),
        (
            "depths_within_one_metre",
            "Converted tape maxima within one metre of the published whole-metre field",
        ),
    ]:
        fact(key, lm[key], "LSETAPE.DAT + mv_production_waterdepth.txt", meaning)
    fact(
        "unmapped_status_codes",
        ", ".join(lm["undocumented_status_codes"]),
        "LSETAPE.DAT + lease-fields.md",
        "Tape codes lacking exact local glossary entries",
    )
    for key, meaning in [
        ("last_gulf_spud", "Latest dated, valid Gulf bore in file"),
        (
            "pre_effective_e_bores_2005_2026",
            "E bore records on a cohort lease dated before effective date",
        ),
        (
            "tied_first_spud_conflicting_cohort_lease_api10s",
            "API10s touching a cohort lease with conflicting bottom leases at first spud",
        ),
        (
            "tied_first_spud_conflicting_cohort_type_api10s",
            "API10s touching a cohort lease with conflicting types at first spud",
        ),
    ]:
        fact(key, bm[key], "mv_boreholes_all.txt", meaning)
    for code, value in bm["undated_e_bores_by_status_2005_2020"].items():
        fact(
            "undated_e_" + code,
            value,
            "mv_boreholes_all.txt",
            f"2005 to 2020 cohort E listings without dated spud, status {code}",
        )
    for key, meaning in [
        ("first_source_month", "Earliest year-month in production detail"),
        ("last_source_month", "Latest year-month in production detail"),
        ("last_source_month_rows", "All detail rows in the terminal production month"),
        ("source_rows", "All detail rows, including zero-volume reports"),
        (
            "production_before_effective_month",
            "Cohort first hydrocarbon month precedes effective month",
        ),
        (
            "oil_before_effective_month",
            "Cohort first crude month precedes effective month",
        ),
    ]:
        fact(key, pm[key], "mv_productiondata.txt", meaning)
    has_month = frame.first_production_month.notna()
    has_tape = frame.lease_first_production_date.notna()
    for key, condition in [
        ("continuous_date_without_positive_month", has_tape & ~has_month),
        ("positive_month_without_continuous_date", has_month & ~has_tape),
    ]:
        fact(
            key,
            condition.sum(),
            "LSETAPE.DAT + mv_productiondata.txt",
            "Difference between continuous commercial production and positive reported monthly volume",
        )
    for code, n in om["source_status_counts"].items():
        fact(
            "owner_status_" + code,
            n,
            "mv_lease_owners_main.txt",
            f"All assignment rows with status {code}",
        )
    for key, meaning in [
        ("termination_dates_present", "All ownership rows with a termination date"),
        (
            "missing_assignment_effective_dates",
            "All ownership rows lacking an assignment effective date",
        ),
        (
            "cohort_current_companies",
            "Distinct listed current company IDs matched to cohort at snapshot",
        ),
        (
            "cohort_current_leases",
            "Distinct cohort leases with at least one current assignment",
        ),
    ]:
        fact(key, om[key], "mv_lease_owners_main.txt", meaning)
    for key, metric, meaning in [
        ("overlap", "both_endpoints", "Dated bottom and surface matches"),
        (
            "extra",
            "additional_any_date",
            "Additional leases when the date rule is removed",
        ),
        (
            "earlier_only",
            "earlier_only",
            "Additional leases with only pre-effective spuds",
        ),
        (
            "missing_only",
            "undated_only",
            "Additional leases with only undated listings",
        ),
    ]:
        fact(
            "bounds_" + metric,
            pooled_bounds[key],
            "LSETAPE.DAT + mv_boreholes_all.txt",
            f"{meaning}, any bore type, leases effective in 2005 to 2020",
        )
    return pd.DataFrame(rows)


def build_numbers(tables):
    numbers = {}

    def add(key, table, filt, column, unit):
        v = select_one(tables[table], filt)[column]
        if isinstance(v, np.generic):
            v = v.item()
        if pd.isna(v):
            v = None
        elif isinstance(v, float) and v.is_integer():
            v = int(v)
        numbers[key] = {
            "value": v,
            "unit": unit,
            "table": table + ".csv",
            "filter": filt,
            "column": column,
        }

    def add_fields(prefix, table, filt, cols):
        for col, unit in cols.items():
            add(f"{prefix}.{col}", table, filt, col, unit)

    issued = tables["issuance"]
    overall = {"issue_year": ALL_YEARS, "depth_band": ALL}
    add("issued_total", "issuance", overall, "leases", "leases")
    annual = issued[issued.depth_band.eq(ALL) & issued.issue_year.ne(ALL_YEARS)]
    peak = annual.loc[annual.leases.idxmax()]
    for year in [peak.issue_year, "2025", "2026"]:
        sel = {"issue_year": year, "depth_band": ALL}
        add("issued_" + year, "issuance", sel, "leases", "leases")
    add(
        "peak_effective_year",
        "issuance",
        {"issue_year": peak.issue_year, "depth_band": ALL},
        "issue_year",
        "calendar year",
    )
    for code in tables["current_status"].status_code.unique():
        add_fields(
            "status." + code,
            "current_status",
            {**overall, "status_code": code},
            {"leases": "leases", "share_pct": "%"},
        )
    for b, slug in zip(
        [*BANDS, ALL],
        ["under_100", "100_to_500", "500_to_1500", "1500_plus", "unknown", "all"],
    ):
        filt = {"issue_year": ALL_YEARS, "depth_band": b}
        add("issued." + slug, "issuance", filt, "leases", "leases")
        add_fields(
            "exploration." + slug,
            "exploration",
            filt,
            {
                "leases": "leases",
                "explored_leases": "leases",
                "primry_sop_operns_without_event": "leases",
                "prod_without_event": "leases",
                "unit_without_event": "leases",
                "open_without_observed_event": "leases",
                "exploration_wells": "API10 wells",
                "share_pct": "%",
                "leases_with_any_e_bore": "leases",
                "any_e_bore_share_pct": "%",
                "explored_within_five_years": "leases",
                "five_year_share_pct": "%",
                "days_to_spud_p25": "days",
                "days_to_spud_median": "days",
                "days_to_spud_p75": "days",
                "days_to_any_e_bore_p25": "days",
                "days_to_any_e_bore_median": "days",
                "days_to_any_e_bore_p75": "days",
            },
        )
        add_fields(
            "well_site." + slug,
            "exploration_site_depth",
            {"depth_band": b},
            {
                "timed_leases": "leases",
                "days_to_spud_p25": "days",
                "days_to_spud_median": "days",
                "days_to_spud_p75": "days",
            },
        )
        for event, kind in [("Crude oil", "oil"), ("Any hydrocarbon", "hydrocarbon")]:
            add_fields(
                f"{kind}.{slug}",
                "first_production",
                {"period": MATURE_TOTAL, "depth_band": b, "event": event},
                {
                    "leases": "leases",
                    "share_pct": "%",
                    "median_years": "years",
                    "after_window_leases": "leases",
                    "observed_leases": "leases",
                    "timed_leases": "leases",
                    "without_observed_event": "leases",
                    "primry_sop_operns_without_event": "leases",
                    "prod_without_event": "leases",
                    "unit_without_event": "leases",
                    "open_without_observed_event": "leases",
                    "term_leases": "leases",
                    "over_term_leases": "leases",
                    "months_p25": "months",
                    "months_median": "months",
                    "months_p75": "months",
                    "primary_term_pct_p25": "%",
                    "primary_term_pct_median": "%",
                    "primary_term_pct_p75": "%",
                },
            )
    for key in ("a", "b", "c", "d", "e"):
        fields = {"matched_leases": "leases"}
        if key in ("c", "d", "e"):
            fields["share_pct"] = "%"
        add_fields(
            f"bounds.{key}",
            "lease_match_bounds",
            {"cohort": "2005 to 2020", "band": "All", "variant": BOUND_VARIANTS[key]},
            fields,
        )
    for row in tables["coverage"].itertuples(index=False):
        col = "text" if pd.isna(row.number) else "number"
        add(
            "coverage." + row.metric,
            "coverage",
            {"metric": row.metric},
            col,
            "source text" if col == "text" else "count",
        )
    for _, row in tables["record_counts"].iterrows():
        for col, n in row.items():
            if not (
                col.startswith("rows_") or (col.startswith(("drop__", "flag__")) and n)
            ):
                continue
            add(
                f"audit.{row.stage}.{col}",
                "record_counts",
                {"stage": row.stage},
                col,
                "records at this stage",
            )
    return numbers


def validate_figures(charts):
    from PIL import Image

    for stem in (
        "issuance",
        "current_status",
        "exploration",
        "exploration_site_depth",
        "first_production",
    ):
        svg = (charts / f"{stem}.svg").read_text(encoding="utf-8")
        root = ET.fromstring(svg)
        tags = {node.tag.rsplit("}", 1)[-1] for node in root.iter()}
        require(
            not tags.intersection({"pattern", "clipPath", "filter", "mask"})
            and "clip-path" not in svg,
            f"Prohibited SVG element or clip-path in {stem}",
        )
        require(
            "text" in tags and "DejaVu Sans" in svg, f"SVG typography missing in {stem}"
        )
        with Image.open(charts / f"{stem}.png") as image:
            require(
                image.format == "PNG" and image.width > 1000 and image.height > 600,
                f"Invalid PNG: {stem}",
            )
            image.load()


def compare_quartiles(values, row, prefix):
    actual = np.array(
        [row[prefix + "_p25"], row[prefix + "_median"], row[prefix + "_p75"]],
        dtype=float,
    )
    sample = values.dropna()
    expected = (
        np.percentile(sample, [25, 50, 75]) if len(sample) else np.full(3, np.nan)
    )
    require(
        np.allclose(expected, actual, equal_nan=True, rtol=0, atol=1e-10),
        f"Quartiles disagree for {prefix}, {row['depth_band']}",
    )


def validate_site_quantiles(table, durations):
    for band in [*BANDS, ALL]:
        row = select_one(table, {"depth_band": band})
        days = (
            durations.days
            if band == ALL
            else durations.loc[durations.depth_band.eq(band), "days"]
        )
        require(
            row.timed_leases == len(days), f"Well-site timing count differs for {band}"
        )
        compare_quartiles(days, row, "days_to_spud")


def validate_quantiles(tables, older):
    """Recompute order statistics from individual leases after CSV round-trip."""

    for row in tables["exploration"].to_dict("records"):
        g = older
        if row["issue_year"] != ALL_YEARS:
            g = g[g.issue_year.eq(int(row["issue_year"]))]
        if row["depth_band"] != ALL:
            g = g[g.depth_band.eq(row["depth_band"])]
        compare_quartiles(
            (g.exploration_spud - g.effective_date).dt.days, row, "days_to_spud"
        )
        compare_quartiles(
            (g.any_e_bore_spud - g.effective_date).dt.days, row, "days_to_any_e_bore"
        )
    cohorts = dict(period_groups(older))
    for row in tables["first_production"].to_dict("records"):
        g = cohorts[row["period"]]
        if row["depth_band"] != ALL:
            g = g.loc[g.depth_band.eq(row["depth_band"])]
        months = month_lag(g.effective_date, g[EVENTS[row["event"]]])
        months = months[months.between(0, WINDOW_MONTHS - 1)]
        require(
            row["leases"] == len(g)
            and row["timed_leases"] == len(months)
            and np.isclose(row["share_pct"], pct(len(months), len(g)), equal_nan=True),
            "Window incidence differs from the individual lease dates",
        )
        compare_quartiles(months, row, "months")
        compare_quartiles(
            100
            * months
            / (12 * g.primary_term_years.where(g.primary_term_years.gt(0))),
            row,
            "primary_term_pct",
        )


def validate_numbers(numbers, tables):
    for key, claim in numbers.items():
        table = tables[Path(claim["table"]).stem]
        observed = select_one(table, claim["filter"])[claim["column"]]
        value = claim["value"]
        if value is None:
            require(pd.isna(observed), f"Missing headline differs: {key}")
        else:
            require(observed == value, f"Headline differs: {key}")


def build(output, data_dir, pins, check):
    from bore_basis import read_bores, site_spud_table
    from bound_check import calculate_bounds
    from lease_basis import read_leases, read_owners
    from oil_basis import read_production

    leases, la, lm = read_leases(data_dir / TAPE, REPOSITORY)
    check(
        "Every lease in this cohort took effect on the first of a month",
        lambda: require(
            leases.effective_date.dt.is_month_start.all(),
            "Monthly production cannot resolve the term boundary of a mid-month lease",
        ),
    )
    comparison, da = check(
        "Converted LSETAPE depth scale agrees with BSEE's whole-metre lease lookup within one metre",
        lambda: compare_native_depths(leases, data_dir / PRODUCTION),
    )
    lm.update(comparison)
    with ZipFile(data_dir / TAPE) as archive:
        lm["tape_file_date"] = (
            pd.Timestamp(*archive.getinfo("LSETAPE.DAT").date_time[:3])
            .date()
            .isoformat()
        )
    leases["depth_band"] = depth_band(leases.lease_depth_m)
    as_of = pd.Timestamp(pins[BORE]["collection_end_utc"]).date()
    b, wells, ba, bm = read_bores(data_dir / BORE, leases, as_of)
    p, pa, pm = read_production(data_dir / PRODUCTION, leases)
    _, oa, om = read_owners(data_dir / OWNERS, leases, REPOSITORY)
    f = leases.merge(b, on="lease_id", how="left", validate="one_to_one").merge(
        p, on="lease_id", how="left", validate="one_to_one"
    )
    check(
        "Joins preserve every cohort lease and all exploration denominators",
        lambda: require(
            len(f) == len(leases)
            and f.lease_id.is_unique
            and f.exploration_wells.notna().all(),
            "Join changed cohort",
        ),
    )
    older = f[f.issue_year.between(COHORT_START, COHORT_END)]
    older_audit = {
        "stage": "Exploration cohort effective through 2020",
        "read": len(f),
        "kept": len(older),
        "drops": {"issued_after_2020": int(f.issue_year.gt(2020).sum())},
    }
    check(
        "All 2005 to 2020 leases reach their fifth anniversary by the last observed Gulf spud",
        lambda: require(
            (
                older.effective_date + pd.DateOffset(years=FOLLOWUP_YEARS)
                <= pd.Timestamp(bm["last_gulf_spud"])
            ).all(),
            "Unequal five-year horizon",
        ),
    )
    months = (
        pd.period_range("2005-01", pm["last_source_month"], freq="M")
        .astype(str)
        .tolist()
    )
    check(
        "Production detail has every calendar month from 2005-01 through the reported cutoff",
        lambda: require(
            months == pm["source_months_from_2005"], "Gap in production month coverage"
        ),
    )
    site, sa, site_durations = site_spud_table(older, wells, depth_band, BANDS)
    production = check(
        "All leases effective in 2005 to 2020 have 60 reporting months from month 0 through month 59",
        lambda: production_table(
            f, audits=pa, last_source_month=pm["last_source_month"]
        ),
    )
    source_tables = {
        "issuance": issue_table(f),
        "current_status": status_table(f),
        "exploration": exploration_table(older),
        "exploration_site_depth": site,
        "first_production": production,
        "record_counts": audit_table([*la, older_audit, *da, *ba, *sa, *pa, *oa]),
    }
    for stem, df in source_tables.items():
        df.to_csv(output / f"{stem}.csv", index=False, lineterminator="\n")
    tables = {stem: read_table(output, stem) for stem in source_tables}
    counts = calculate_bounds(data_dir, pins, output / "exploration.csv")
    tables["lease_match_bounds"] = write_lease_match_bounds(output, check, counts)
    coverage = coverage_table(f, lm, bm, pm, om, counts[ALL_YEARS, ALL])
    coverage.to_csv(output / "coverage.csv", index=False, lineterminator="\n")
    tables["coverage"] = read_table(output, "coverage")
    check(
        "Issuance counts reconcile for every band and year to distinct source leases",
        lambda: validate_issues(tables["issuance"], f),
    )
    check(
        "Every current-status code reconciles by band and year; shares use the full cohort",
        lambda: validate_status(tables["current_status"], f),
    )
    check(
        "Every assigned API10 is unique and counted in exactly one lease depth band",
        lambda: validate_wells(wells, f),
    )
    check(
        "Exploration counts reconcile across bands, years, unique wells and all cohort leases",
        lambda: validate_exploration(tables["exploration"], older, wells),
    )

    def check_site():
        table = tables["exploration_site_depth"]
        validate_site_quantiles(table, site_durations)
        grand = select_one(table, {"depth_band": ALL})
        block = select_one(
            tables["exploration"], {"depth_band": ALL, "issue_year": ALL_YEARS}
        )
        require(
            table.depth_band.is_unique
            and set(table.depth_band) == {*BANDS, ALL}
            and table.loc[table.depth_band.ne(ALL), "timed_leases"].sum()
            == grand.timed_leases,
            "Well-site depth bands do not sum to the inclusive all-band sample",
        )
        for col in [
            "timed_leases",
            "days_to_spud_p25",
            "days_to_spud_median",
            "days_to_spud_p75",
        ]:
            require(
                np.isclose(grand[col], block[col]),
                "Site and block summaries cover different events",
            )

    check(
        "Site counts and quartiles match individual durations in each assigned band, and pooled timing matches block timing",
        check_site,
    )
    check(
        "Production, timing and primary-term sample counts reconcile for each event across bands",
        lambda: validate_production(tables["first_production"], older),
    )
    check(
        "Median and middle half in every timing row match individual lease durations and ratios",
        lambda: validate_quantiles(tables, older),
    )
    check(
        "Every stage reconciles read, kept and dropped rows; downstream reads equal upstream retained rows",
        lambda: validate_audit(tables["record_counts"]),
    )
    numbers = build_numbers(tables)
    number_path = output / "numbers.json"
    number_path.write_text(
        json.dumps(numbers, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    check(
        "Every headline value resolves to exactly one saved CSV row and column",
        lambda: validate_numbers(json.loads(number_path.read_bytes()), tables),
    )
    from lease_trends import write_trends

    check(
        "Five trend figures and writer citations resolve to saved table cells",
        lambda: write_trends(output, f, older, tables),
    )
    draw_charts(output, lm["last_effective_date"], as_of)
    check(
        "All five SVG/PNG pairs decode; SVGs use DejaVu Sans and contain no prohibited constructs",
        lambda: validate_figures(output),
    )
