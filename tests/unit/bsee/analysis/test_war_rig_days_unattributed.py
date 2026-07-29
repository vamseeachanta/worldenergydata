"""Unattributed WAR coverage is not absent coverage (#1120).

`mv_war_main_prop` does not cover every `SN_WAR` in `mv_war_main`. On the
2026-02-19 feed that is 2,030 weeks, 280 of them inside the published
253-bore population -- and for 38 of those bores it is *every* week they have,
up to 32 weeks each of recorded rig presence.

Those weeks were being dropped by an inner join before `days_status` ever saw
them, so the pipeline reported `no_war_activity` -- a claim that BSEE holds
nothing -- about bores BSEE holds weeks of data for. The status column was
accurate about the data it received and false about the world, because the
data had already been filtered upstream.

The rule these tests pin: a week with no activity code is UNATTRIBUTED. It
counts as coverage, it never counts toward an activity total, and it is never
reported as absence.
"""

import pandas as pd

from worldenergydata.bsee.analysis.war_rig_days import (
    STATUS_COVERED,
    STATUS_COVERED_UNATTRIBUTED,
    STATUS_NO_ACTIVITY,
    rig_days_by_bore,
)

API = "608124009500"
OTHER = "608124111100"
COLUMNS = ["API_WELL_NUMBER", "WAR_START_DT", "WAR_END_DT", "WELL_ACTIVITY_CD"]


def war(rows):
    return pd.DataFrame(rows, columns=COLUMNS)


class TestUnattributedIsNotAbsent:
    def test_a_bore_with_only_uncoded_weeks_is_covered_not_absent(self):
        # The 38-bore case: WAR holds the weeks, none carries a code.
        frame = rig_days_by_bore(
            war(
                [
                    [API, "2024-01-01", "2024-01-07", None],
                    [API, "2024-01-08", "2024-01-14", None],
                ]
            )
        ).squeeze()

        assert frame["days_status"] == STATUS_COVERED_UNATTRIBUTED
        assert frame["days_status"] != STATUS_NO_ACTIVITY

    def test_its_coverage_is_reported_rather_than_erased(self):
        frame = rig_days_by_bore(
            war(
                [
                    [API, "2024-01-01", "2024-01-07", None],
                    [API, "2024-01-08", "2024-01-14", None],
                ]
            )
        ).squeeze()

        assert int(frame["war_days_total"]) == 14
        assert int(frame["war_weeks"]) == 2
        assert int(frame["war_weeks_unattributed"]) == 2

    def test_uncoded_weeks_never_reach_an_activity_total(self):
        # Coverage without attribution cannot become drilling days.
        frame = rig_days_by_bore(
            war([[API, "2024-01-01", "2024-01-07", None]])
        ).squeeze()

        assert pd.isna(frame["drilling_days"])
        assert pd.isna(frame["completion_days"])
        assert frame["days_by_code"] == {}

    def test_a_partially_coded_bore_counts_only_its_coded_weeks(self):
        frame = rig_days_by_bore(
            war(
                [
                    [API, "2024-01-01", "2024-01-07", "DRL"],
                    [API, "2024-02-01", "2024-02-07", None],
                ]
            )
        ).squeeze()

        assert int(frame["drilling_days"]) == 7  # not 14
        assert int(frame["war_days_total"]) == 14  # coverage includes both
        assert int(frame["war_weeks_unattributed"]) == 1
        assert frame["days_status"] == STATUS_COVERED  # some week is attributed


class TestTheThreeStatesStayDistinct:
    def test_absent_covered_and_unattributed_are_three_different_things(self):
        frame = rig_days_by_bore(
            war(
                [
                    [API, "2024-01-01", "2024-01-07", "DRL"],
                    [OTHER, "2024-01-01", "2024-01-07", None],
                ]
            ),
            population=[API, OTHER, "999999999999"],
        ).set_index("api12")

        assert frame.loc[API, "days_status"] == STATUS_COVERED
        assert frame.loc[OTHER, "days_status"] == STATUS_COVERED_UNATTRIBUTED
        assert frame.loc["999999999999", "days_status"] == STATUS_NO_ACTIVITY

    def test_only_the_genuinely_absent_bore_reports_null_coverage(self):
        frame = rig_days_by_bore(
            war([[OTHER, "2024-01-01", "2024-01-07", None]]),
            population=[OTHER, "999999999999"],
        ).set_index("api12")

        # Unattributed: coverage is known.
        assert int(frame.loc[OTHER, "war_days_total"]) == 7
        # Absent: coverage is not known, and must not read as zero.
        assert pd.isna(frame.loc["999999999999", "war_days_total"])
