# ABOUTME: DRILLING_DAYS in the enrichment engine must come from the shared
# ABOUTME: WAR rig-days module at API12 grain, never from a calendar span (#1075).
"""Behavioural tests for ``ActivityEnrichmentEngine`` drilling days.

These assert *what the number means*, not how it is computed: that it is WAR
rig time rather than a spud-to-TD calendar span, that it is keyed on the
wellbore (API12) rather than the well (API10), and that absent WAR coverage
surfaces as null rather than as a zero-day well.
"""

from __future__ import annotations

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.intervention.enrichment_engine import (
    SOURCE_DIRECT,
    SOURCE_SN_WAR_JOIN,
    SOURCE_UNAVAILABLE,
    STATUS_NO_DRILLING,
    ActivityEnrichmentEngine,
)
from worldenergydata.bsee.analysis.war_rig_days import (
    STATUS_COVERED,
    STATUS_NO_ACTIVITY,
)

FLEET = pd.DataFrame({"RIG_NAME": ["RIG A"], "RIG_TYPE": ["Drillship"]})


def _war_week(sn, api12, start, end, code):
    return {
        "SN_WAR": sn,
        "API_WELL_NUMBER": api12,
        "WAR_START_DT": start,
        "WAR_END_DT": end,
        "WELL_ACTIVITY_CD": code,
    }


def _war_rows(api12s):
    """WAR-main-shaped rows: the frame the engine is constructed with."""
    return pd.DataFrame(
        {
            "API_WELL_NUMBER": list(api12s),
            "RIG_NAME": ["RIG A"] * len(api12s),
            "WATER_DEPTH": [4000.0] * len(api12s),
            "WAR_START_DT": ["2020-01-05"] * len(api12s),
            "WAR_END_DT": ["2020-01-11"] * len(api12s),
        }
    )


def _borehole_rows(api12s, spud="2010-01-01", td="2020-12-31"):
    """Borehole frame whose calendar span is deliberately absurd (~4,000 days)."""
    return pd.DataFrame(
        {
            "API_WELL_NUMBER": list(api12s),
            "WELL_SPUD_DATE": [spud] * len(api12s),
            "TOTAL_DEPTH_DATE": [td] * len(api12s),
            "BH_TOTAL_MD": [25000.0] * len(api12s),
            "WATER_DEPTH": [4000.0] * len(api12s),
            "BOREHOLE_STAT_CD": ["COM"] * len(api12s),
            "WELL_NAME_SUFFIX": [""] * len(api12s),
        }
    )


def _enrich(war, borehole, activity, **kw):
    engine = ActivityEnrichmentEngine(
        war_df=war, fleet_df=FLEET, borehole_df=borehole, war_activity_df=activity, **kw
    )
    return engine, engine.enrich()


# -- Grain ------------------------------------------------------------------


def test_drilling_days_are_per_wellbore_not_per_well():
    """Two sidetracks of one well must keep their own, different day counts.

    If this path were rolled up to API10 both bores would carry the same
    number; the borehole frame is keyed on API12, so they must not.
    """
    api = ["608124009500", "608124009501"]
    activity = pd.DataFrame(
        [
            # bore ...00 drills two consecutive weeks -> 14 inclusive days
            _war_week(1, api[0], "2020-01-05", "2020-01-11", "DRL"),
            _war_week(2, api[0], "2020-01-12", "2020-01-18", "DRL"),
            # bore ...01 drills one week -> 7 days
            _war_week(3, api[1], "2020-03-01", "2020-03-07", "DRL"),
        ]
    )
    _, out = _enrich(_war_rows(api), _borehole_rows(api), activity)

    days = dict(zip(out["API_WELL_NUMBER"], out["DRILLING_DAYS"]))
    assert days[api[0]] == 14.0
    assert days[api[1]] == 7.0


def test_sidetrack_suffix_is_not_collapsed_to_the_parent_well():
    """A bore with no WAR activity stays null even when its sibling has days."""
    api = ["608124009500", "608124009501"]
    activity = pd.DataFrame([_war_week(1, api[0], "2020-01-05", "2020-01-11", "DRL")])
    _, out = _enrich(_war_rows(api), _borehole_rows(api), activity)

    days = dict(zip(out["API_WELL_NUMBER"], out["DRILLING_DAYS"]))
    assert days[api[0]] == 7.0
    assert pd.isna(days[api[1]])


# -- Basis: rig time, not calendar span -------------------------------------


