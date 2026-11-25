"""Well spuds from the BSEE dated borehole archive at the API10 grain.

Field and type semantics follow worldenergydata's BSEE wells/borehole-fields.md
and wells/type-codes.md. Bottom-lease attribution follows its
borehole_lease_reconciliation.py. The existing headered borehole acquirer's
normalized view drops REGION_CODE; read its documented raw member with string
identifiers to retain region and audit raw records.
"""

from zipfile import ZipFile

import pandas as pd

MEMBER = "BoreholeRawData/mv_boreholes_all.txt"
FIELDS = {
    "API_WELL_NUMBER": "api12",
    "BOTM_LEASE_NUMBER": "lease_id",
    "WELL_TYPE_CODE": "well_type",
    "WELL_SPUD_DATE": "spud_text",
    "REGION_CODE": "region",
    "WATER_DEPTH": "depth_ft",
    "BOREHOLE_STAT_CD": "status",
}


def _select(frame, stage, conditions, audits):
    """Apply disjoint, ordered exclusion reasons, counting survivors directly."""
    available = pd.Series(True, index=frame.index)
    drops = {}
    for reason, mask in conditions.items():
        reject = available & mask
        drops[reason] = int(reject.sum())
        available &= ~reject
    kept = frame.loc[available].copy()
    audits.append(
        {"stage": stage, "read": len(frame), "kept": len(kept), "drops": drops}
    )
    return kept


