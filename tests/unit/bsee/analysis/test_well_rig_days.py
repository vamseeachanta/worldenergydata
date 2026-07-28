"""Tests for WellRigDays after its convergence onto war_rig_days (#1075).

These pin *behaviour* the API12 pipeline publishes: that drilling days are
rig time from WAR activity codes rather than a spud -> total-depth calendar
span, and that absent WAR coverage reads as null rather than zero.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.war_rig_days import (
    BASIS_DRL_COM_PND,
    STATUS_COVERED,
    STATUS_NO_ACTIVITY,
)
from worldenergydata.bsee.analysis.well_rig_days import WellRigDays

API12 = "608124009500"

# A suspended well: the rig drilled two weeks in January, left, and came back
# to complete in July.  Spud -> TD spans 181 calendar days but only 14 of them
# are drilling rig time.
SPUD_DATE = "2014-01-01"
TD_DATE = "2014-06-30"
SPUD_TO_TD_CALENDAR_DAYS = 181
DRL_DAYS = 14
COM_DAYS = 7

WEEKS = [
    ("2014-01-05", "2014-01-11", "DRL"),
    ("2014-01-12", "2014-01-18", "DRL"),
    ("2014-07-06", "2014-07-12", "COM"),
]

CFG = {"parameters": {"max_allowed_npt": 90}}

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE = REPO_ROOT / "docs/modules/bsee/analysis/rig_days/war_data_608124009500.csv"

# Owner-published totals for well 608124009500 (rig_days_summary.md).
OWNER_DRL_DAYS = 151
OWNER_TOTAL_DAYS = 308
# Its spud -> total-depth span, i.e. what the old milestone rule returned.
REFERENCE_SPUD = "2014-07-27"
REFERENCE_TD = "2014-12-20"
REFERENCE_CALENDAR_DAYS = 147


def _war_frames(weeks=WEEKS, api12=API12, rig_name="Discoverer India"):
    """mv_war_main / mv_war_main_prop as the API12 loader hands them over."""
    main = pd.DataFrame(
        {
            "SN_WAR": list(range(1, len(weeks) + 1)),
            "API_WELL_NUMBER": [api12] * len(weeks),
            "WAR_START_DT": [w[0] for w in weeks],
            "WAR_END_DT": [w[1] for w in weeks],
            "RIG_NAME": [rig_name] * len(weeks),
        }
    )
    prop = pd.DataFrame(
        {
            "SN_WAR": list(range(1, len(weeks) + 1)),
            "WELL_ACTIVITY_CD": [w[2] for w in weeks],
        }
    )
    return main, prop


def _api12_df(spud=SPUD_DATE, td=TD_DATE):
    return pd.DataFrame({"WELL_SPUD_DATE": [spud], "TOTAL_DEPTH_DATE": [td]})


def _merged_war(weeks=WEEKS, api12=API12):
    """The joined frame rig_days_from_milestone receives."""
    main, prop = _war_frames(weeks, api12=api12)
    war = main.merge(prop, on="SN_WAR", how="left")
    war["WAR_START_DT"] = pd.to_datetime(war["WAR_START_DT"])
    war["WAR_END_DT"] = pd.to_datetime(war["WAR_END_DT"])
    return war


@pytest.fixture
def well():
    return WellRigDays()


class TestDrillingDaysAreRigTimeNotCalendarSpan:
    """The #1075 defect: a calendar span counted days the rig was elsewhere."""

    def test_drilling_days_come_from_drl_war_weeks(self, well):
        result = well.rig_days_from_milestone(
            CFG, pd.Timestamp(SPUD_DATE), pd.Timestamp(TD_DATE), _merged_war()
        )
        assert result["drilling_days"] == DRL_DAYS

    def test_drilling_days_ignore_the_suspended_period(self, well):
        result = well.rig_days_from_milestone(
            CFG, pd.Timestamp(SPUD_DATE), pd.Timestamp(TD_DATE), _merged_war()
        )
        assert result["drilling_days"] < SPUD_TO_TD_CALENDAR_DAYS

    def test_completion_days_come_from_com_weeks_not_everything_after_td(self, well):
        # The old rule was (max WAR end - TD) + 1 = 13 days, which credits the
        # gap between total depth and the completion crew arriving.
        result = well.rig_days_from_milestone(
            CFG, pd.Timestamp(SPUD_DATE), pd.Timestamp(TD_DATE), _merged_war()
        )
        assert result["completion_days"] == COM_DAYS

    def test_rig_days_is_drilling_plus_completion(self, well):
        result = well.rig_days_from_milestone(
            CFG, pd.Timestamp(SPUD_DATE), pd.Timestamp(TD_DATE), _merged_war()
        )
        assert result["rig_days"] == DRL_DAYS + COM_DAYS

    def test_adjacent_drl_weeks_are_continuous_rig_time(self, well):
        # Two back-to-back weeks are 14 days of rig time, not 7 + 7 with a
        # boundary day lost or gained.
        result = well.rig_days_from_milestone(
            CFG, pd.Timestamp(SPUD_DATE), pd.Timestamp(TD_DATE), _merged_war()
        )
        assert result["drilling_days"] == 14

    def test_days_survive_missing_spud_and_td_milestones(self, well):
        # Previously any missing milestone short-circuited to all zeros, even
        # with a full WAR history in hand.
        result = well.rig_days_from_milestone(CFG, None, None, _merged_war())
        assert result["drilling_days"] == DRL_DAYS
        assert result["completion_days"] == COM_DAYS
        assert result["days_status"] == STATUS_COVERED