def test_drilling_days_ignore_the_spud_to_td_calendar_span():
    """The regression the issue is about: a 4,000-day span must not survive."""
    api = ["608124009500"]
    activity = pd.DataFrame([_war_week(1, api[0], "2020-01-05", "2020-01-11", "DRL")])
    war, bh = _war_rows(api), _borehole_rows(api, spud="2010-01-01", td="2020-12-31")
    calendar_span = (pd.Timestamp("2020-12-31") - pd.Timestamp("2010-01-01")).days
    assert calendar_span > 3900  # the frame really is that pathological

    _, out = _enrich(war, bh, activity)
    assert out["DRILLING_DAYS"].iloc[0] == 7.0


def test_only_drilling_coded_weeks_count_towards_drilling_days():
    """Completion and workover weeks are rig time but are not drilling time."""
    api = ["608124009500"]
    activity = pd.DataFrame(
        [
            _war_week(1, api[0], "2020-01-05", "2020-01-11", "DRL"),
            _war_week(2, api[0], "2020-01-12", "2020-01-18", "COM"),
            _war_week(3, api[0], "2020-01-19", "2020-01-25", "WO"),
        ]
    )
    _, out = _enrich(_war_rows(api), _borehole_rows(api), activity)
    assert out["DRILLING_DAYS"].iloc[0] == 7.0


def test_covered_bore_with_no_drilling_week_is_null_not_zero():
    """In WAR, but no drilling-coded week.

    Emitting 0 here would assert the rig drilled this bore in no days, which
    is false for the common case: a bore drilled before WAR reporting shows
    only its later plugging or workover weeks. WAR carries no drilling
    evidence, so the value is null and the reason is stated. On the full
    corpus this is 54% of covered bores, so a 0 would badly skew any mean.
    """
    api = ["608124009500"]
    activity = pd.DataFrame([_war_week(1, api[0], "2020-01-05", "2020-01-11", "WO")])
    _, out = _enrich(_war_rows(api), _borehole_rows(api), activity)

    assert pd.isna(out["DRILLING_DAYS"].iloc[0])
    assert out["DRILLING_DAYS_STATUS"].iloc[0] == STATUS_NO_DRILLING
    # float64 with NaN, not the nullable Float64 dtype -- comprehensive_analyzer
    # feeds this column to np.nanpercentile, which rejects the latter.
    assert out["DRILLING_DAYS"].dtype == "float64"


def test_a_drilled_bore_is_labelled_covered():
    api = ["608124009500"]
    activity = pd.DataFrame([_war_week(1, api[0], "2020-01-05", "2020-01-11", "DRL")])
    _, out = _enrich(_war_rows(api), _borehole_rows(api), activity)
    assert out["DRILLING_DAYS_STATUS"].iloc[0] == STATUS_COVERED


def test_float_formatted_war_api_still_matches_the_borehole_population():
    """``pd.concat`` over the WAR zip widens API_WELL_NUMBER to float64.

    It then stringifies as "608124009500.0" while the borehole frame holds
    "608124009500".  Without normalising the WAR side the overlap between
    the two is exactly zero and every bore comes back null.
    """
    api = ["608124009500"]
    activity = pd.DataFrame(
        [_war_week(1, 608124009500.0, "2020-01-05", "2020-01-11", "DRL")]
    )
    assert activity["API_WELL_NUMBER"].dtype == "float64"

    _, out = _enrich(_war_rows(api), _borehole_rows(api), activity)
    assert out["DRILLING_DAYS"].iloc[0] == 7.0


# -- Absent coverage is null, never zero ------------------------------------


def test_bore_absent_from_war_is_null_not_zero():
    api = ["608124009500"]
    activity = pd.DataFrame(
        [_war_week(1, "177004076700", "2020-01-05", "2020-01-11", "DRL")]
    )
    _, out = _enrich(_war_rows(api), _borehole_rows(api), activity)

    assert pd.isna(out["DRILLING_DAYS"].iloc[0])
    assert out["DRILLING_DAYS"].iloc[0] != 0
    assert out["DRILLING_DAYS_STATUS"].iloc[0] == STATUS_NO_ACTIVITY


def test_unavailable_activity_source_nulls_days_rather_than_inventing_them():
    """With no way to compute rig time, emit nothing -- not a calendar span."""
    api = ["608124009500"]
    war = _war_rows(api)  # no WELL_ACTIVITY_CD and no SN_WAR anywhere
    engine = ActivityEnrichmentEngine(
        war_df=war, fleet_df=FLEET, borehole_df=_borehole_rows(api)
    )
    out = engine.enrich()

    assert out["DRILLING_DAYS"].isna().all()
    assert engine.get_join_stats()["rig_days_source"] == SOURCE_UNAVAILABLE


# -- Never negative ---------------------------------------------------------