def read_bores(zip_path, leases, as_of):
    """Return lease summaries, unique assigned API10s, row audits and coverage.

    The main event is a new exploratory well spudded during the lease. The
    sensitivity counts leases reached by any E bore, including later branches.
    Both outcomes use exact bottom lease, require a dated spud, and reject dates
    before the effective date. No lease-expiration adjustment is made.
    """
    as_of = pd.Timestamp(as_of).normalize()
    cohort = leases.set_index("lease_id", verify_integrity=True)
    effective = pd.to_datetime(cohort["effective_date"], errors="raise")
    if effective.isna().any():
        raise ValueError("Borehole join requires a lease effective date")

    with ZipFile(zip_path) as archive, archive.open(MEMBER) as source:
        raw = pd.read_csv(
            source, usecols=list(FIELDS), dtype=str, keep_default_na=False
        )
    raw = raw.rename(columns=FIELDS).apply(lambda col: col.str.strip())
    raw["spud"] = pd.to_datetime(
        raw["spud_text"].replace("", pd.NA), format="%m/%d/%Y", errors="raise"
    )
    raw["depth_ft"] = pd.to_numeric(raw["depth_ft"].replace("", pd.NA), errors="raise")
    raw["depth_ft"] = raw["depth_ft"].where(raw["depth_ft"].gt(0))
    valid_api = raw["api12"].str.fullmatch(r"[0-9]{12}")
    if raw.loc[valid_api, "api12"].duplicated().any():
        raise ValueError("Duplicate API12 in borehole source")

    audits = []
    gulf = raw["region"].eq("G")
    undated = raw["spud"].isna()
    dated = _select(
        raw,
        "BoreholeRawData, dated Gulf bore records",
        {
            "other_region": ~gulf,
            "invalid_api12": ~valid_api,
            "undated_cancelled": undated & raw["status"].eq("CNL"),
            "undated_permit_or_approved_sidetrack": undated
            & raw["status"].isin(["APD", "AST"]),
            "undated_other": undated,
            "spud_after_snapshot": raw["spud"].gt(as_of),
        },
        audits,
    )
    dated["api10"] = dated["api12"].str[:10]

    # Determine the original spud across all available Gulf bores before
    # matching a cohort. A sidetrack onto the lease cannot create a new well.
    first_spuds = dated.groupby("api10")["spud"].transform("min")
    initial = _select(
        dated,
        "Dated Gulf bore records at earliest API10 spud",
        {
            "later_bore_of_same_api10": dated["spud"].ne(first_spuds),
        },
        audits,
    )
    candidates = initial.groupby("api10", as_index=False).agg(
        spud=("spud", "first"),
        lease_id=("lease_id", "first"),
        well_type=("well_type", "first"),
        depth_ft=("depth_ft", "median"),
        depth_min_ft=("depth_ft", "min"),
        depth_max_ft=("depth_ft", "max"),
        measured_bores=("depth_ft", "count"),
        initial_bores=("api12", "size"),
        lease_values=("lease_id", "nunique"),
        type_values=("well_type", "nunique"),
    )
    candidates["incomplete_site_depth"] = candidates["measured_bores"].lt(
        candidates["initial_bores"]
    )
    audits.append(
        {
            "stage": "Earliest-spud bore records grouped into distinct Gulf API10s",
            "read": len(initial),
            "kept": len(candidates),
            "drops": {
                "additional_bore_on_same_well_spud_date": int(
                    initial["api10"].duplicated().sum()
                )
            },
        }
    )
    candidates["effective"] = candidates["lease_id"].map(effective)
    wells = _select(
        candidates,
        "Original-spud API10s attributable to effective cohort leases",
        {
            "conflicting_bottom_leases_at_first_spud": candidates["lease_values"].gt(1),
            "conflicting_types_at_first_spud": candidates["type_values"].gt(1),
            "missing_bottom_lease": candidates["lease_id"].eq(""),
            "bottom_lease_outside_cohort": candidates["effective"].isna(),
            "well_spud_before_lease_effective": candidates["spud"].lt(
                candidates["effective"]
            ),
        },
        audits,
    )
    wells = wells[
        [
            "api10",
            "lease_id",
            "well_type",
            "spud",
            "depth_ft",
            "depth_min_ft",
            "depth_max_ft",
            "incomplete_site_depth",
        ]
    ]
    exploratory = _select(
        wells,
        "Cohort API10s originally spudded as exploratory",
        {
            "first_spud_not_type_E": wells["well_type"].ne("E"),
        },
        audits,
    )

    # Lease incidence at API12 bottom is a sensitivity. Only leases are
    # counted in these results. A later E sidetrack can reach a different lease.
    dated["effective"] = dated["lease_id"].map(effective)
    e_bores = _select(
        dated,
        "All dated Gulf bores for E-bore lease sensitivity",
        {
            "not_exploratory": dated["well_type"].ne("E"),
            "bottom_lease_outside_cohort": dated["effective"].isna(),
            "bore_spud_before_lease_effective": dated["spud"].lt(dated["effective"]),
        },
        audits,
    )
    summary = pd.DataFrame(index=cohort.index)
    by_lease = exploratory.groupby("lease_id")
    summary["exploration_spud"] = by_lease["spud"].min()
    summary["exploration_wells"] = (
        by_lease["api10"].nunique().reindex(cohort.index, fill_value=0)
    )
    summary["any_e_bore_spud"] = e_bores.groupby("lease_id")["spud"].min()
    summary["has_any_e_bore"] = summary["any_e_bore_spud"].notna()
    if (summary["exploration_spud"].notna() & ~summary["has_any_e_bore"]).any():
        raise ValueError("Exploration well missing from the E-bore sensitivity")
    if (
        len(exploratory) != summary["exploration_wells"].sum()
        or not wells["api10"].is_unique
    ):
        raise ValueError(
            "API10 exploration assignments do not reconcile to lease totals"
        )
    eligible = effective.dt.year.between(2005, 2020)
    candidate_e = (
        gulf & valid_api & raw["well_type"].eq("E") & raw["lease_id"].isin(cohort.index)
    )
    all_unspudded = raw.loc[candidate_e & undated]
    analysis_unspudded = all_unspudded[
        all_unspudded["lease_id"].isin(effective.index[eligible])
    ]
    diagnostics = {
        "last_gulf_spud": dated["spud"].max().date().isoformat()
        if len(dated)
        else None,
        "undated_e_bores_by_status_2005_2026": all_unspudded["status"]
        .value_counts()
        .to_dict(),
        "undated_e_bores_by_status_2005_2020": analysis_unspudded["status"]
        .value_counts()
        .to_dict(),
        "pre_effective_e_bores_2005_2026": int(
            (candidate_e & raw["spud"].lt(raw["lease_id"].map(effective))).sum()
        ),
        "tied_first_spud_conflicting_cohort_lease_api10s": int(
            initial.loc[
                initial["lease_id"].isin(cohort.index)
                & initial["api10"].isin(
                    candidates.loc[candidates["lease_values"].gt(1), "api10"]
                ),
                "api10",
            ].nunique()
        ),
        "tied_first_spud_conflicting_cohort_type_api10s": int(
            initial.loc[
                initial["lease_id"].isin(cohort.index)
                & initial["api10"].isin(
                    candidates.loc[candidates["type_values"].gt(1), "api10"]
                ),
                "api10",
            ].nunique()
        ),
        "any_e_bore_leases_2005_2020": int(
            summary.loc[eligible, "has_any_e_bore"].sum()
        ),
        "original_e_spud_leases_2005_2020": int(
            summary.loc[eligible, "exploration_spud"].notna().sum()
        ),
    }
    return summary.reset_index(), wells, audits, diagnostics


