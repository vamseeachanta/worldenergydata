"""Regression pins for defects found by adversarial review of war_rig_days.

Each of these produced a wrong published number, silently, from an input the
original tests never constructed. They are written as *properties* rather than
point checks -- the underlying failure was an invariant enforced at the one
place it was being thought about, and nowhere else.

The governing invariant: **a null must never become a number, and an absence
must never become a measured zero.**
"""

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.war_rig_days import (
    STATUS_COVERED,
    STATUS_NO_ACTIVITY,
    rig_days_by_bore,
    rig_days_by_well,
)

API_A = "608124009500"
API_A_ST = "608124009501"  # sidetrack of the same well
API_B = "608124111100"  # different well
COLUMNS = ["API_WELL_NUMBER", "WAR_START_DT", "WAR_END_DT", "WELL_ACTIVITY_CD"]


def war(rows):
    return pd.DataFrame(rows, columns=COLUMNS)


class TestMalformedSpans:
    """A return whose end precedes its start is malformed, not zero-length."""

    def test_reversed_week_is_not_published_as_zero_days(self):
        # Previously: union_days dropped the interval but _days_and_status
        # still saw a non-empty group and returned (0, war_covered) -- so a
        # reversed seven-day week published as "drilled in 0 days".
        frame = rig_days_by_bore(war([[API_A, "2024-01-07", "2024-01-01", "DRL"]]))
        assert frame.empty or not (frame["drilling_days"] == 0).any()

    def test_reversed_week_in_a_population_reads_as_absent_not_zero(self):
        frame = rig_days_by_bore(
            war([[API_A, "2024-01-07", "2024-01-01", "DRL"]]), population=[API_A]
        )
        row = frame.squeeze()
        assert pd.isna(row["drilling_days"])
        assert row["days_status"] == STATUS_NO_ACTIVITY

    def test_a_valid_span_alongside_a_reversed_one_still_counts(self):
        # The malformed row must be discarded without taking the good one.
        frame = rig_days_by_bore(
            war(
                [
                    [API_A, "2024-01-01", "2024-01-07", "DRL"],
                    [API_A, "2024-02-07", "2024-02-01", "DRL"],
                ]
            )
        )
        assert int(frame.squeeze()["drilling_days"]) == 7


class TestNullsNeverBecomeNumbers:
    """The load-bearing property, checked at well grain where it was broken."""

    def test_all_null_group_stays_null_rather_than_summing_to_zero(self):
        # pandas sums an all-NA group to 0, restating "we do not know this
        # bore's drilling days" as "it was drilled in zero days".
        wells = rig_days_by_well(war([[API_A, "2024-01-01", "2024-01-07", "COM"]]))
        assert pd.isna(wells.squeeze()["drilling_days_additive"])

    def test_partial_coverage_is_disclosed_as_a_lower_bound(self):
        # [7, null] sums to 7 -- min_count=1 needs only one valid value -- so
        # the total is a lower bound. n_bores_covered must reveal that.
        wells = rig_days_by_well(
            war(
                [
                    [API_A, "2024-01-01", "2024-01-07", "DRL"],
                    [API_A_ST, "2024-06-01", "2024-06-07", "COM"],
                ]
            )
        ).squeeze()
        assert wells["n_bores"] == 2
        assert wells["n_bores_covered"] == 2  # both bores are in WAR
        assert int(wells["drilling_days_additive"]) == 7

    def test_uncovered_bore_is_counted_but_not_credited(self):
        wells = rig_days_by_well(
            war([[API_A, "2024-01-01", "2024-01-07", "DRL"]]),
            population=[API_A, API_A_ST],
        ).squeeze()
        assert wells["n_bores"] == 2
        assert wells["n_bores_covered"] == 1
        assert int(wells["drilling_days_additive"]) == 7


class TestNoWellSilentlyDisappears:
    def test_uncovered_bore_keeps_its_well_in_the_output(self):
        # Previously the well grain was built from covered bores only, so an
        # uncovered bore vanished at API10 while being correct at API12.
        rows = war([[API_A, "2024-01-01", "2024-01-07", "DRL"]])
        population = [API_A, API_B]

        bores = rig_days_by_bore(rows, population=population)
        wells = rig_days_by_well(rows, population=population)

        assert set(bores["api12"]) == set(population)
        assert set(wells["api10"]) == {API_A[:10], API_B[:10]}

    def test_every_bore_uncovered_returns_rows_rather_than_raising(self):
        # Previously raised KeyError: 'api10' on the empty union frame.
        wells = rig_days_by_well(
            war([["999999999999", "2024-01-01", "2024-01-07", "DRL"]]),
            population=[API_A],
        )
        assert len(wells) == 1
        assert wells.squeeze()["days_status"] == STATUS_NO_ACTIVITY

    def test_a_well_with_no_coverage_is_not_labelled_covered(self):
        wells = rig_days_by_well(
            war([[API_A, "2024-01-01", "2024-01-07", "DRL"]]),
            population=[API_A, API_B],
        ).set_index("api10")
        assert wells.loc[API_A[:10], "days_status"] == STATUS_COVERED
        assert wells.loc[API_B[:10], "days_status"] == STATUS_NO_ACTIVITY


class TestDateDtypes:
    @pytest.mark.parametrize(
        "start,end",
        [
            (20240101, 20240107),  # int -> read as ns since epoch -> 1970
            ("20240101", "20240107"),
            ("2024-01-01", "2024-01-07"),
            ("2024-01-01 00:01:00", "2024-01-07 23:59:00"),
        ],
    )
    def test_every_dtype_the_feed_uses_yields_the_same_week(self, start, end):
        # As bare integers pandas reads these as nanoseconds after the epoch,
        # collapsing both to 1970-01-01 and measuring a seven-day week as one.
        frame = rig_days_by_bore(war([[API_A, start, end, "DRL"]]))
        assert int(frame.squeeze()["drilling_days"]) == 7