def test_drilling_days_are_never_negative():
    """Replaces the old ``.where(raw_days >= 0)`` clamp.

    A reversed WAR week (end before start) used to be expressible as a
    negative calendar span; under the rig-days basis such rows are dropped,
    so the floor is 0.
    """
    api = ["608124009500"]
    activity = pd.DataFrame(
        [
            _war_week(1, api[0], "2020-01-11", "2020-01-05", "DRL"),  # reversed
            _war_week(2, api[0], "2020-02-02", "2020-02-08", "DRL"),
        ]
    )
    # TD before spud too, which is what used to produce a negative.
    bh = _borehole_rows(api, spud="2020-12-31", td="2010-01-01")
    _, out = _enrich(_war_rows(api), bh, activity)

    assert (out["DRILLING_DAYS"].dropna() >= 0).all()
    assert out["DRILLING_DAYS"].iloc[0] == 7.0


# -- Contract with downstream consumers -------------------------------------


def test_drilling_days_stays_float_for_numpy_consumers():
    """``comprehensive_analyzer`` runs ``np.nanpercentile`` over this column.

    A nullable ``Float64`` would break that, so the dtype must stay a plain
    numpy float even though the column carries nulls.
    """
    api = ["608124009500", "608124009501"]
    activity = pd.DataFrame([_war_week(1, api[0], "2020-01-05", "2020-01-11", "DRL")])
    _, out = _enrich(_war_rows(api), _borehole_rows(api), activity)

    assert out["DRILLING_DAYS"].dtype == "float64"


def test_enriched_frame_records_the_basis_it_used():
    api = ["608124009500"]
    activity = pd.DataFrame([_war_week(1, api[0], "2020-01-05", "2020-01-11", "DRL")])
    engine, out = _enrich(_war_rows(api), _borehole_rows(api), activity)

    basis = str(out["DRILLING_DAYS_BASIS"].iloc[0])
    assert "DRL_COM" in basis
    assert engine.get_join_stats()["rig_days_basis"] == basis


def test_join_stats_report_rig_days_provenance_and_fill():
    api = ["608124009500", "608124009501"]
    activity = pd.DataFrame([_war_week(1, api[0], "2020-01-05", "2020-01-11", "DRL")])
    engine, _ = _enrich(_war_rows(api), _borehole_rows(api), activity)

    stats = engine.get_join_stats()
    assert stats["rig_days_source"] == SOURCE_DIRECT
    assert stats["rig_days_fill_rate"] == pytest.approx(0.5)


# -- Recovering the activity frame from the acquirer's ragged concat ---------


def test_activity_codes_are_recovered_by_sn_war_self_join():
    """``acquire_war_dataframe`` concatenates the WAR zip members vertically.

    ``WELL_ACTIVITY_CD`` (mv_war_main_prop) and ``API_WELL_NUMBER`` /
    ``WAR_START_DT`` (mv_war_main) therefore never share a row -- they share
    only ``SN_WAR``.  The engine must re-join them rather than give up.
    """
    api = ["608124009500"]
    main_rows = pd.DataFrame(
        {
            "SN_WAR": [1, 2],
            "API_WELL_NUMBER": api * 2,
            "RIG_NAME": ["RIG A"] * 2,
            "WATER_DEPTH": [4000.0] * 2,
            "WAR_START_DT": ["2020-01-05", "2020-01-12"],
            "WAR_END_DT": ["2020-01-11", "2020-01-18"],
        }
    )
    prop_rows = pd.DataFrame({"SN_WAR": [1, 2], "WELL_ACTIVITY_CD": ["DRL", "DRL"]})
    ragged = pd.concat([main_rows, prop_rows], ignore_index=True)
    assert (
        not ragged[list(main_rows.columns) + ["WELL_ACTIVITY_CD"]]
        .notna()
        .all(axis=1)
        .any()
    )  # no row carries everything

    engine = ActivityEnrichmentEngine(
        war_df=ragged, fleet_df=FLEET, borehole_df=_borehole_rows(api)
    )
    out = engine.enrich()

    assert engine.get_join_stats()["rig_days_source"] == SOURCE_SN_WAR_JOIN
    # Two adjacent WAR weeks are continuous rig time: 14 days, not 2x7 - 1.
    assert out.loc[out["API_WELL_NUMBER"].eq(api[0]), "DRILLING_DAYS"].iloc[0] == 14.0


def test_empty_war_frame_short_circuits():
    engine = ActivityEnrichmentEngine(
        war_df=pd.DataFrame(),
        fleet_df=FLEET,
        borehole_df=_borehole_rows(["608124009500"]),
    )
    assert engine.enrich().empty
