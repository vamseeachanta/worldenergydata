"""Capabilities ported out of the legacy ONGFDComponents (#1112).

The legacy module measured sidetrack and abandonment as separate phases, and
attributed days to the rig that reported them. Those capabilities were real and
absent from the drilling/completion split. The legacy *arithmetic* was not
ported: it summed per-rig intervals (double-counting overlaps) and inferred
days from gaps between WAR reports.

Not ported, deliberately: NPT. The legacy code inferred non-productive time
from gaps between consecutive reports. A gap evidences missing reporting
coverage, not an idle rig -- it equally means reporting cadence, rig release,
suspension or extraction loss. Naming it NPT asserts far more than the data
supports, which is the defect class this whole module exists to remove.
"""

import pandas as pd

from worldenergydata.bsee.analysis.war_rig_days import (
    DEFAULT_PHASES,
    STATUS_COVERED,
    STATUS_NO_ACTIVITY_CODED,
    rig_days_by_bore,
)

API = "608124009500"
COLUMNS = ["API_WELL_NUMBER", "WAR_START_DT", "WAR_END_DT", "WELL_ACTIVITY_CD"]


def war(rows, columns=COLUMNS):
    return pd.DataFrame(rows, columns=columns)


class TestPhaseDurations:
    def test_sidetrack_days_are_measured_separately(self):
        frame = rig_days_by_bore(
            war(
                [
                    [API, "2024-01-01", "2024-01-07", "DRL"],
                    [API, "2024-02-01", "2024-02-07", "ST"],
                ]
            )
        ).squeeze()
        assert int(frame["drilling_days"]) == 7
        assert int(frame["sidetrack_days"]) == 7
        assert frame["sidetrack_days_status"] == STATUS_COVERED

    def test_temporary_and_permanent_abandonment_stay_distinct(self):
        # Different operational outcomes. The legacy code kept them apart and
        # collapsing them here would discard that.
        frame = rig_days_by_bore(
            war(
                [
                    [API, "2024-01-01", "2024-01-07", "TA"],
                    [API, "2024-03-01", "2024-03-14", "PA"],
                ]
            )
        ).squeeze()
        assert int(frame["temp_abandonment_days"]) == 7
        assert int(frame["perm_abandonment_days"]) == 14

    def test_an_absent_phase_is_null_not_zero(self):
        # Same rule as drilling: no week coded to the phase is an absence of
        # evidence, not a measurement of zero.
        frame = rig_days_by_bore(
            war([[API, "2024-01-01", "2024-01-07", "DRL"]])
        ).squeeze()
        assert pd.isna(frame["sidetrack_days"])
        assert frame["sidetrack_days_status"] == STATUS_NO_ACTIVITY_CODED

    def test_phases_are_configurable_rather_than_hardcoded(self):
        frame = rig_days_by_bore(
            war([[API, "2024-01-01", "2024-01-07", "WO"]]),
            phases={"workover": frozenset({"WO"})},
        ).squeeze()
        assert int(frame["workover_days"]) == 7
        assert "sidetrack_days" not in frame.index

    def test_default_phases_cover_sidetrack_and_both_abandonments(self):
        assert set(DEFAULT_PHASES) == {
            "sidetrack",
            "temp_abandonment",
            "perm_abandonment",
        }


class TestRigAttribution:
    COLS = COLUMNS + ["RIG_NAME"]

    def test_days_are_attributed_to_the_reporting_rig(self):
        frame = rig_days_by_bore(
            war(
                [
                    [API, "2024-01-01", "2024-01-07", "DRL", "NOBLE JIM DAY"],
                    [API, "2024-03-01", "2024-03-07", "DRL", "DEEPWATER TITAN"],
                ],
                columns=self.COLS,
            )
        ).squeeze()
        assert frame["rig_days_by_rig"] == {"NOBLE JIM DAY": 7, "DEEPWATER TITAN": 7}

    def test_overlapping_weeks_for_one_rig_are_unioned_not_summed(self):
        # The legacy implementation summed, double-counting the overlap.
        frame = rig_days_by_bore(
            war(
                [
                    [API, "2024-01-01", "2024-01-10", "DRL", "RIG A"],
                    [API, "2024-01-05", "2024-01-07", "DRL", "RIG A"],
                ],
                columns=self.COLS,
            )
        ).squeeze()
        assert frame["rig_days_by_rig"] == {"RIG A": 10}

    def test_a_missing_rig_name_is_unattributed_not_a_rig_called_unknown(self):
        frame = rig_days_by_bore(
            war(
                [[API, "2024-01-01", "2024-01-07", "DRL", None]],
                columns=self.COLS,
            )
        ).squeeze()
        assert frame["rig_days_by_rig"] == {None: 7}

    def test_absent_column_yields_no_attribution_rather_than_a_guess(self):
        frame = rig_days_by_bore(
            war([[API, "2024-01-01", "2024-01-07", "DRL"]])
        ).squeeze()
        assert frame["rig_days_by_rig"] == {}


class TestDrillFluidWeight:
    COLS = COLUMNS + ["DRILL_FLUID_WGT"]

    def test_the_heaviest_reported_weight_is_carried(self):
        frame = rig_days_by_bore(
            war(
                [
                    [API, "2024-01-01", "2024-01-07", "DRL", 12.0],
                    [API, "2024-01-08", "2024-01-14", "DRL", 14.5],
                ],
                columns=self.COLS,
            )
        ).squeeze()
        assert frame["max_drill_fluid_wgt"] == 14.5

    def test_nothing_reported_is_null_not_zero(self):
        # A bore with no recorded fluid weight is not a bore drilled on water.
        frame = rig_days_by_bore(
            war(
                [[API, "2024-01-01", "2024-01-07", "DRL", None]],
                columns=self.COLS,
            )
        ).squeeze()
        assert pd.isna(frame["max_drill_fluid_wgt"])

    def test_zero_is_treated_as_unreported(self):
        frame = rig_days_by_bore(
            war(
                [[API, "2024-01-01", "2024-01-07", "DRL", 0]],
                columns=self.COLS,
            )
        ).squeeze()
        assert pd.isna(frame["max_drill_fluid_wgt"])


class TestNoRegression:
    def test_existing_outputs_are_unchanged_by_the_port(self):
        frame = rig_days_by_bore(
            war(
                [
                    [API, "2024-01-01", "2024-01-07", "DRL"],
                    [API, "2024-01-08", "2024-01-14", "COM"],
                ]
            )
        ).squeeze()
        assert int(frame["drilling_days"]) == 7
        assert int(frame["completion_days"]) == 7
        assert int(frame["war_days_total"]) == 14
