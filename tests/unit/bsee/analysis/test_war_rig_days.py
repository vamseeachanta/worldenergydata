"""Tests for war_rig_days -- the single WAR activity-code rig-day implementation.

The anchor test reproduces the domain owner's own published totals for well
608124009500 (a Stones well) from the WAR extract committed alongside this
repo, so the basis is validated in CI without the ~370 MB raw WAR download.
"""

from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.war_rig_days import (
    BASIS_DRL_COM,
    BASIS_DRL_COM_PND,
    BASIS_METHOD_1,
    STATUS_COVERED,
    STATUS_NO_ACTIVITY,
    normalize_api12,
    rig_days_by_bore,
    rig_days_by_well,
    union_days,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE = REPO_ROOT / "docs/modules/bsee/analysis/rig_days/war_data_608124009500.csv"
REFERENCE_API12 = "608124009500"

# rig_days_summary.md records, for this well: {"COM": 87, "DRL": 151,
# "PND": 49, "TA": 21}.  DRL, PND and the 308-day total reproduce exactly.
# COM/TA differ by 4 days in a compensating pair because one WAR week
# straddles the COM -> TA code change; the total is therefore unaffected.
OWNER_DRL_DAYS = 151
OWNER_PND_DAYS = 49
OWNER_TOTAL_DAYS = 308


@pytest.fixture(scope="module")
def war() -> pd.DataFrame:
    if not FIXTURE.exists():  # pragma: no cover - guards a moved fixture
        pytest.skip(f"WAR fixture not found: {FIXTURE}")
    return pd.read_csv(FIXTURE)


def _ts(day: str) -> pd.Timestamp:
    return pd.Timestamp(day)


class TestUnionDays:
    def test_single_war_week_is_inclusive_of_both_endpoints(self):
        # A WAR week runs Sunday 00:00 -> Saturday 23:59 and is seven days.
        assert union_days([(_ts("2014-07-27"), _ts("2014-08-02"))]) == 7

    def test_back_to_back_weeks_merge_into_continuous_rig_time(self):
        # Regression: adjacent weeks were previously counted as disjoint,
        # losing a day at every week boundary.
        weeks = [
            (_ts("2014-01-01"), _ts("2014-01-07")),
            (_ts("2014-01-08"), _ts("2014-01-14")),
        ]
        assert union_days(weeks) == 14

    def test_overlapping_intervals_are_not_double_counted(self):
        spans = [
            (_ts("2014-01-01"), _ts("2014-01-10")),
            (_ts("2014-01-05"), _ts("2014-01-07")),
        ]
        assert union_days(spans) == 10

    def test_gap_between_spans_is_excluded(self):
        spans = [
            (_ts("2014-01-01"), _ts("2014-01-07")),
            (_ts("2014-02-01"), _ts("2014-02-07")),
        ]
        assert union_days(spans) == 14

    def test_empty_and_missing_endpoints_yield_zero(self):
        assert union_days([]) == 0
        assert union_days([(pd.NaT, _ts("2014-01-07"))]) == 0

    def test_time_of_day_does_not_truncate_a_run_of_weeks(self):
        # WAR weeks are stamped 00:01 -> 23:59.  Seven consecutive weeks span
        # 47d23h59m of elapsed time but 49 calendar days; counting elapsed
        # time silently loses a day.  This is the PND run on well
        # 608124009500, which the owner records as 49 days.
        weeks = [
            (_ts("2014-12-21 00:01"), _ts("2014-12-27 23:59")),
            (_ts("2014-12-28 00:01"), _ts("2015-01-03 23:59")),
            (_ts("2015-01-04 00:01"), _ts("2015-01-10 23:59")),
            (_ts("2015-01-11 00:01"), _ts("2015-01-17 23:59")),
            (_ts("2015-01-18 00:01"), _ts("2015-01-24 23:59")),
            (_ts("2015-01-25 00:01"), _ts("2015-01-31 23:59")),
            (_ts("2015-02-01 00:00"), _ts("2015-02-07 00:00")),
        ]
        assert union_days(weeks) == 49


class TestOwnerReferenceWell:
    """The acceptance criterion from #1063: reproduce the owner's numbers."""

    def test_drilling_days_match_owner_exactly(self, war):
        bores = rig_days_by_bore(war, basis=BASIS_DRL_COM)
        row = bores.loc[bores["api12"].eq(REFERENCE_API12)].squeeze()
        assert int(row["drilling_days"]) == OWNER_DRL_DAYS

    def test_pnd_days_match_owner_exactly(self, war):
        bores = rig_days_by_bore(war, basis=BASIS_DRL_COM)
        row = bores.loc[bores["api12"].eq(REFERENCE_API12)].squeeze()
        assert int(row["pnd_days"]) == OWNER_PND_DAYS

    def test_total_war_days_match_owner_exactly(self, war):
        bores = rig_days_by_bore(war, basis=BASIS_DRL_COM)
        row = bores.loc[bores["api12"].eq(REFERENCE_API12)].squeeze()
        assert int(row["war_days_total"]) == OWNER_TOTAL_DAYS

    def test_com_and_ta_differ_only_as_a_compensating_pair(self, war):
        # One WAR week straddles the COM -> TA transition, so our split is
        # COM 91 / TA 17 against the owner's 87 / 21.  Pin the invariant that
        # matters -- the pair sums to the same 108 days -- rather than the
        # arbitrary side of the boundary the straddling week lands on.
        bores = rig_days_by_bore(war, basis=BASIS_DRL_COM)
        row = bores.loc[bores["api12"].eq(REFERENCE_API12)].squeeze()
        com = row["days_by_code"].get("COM", 0)
        ta = row["days_by_code"].get("TA", 0)
        assert com + ta == 87 + 21
        assert abs(com - 87) <= 7  # within one WAR week of the owner's split


class TestBasisIsAlwaysDeclared:
    def test_bore_frame_records_the_basis_it_was_computed_under(self, war):
        bores = rig_days_by_bore(war, basis=BASIS_DRL_COM)
        assert bores["basis"].eq(BASIS_DRL_COM.describe()).all()
        assert "days=inclusive" in BASIS_DRL_COM.describe()

    def test_pnd_moves_completion_but_never_drilling(self, war):
        without = rig_days_by_bore(war, basis=BASIS_DRL_COM).squeeze()
        with_pnd = rig_days_by_bore(war, basis=BASIS_DRL_COM_PND).squeeze()
        assert with_pnd["drilling_days"] == without["drilling_days"]
        assert with_pnd["completion_days"] > without["completion_days"]

    def test_owner_method_1_adds_ta_on_top_of_pnd(self, war):
        with_pnd = rig_days_by_bore(war, basis=BASIS_DRL_COM_PND).squeeze()
        method_1 = rig_days_by_bore(war, basis=BASIS_METHOD_1).squeeze()
        assert method_1["completion_days"] > with_pnd["completion_days"]

    def test_pnd_is_reported_separately_under_every_basis(self, war):
        for basis in (BASIS_DRL_COM, BASIS_DRL_COM_PND, BASIS_METHOD_1):
            frame = rig_days_by_bore(war, basis=basis)
            assert int(frame.squeeze()["pnd_days"]) == OWNER_PND_DAYS


class TestPopulationCoverage:
    def test_bore_without_war_activity_is_null_not_zero(self, war):
        absent = "999999999999"
        frame = rig_days_by_bore(war, population=[REFERENCE_API12, absent])
        row = frame.loc[frame["api12"].eq(absent)].squeeze()

        assert row["days_status"] == STATUS_NO_ACTIVITY
        assert pd.isna(row["drilling_days"])
        assert pd.isna(row["completion_days"])

    def test_covered_bore_is_flagged_covered(self, war):
        frame = rig_days_by_bore(war, population=[REFERENCE_API12])
        assert frame.squeeze()["days_status"] == STATUS_COVERED

    def test_population_restricts_the_output(self, war):
        frame = rig_days_by_bore(war, population=[REFERENCE_API12])
        assert list(frame["api12"]) == [REFERENCE_API12]


class TestApi10Collapse:
    def test_grain_columns_are_derived_from_the_api12_key(self, war):
        bores = rig_days_by_bore(war)
        row = bores.squeeze()
        assert row["api10"] == REFERENCE_API12[:10]
        assert row["bore_suffix"] == REFERENCE_API12[10:]

    def test_single_bore_well_has_no_overlap_between_methods(self, war):
        wells = rig_days_by_well(war)
        row = wells.squeeze()
        assert row["n_bores"] == 1
        assert row["overlap_days"] == 0
        assert row["war_days_total"] == OWNER_TOTAL_DAYS

    def test_sidetrack_boundary_week_is_not_double_counted(self):
        # Two bores of one well whose WAR weeks abut across the sidetrack.
        # Additive counts the boundary week twice; the union must not.
        war = pd.DataFrame(
            {
                "API_WELL_NUMBER": ["608124009500", "608124009501"],
                "WAR_START_DT": ["2014-01-01", "2014-01-08"],
                "WAR_END_DT": ["2014-01-14", "2014-01-21"],
                "WELL_ACTIVITY_CD": ["DRL", "DRL"],
            }
        )
        wells = rig_days_by_well(war).squeeze()

        assert wells["n_bores"] == 2
        assert wells["bore_suffixes"] == "00,01"
        assert wells["war_days_additive"] == 28  # 14 + 14
        assert wells["war_days_total"] == 21  # Jan 1 -> Jan 21
        assert wells["overlap_days"] == 7  # one straddling week


class TestApiNormalization:
    """A float-typed API column must not read as absent WAR coverage."""

    def test_float_typed_api_still_matches_the_population(self):
        # Concatenating heterogeneous WAR members widens API_WELL_NUMBER to
        # float64, which stringifies as "608124009500.0".  Before this was
        # handled, every bore fell out of the population match and came back
        # null -- reported as no_war_activity, so a dtype mismatch was
        # indistinguishable from a genuine coverage gap.
        war = pd.DataFrame(
            {
                "API_WELL_NUMBER": [608124009500.0, 608124009500.0],
                "WAR_START_DT": ["2014-01-01", "2014-01-08"],
                "WAR_END_DT": ["2014-01-07", "2014-01-14"],
                "WELL_ACTIVITY_CD": ["DRL", "DRL"],
            }
        )
        row = rig_days_by_bore(war, population=[REFERENCE_API12]).squeeze()

        assert row["days_status"] == STATUS_COVERED
        assert row["api12"] == REFERENCE_API12
        assert int(row["drilling_days"]) == 14

    def test_normalization_is_symmetric_across_both_sides_of_the_match(self):
        war = pd.DataFrame(
            {
                "API_WELL_NUMBER": ["608124009500"],
                "WAR_START_DT": ["2014-01-01"],
                "WAR_END_DT": ["2014-01-07"],
                "WELL_ACTIVITY_CD": ["DRL"],
            }
        )
        # float-typed population, string-typed WAR
        row = rig_days_by_bore(war, population=[608124009500.0]).squeeze()
        assert row["days_status"] == STATUS_COVERED
        assert int(row["drilling_days"]) == 7

    def test_int_typed_api_is_unaffected(self):
        assert list(normalize_api12([608124009500])) == ["608124009500"]
        assert list(normalize_api12(["608124009500"])) == ["608124009500"]
        assert list(normalize_api12([608124009500.0])) == ["608124009500"]


class TestInputContract:
    def test_missing_required_column_is_a_clear_error(self):
        with pytest.raises(ValueError, match="WELL_ACTIVITY_CD"):
            rig_days_by_bore(pd.DataFrame({"API_WELL_NUMBER": ["1"]}))
