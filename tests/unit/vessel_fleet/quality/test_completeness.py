"""Tests for vessel fleet completeness scoring."""

import pytest

from worldenergydata.vessel_fleet.quality.completeness import (
    completeness_score,
    fleet_completeness_report,
)


class TestCompletenessScore:
    def test_all_fields_present(self):
        record = {"A": 1, "B": 2, "C": 3}
        assert completeness_score(record, ("A", "B", "C")) == 1.0

    def test_no_fields_present(self):
        record = {"X": 1}
        assert completeness_score(record, ("A", "B", "C")) == 0.0

    def test_partial_fields(self):
        record = {"A": 1, "B": None, "C": 3}
        assert completeness_score(record, ("A", "B", "C")) == pytest.approx(2 / 3)

    def test_missing_keys_treated_as_none(self):
        record = {"A": 1}
        assert completeness_score(record, ("A", "B")) == 0.5

    def test_empty_core_fields(self):
        record = {"A": 1}
        assert completeness_score(record, ()) == 0.0

    def test_empty_record(self):
        assert completeness_score({}, ("A", "B")) == 0.0

    def test_none_values_not_counted(self):
        record = {"A": None, "B": None}
        assert completeness_score(record, ("A", "B")) == 0.0

    def test_zero_value_is_counted(self):
        record = {"A": 0, "B": ""}
        assert completeness_score(record, ("A", "B")) == 1.0

    def test_single_field(self):
        record = {"A": "value"}
        assert completeness_score(record, ("A",)) == 1.0


class TestFleetCompletenessReport:
    def test_empty_records(self):
        report = fleet_completeness_report([])
        assert report["total_records"] == 0
        assert report["avg_completeness"] == 0.0
        assert report["field_coverage"] == {}

    def test_drilling_rig_category(self):
        records = [
            {
                "VESSEL_NAME": "Rig A",
                "RIG_TYPE": "drillship",
                "OWNER": "Co",
                "WATER_DEPTH_RATING_FT": 10000,
                "DRILLING_DEPTH_RATING_FT": 35000,
                "YEAR_BUILT": 2015,
                "DP_CLASS": "3",
                "LOA_M": 230,
                "BEAM_M": 42,
                "IMO_NUMBER": "1234567",
            },
        ]
        report = fleet_completeness_report(records, "drilling_rig")
        assert report["total_records"] == 1
        assert report["avg_completeness"] == 1.0
        assert report["min_completeness"] == 1.0
        assert report["max_completeness"] == 1.0
        assert report["field_coverage"]["VESSEL_NAME"] == 1.0

    def test_construction_vessel_category(self):
        records = [
            {
                "VESSEL_NAME": "HLV A",
                "VESSEL_TYPE": "heavy_lift",
                "OWNER": "Co",
                "YEAR_BUILT": 2019,
                "LOA_M": 220,
                "BEAM_M": 102,
                "DP_CLASS": "3",
                "IMO_NUMBER": "7654321",
                "MAIN_CRANE_CAPACITY_T": 14000,
                "QUARTERS_CAPACITY": 400,
            },
        ]
        report = fleet_completeness_report(records, "construction_vessel")
        assert report["avg_completeness"] == 1.0

    def test_partial_records(self):
        records = [
            {"VESSEL_NAME": "A", "RIG_TYPE": "semi"},
            {"VESSEL_NAME": "B"},
        ]
        report = fleet_completeness_report(records, "drilling_rig")
        assert report["total_records"] == 2
        assert report["field_coverage"]["VESSEL_NAME"] == 1.0
        assert report["field_coverage"]["RIG_TYPE"] == 0.5
        assert report["avg_completeness"] < 1.0

    def test_min_max_completeness(self):
        records = [
            {"VESSEL_NAME": "A"},
            {
                "VESSEL_NAME": "B", "RIG_TYPE": "drillship",
                "OWNER": "Co", "WATER_DEPTH_RATING_FT": 10000,
                "DRILLING_DEPTH_RATING_FT": 35000, "YEAR_BUILT": 2015,
                "DP_CLASS": "3", "LOA_M": 230, "BEAM_M": 42,
                "IMO_NUMBER": "1234567",
            },
        ]
        report = fleet_completeness_report(records, "drilling_rig")
        assert report["min_completeness"] < report["max_completeness"]
        assert report["max_completeness"] == 1.0

    def test_rounding(self):
        records = [
            {"VESSEL_NAME": "A", "RIG_TYPE": "semi", "OWNER": "Co"},
        ]
        report = fleet_completeness_report(records, "drilling_rig")
        # 3/10 = 0.3 -> should be rounded to 4 decimal places
        assert report["avg_completeness"] == 0.3