class TestAbsentCoverageIsNullNotZero:
    def test_no_war_rows_yields_null_days(self, well):
        result = well.rig_days_from_milestone(
            CFG, pd.Timestamp(SPUD_DATE), pd.Timestamp(TD_DATE), _merged_war(weeks=[])
        )
        assert result["drilling_days"] is None
        assert result["completion_days"] is None
        assert result["rig_days"] is None
        assert result["days_status"] == STATUS_NO_ACTIVITY

    def test_unusable_war_frame_yields_null_days_not_an_exception(self, well):
        result = well.rig_days_from_milestone(
            CFG, None, None, pd.DataFrame({"API_WELL_NUMBER": [API12]})
        )
        assert result["drilling_days"] is None
        assert result["days_status"] == STATUS_NO_ACTIVITY

    def test_a_genuine_zero_is_distinguishable_from_no_coverage(self, well):
        # WAR covers this bore but records no DRL week at all.
        only_com = [("2014-07-06", "2014-07-12", "COM")]
        result = well.rig_days_from_milestone(
            CFG, None, None, _merged_war(weeks=only_com)
        )
        assert result["drilling_days"] == 0
        assert result["days_status"] == STATUS_COVERED


class TestBasisIsDeclaredNotAssumed:
    def test_result_records_the_basis_it_was_computed_under(self, well):
        result = well.rig_days_from_milestone(CFG, None, None, _merged_war())
        assert "DRL_COM" in result["basis"]
        assert "days=inclusive" in result["basis"]

    def test_an_alternate_basis_changes_completion_and_the_label(self, well):
        weeks = WEEKS + [("2014-07-13", "2014-07-19", "PND")]
        default = well.rig_days_from_milestone(CFG, None, None, _merged_war(weeks))
        with_pnd = well.rig_days_from_milestone(
            CFG, None, None, _merged_war(weeks), basis=BASIS_DRL_COM_PND
        )
        assert with_pnd["completion_days"] > default["completion_days"]
        assert with_pnd["basis"] != default["basis"]
        assert "PND" in with_pnd["basis"]

    def test_calendar_span_is_reported_under_its_own_label(self, well):
        result = well.rig_days_from_milestone(
            CFG, pd.Timestamp(SPUD_DATE), pd.Timestamp(TD_DATE), _merged_war()
        )
        assert result["spud_to_td_calendar_days"] == SPUD_TO_TD_CALENDAR_DAYS
        assert result["drilling_days"] != result["spud_to_td_calendar_days"]

    def test_calendar_span_is_null_when_a_milestone_is_missing(self, well):
        result = well.rig_days_from_milestone(
            CFG, None, pd.Timestamp(TD_DATE), _merged_war()
        )
        assert result["spud_to_td_calendar_days"] is None

    def test_result_is_json_serialisable_for_the_api12_report(self, well):
        result = well.rig_days_from_milestone(CFG, None, None, _merged_war())
        assert json.loads(json.dumps(result))["drilling_days"] == DRL_DAYS


