"""Tests for completeness scoring."""

from worldenergydata.vessel_fleet.quality.completeness import (
    completeness_score,
    fleet_completeness_report,
)


class TestCompletenessScore:
    def test_full_record(self):
        record = {
            "VESSEL_NAME": "A", "RIG_TYPE": "drillship", "OWNER": "X",
            "WATER_DEPTH_RATING_FT": 12000, "DRILLING_DEPTH_RATING_FT": 40000,
            "YEAR_BUILT": 2014, "DP_CLASS": 3, "LOA_M": 228, "BEAM_M": 42,
            "IMO_NUMBER": "1234567",
        }
        fields = ("VESSEL_NAME", "RIG_TYPE", "OWNER", "WATER_DEPTH_RATING_FT",
                  "DRILLING_DEPTH_RATING_FT", "YEAR_BUILT", "DP_CLASS",
                  "LOA_M", "BEAM_M", "IMO_NUMBER")
        assert completeness_score(record, fields) == 1.0

    def test_partial_record(self):
        record = {"VESSEL_NAME": "A", "YEAR_BUILT": 2014}
        fields = ("VESSEL_NAME", "RIG_TYPE", "OWNER", "YEAR_BUILT")
        assert completeness_score(record, fields) == 0.5

    def test_empty_record(self):
        assert completeness_score({}, ("VESSEL_NAME",)) == 0.0


class TestFleetCompletenessReport:
    def test_basic_report(self):
        records = [
            {"VESSEL_NAME": "A", "RIG_TYPE": "drillship", "OWNER": "X"},
            {"VESSEL_NAME": "B"},
        ]
        report = fleet_completeness_report(records, "drilling_rig")
        assert report["total_records"] == 2
        assert 0 < report["avg_completeness"] < 1.0

    def test_empty_records(self):
        report = fleet_completeness_report([], "drilling_rig")
        assert report["total_records"] == 0