def site_spud_table(leases, assignments, band_fn, bands):
    """Time each explored lease once, grouped by depth at its first E well(s)."""
    if not assignments["api10"].is_unique:
        raise ValueError(
            "Well-site timing requires a unique original-spud assignment for every API10"
        )
    cohort = leases.set_index("lease_id", verify_integrity=True)
    effective = pd.to_datetime(cohort["effective_date"])
    in_window = effective.dt.year.between(2005, 2020)
    audits = []
    wells = _select(
        assignments,
        "Original-spud API10s for well-site exploration timing",
        {
            "not_exploratory": assignments["well_type"].ne("E"),
            "outside_2005_2020_lease_cohort": ~assignments["lease_id"].isin(
                cohort.index[in_window]
            ),
        },
        audits,
    )
    earliest = wells.groupby("lease_id")["spud"].transform("min")
    first = _select(
        wells,
        "First exploration spud on each lease at measured well site",
        {
            "later_exploration_well_on_same_lease": wells["spud"].ne(earliest),
        },
        audits,
    )
    # A unique band requires agreement across every bore row tied at the
    # original spud and every API10 tied at the first E spud on that lease.
    # A midpoint or a median could put an ambiguous site in a known band.
    low = band_fn(first["depth_min_ft"] * 0.3048)
    high = band_fn(first["depth_max_ft"] * 0.3048)
    first["site_band"] = low
    first["known_well_band"] = (
        low.eq(high) & low.ne("Unknown") & ~first["incomplete_site_depth"]
    )
    first["has_depth"] = first["depth_max_ft"].notna()
    sites = first.groupby("lease_id").agg(
        spud=("spud", "first"),
        depth_band=("site_band", "first"),
        distinct_bands=("site_band", "nunique"),
        all_known=("known_well_band", "all"),
        any_depth=("has_depth", "any"),
    )
    audits.append(
        {
            "stage": "First-spud exploratory API10s grouped into distinct timed leases",
            "read": len(first),
            "kept": len(sites),
            "drops": {
                "another_well_at_same_first_spud": int(
                    first["lease_id"].duplicated().sum()
                )
            },
        }
    )
    ambiguous = ~sites["all_known"] | sites["distinct_bands"].gt(1)
    sites.loc[ambiguous, "depth_band"] = "Unknown"
    _select(
        sites,
        "Timed leases with a resolved measured site band",
        {
            "missing_site_depth": ~sites["any_depth"],
            "ambiguous_site_band": ambiguous,
        },
        audits,
    )
    sites["days"] = (sites["spud"] - effective.reindex(sites.index)).dt.days
    if sites["days"].isna().any() or sites["days"].lt(0).any():
        raise ValueError(
            "Missing or pre-effective original E event in well-site timing"
        )
    if "exploration_spud" in cohort:
        expected = cohort.loc[in_window, "exploration_spud"].dropna().sort_index()
        actual = sites["spud"].sort_index()
        if not actual.index.equals(expected.index) or not actual.eq(expected).all():
            raise ValueError(
                "Block-band and well-site series select different lease first spuds"
            )
    rows = []
    for band in [*bands, "All bands"]:
        days = (
            sites["days"]
            if band == "All bands"
            else sites.loc[sites["depth_band"].eq(band), "days"]
        )
        p25, median, p75 = days.quantile([0.25, 0.5, 0.75])
        rows.append(
            {
                "depth_band": band,
                "timed_leases": len(days),
                "days_to_spud_p25": p25,
                "days_to_spud_median": median,
                "days_to_spud_p75": p75,
            }
        )
    return pd.DataFrame(rows), audits