class TestOwnerReferenceWell:
    """This module must now agree with the owner's published totals."""

    @pytest.fixture(scope="class")
    def reference_war(self):
        if not FIXTURE.exists():  # pragma: no cover - guards a moved fixture
            pytest.skip(f"WAR fixture not found: {FIXTURE}")
        return pd.read_csv(FIXTURE)

    def test_drilling_days_match_the_owners_published_total(self, well, reference_war):
        result = well.rig_days_from_milestone(
            CFG,
            pd.Timestamp(REFERENCE_SPUD),
            pd.Timestamp(REFERENCE_TD),
            reference_war,
        )
        assert result["drilling_days"] == OWNER_DRL_DAYS

    def test_the_old_calendar_rule_undercounted_this_well(self, well, reference_war):
        result = well.rig_days_from_milestone(
            CFG,
            pd.Timestamp(REFERENCE_SPUD),
            pd.Timestamp(REFERENCE_TD),
            reference_war,
        )
        assert result["spud_to_td_calendar_days"] == REFERENCE_CALENDAR_DAYS
        assert result["drilling_days"] > result["spud_to_td_calendar_days"]

    def test_total_war_days_match_the_owners_published_total(self, well, reference_war):
        result = well.rig_days_from_milestone(CFG, None, None, reference_war)
        assert result["war_days_total"] == OWNER_TOTAL_DAYS


class TestRigAnalysisEndToEnd:
    def test_activity_code_days_come_from_the_shared_module(self, well):
        main, prop = _war_frames()
        out = well.rig_analysis(CFG, _api12_df(), main, prop)

        assert out["api12_war_days"]["DRL"] == DRL_DAYS
        assert out["api12_war_days"]["COM"] == COM_DAYS
        # Total is the union of every WAR week, not the sum of the buckets.
        assert out["api12_war_days"]["total_rig_days"] == DRL_DAYS + COM_DAYS

    def test_rig_name_attribution_is_preserved(self, well):
        main, prop = _war_frames()
        out = well.rig_analysis(CFG, _api12_df(), main, prop)
        assert out["rig_str"] == "Discoverer India"

    def test_milestone_and_war_views_agree_on_drilling_days(self, well):
        main, prop = _war_frames()
        out = well.rig_analysis(CFG, _api12_df(), main, prop)
        assert (
            out["rig_days_from_milestone"]["drilling_days"]
            == out["api12_war_days"]["DRL"]
        )

    def test_no_war_coverage_reports_none_rather_than_empty_days(self, well):
        main, prop = _war_frames(weeks=[])
        out = well.rig_analysis(CFG, _api12_df(), main, prop)

        # None is the caller's signal to write null Drilling/Completion Days.
        assert out["api12_war_days"] is None
        assert out["rig_days_from_milestone"]["days_status"] == STATUS_NO_ACTIVITY

    def test_result_shape_is_unchanged_for_existing_consumers(self, well):
        main, prop = _war_frames()
        out = well.rig_analysis(CFG, _api12_df(), main, prop)

        assert set(out) == {"rig_str", "api12_war_days", "rig_days_from_milestone"}
        assert {"drilling_days", "completion_days", "rig_days"} <= set(
            out["rig_days_from_milestone"]
        )
