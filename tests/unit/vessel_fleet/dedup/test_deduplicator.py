"""Tests for fleet deduplication."""

from worldenergydata.vessel_fleet.dedup.deduplicator import deduplicate_fleet


class TestDeduplicateFleet:
    def test_no_duplicates(self):
        records = [
            {"VESSEL_NAME": "A", "IMO_NUMBER": "1234567"},
            {"VESSEL_NAME": "B", "IMO_NUMBER": "2345678"},
        ]
        result = deduplicate_fleet(records)
        assert len(result) == 2

    def test_imo_dedup(self):
        records = [
            {"VESSEL_NAME": "A", "IMO_NUMBER": "1234567", "DATA_SOURCE": "equasis"},
            {"VESSEL_NAME": "A", "IMO_NUMBER": "1234567", "DATA_SOURCE": "contractor_fleet_page", "OWNER": "Test"},
        ]
        result = deduplicate_fleet(records)
        assert len(result) == 1
        assert result[0]["OWNER"] == "Test"  # Higher priority source wins

    def test_name_dedup(self):
        records = [
            {"VESSEL_NAME": "DEEPWATER TITAN", "DATA_SOURCE": "xls_historical"},
            {"VESSEL_NAME": "DEEPWATER TITAN", "DATA_SOURCE": "contractor_spec_pdf", "YEAR_BUILT": 2014},
        ]
        result = deduplicate_fleet(records)
        assert len(result) == 1
        assert result[0]["YEAR_BUILT"] == 2014

    def test_merge_fills_gaps(self):
        records = [
            {"VESSEL_NAME": "A", "IMO_NUMBER": "1234567", "OWNER": "X", "DATA_SOURCE": "equasis"},
            {"VESSEL_NAME": "A", "IMO_NUMBER": "1234567", "YEAR_BUILT": 2020, "DATA_SOURCE": "contractor_fleet_page"},
        ]
        result = deduplicate_fleet(records)
        assert len(result) == 1
        assert result[0]["OWNER"] == "X"
        assert result[0]["YEAR_BUILT"] == 2020

    def test_empty_list(self):
        assert deduplicate_fleet([]) == []
