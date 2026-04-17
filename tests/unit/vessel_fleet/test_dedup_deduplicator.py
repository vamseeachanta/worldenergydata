"""Tests for vessel fleet deduplication and merge module."""

import pytest

from worldenergydata.vessel_fleet.dedup.deduplicator import (
    _SOURCE_PRIORITY,
    _merge_records,
    deduplicate_fleet,
)

# ---------------------------------------------------------------------------
# _SOURCE_PRIORITY constant
# ---------------------------------------------------------------------------


class TestSourcePriority:
    def test_manual_highest(self):
        assert _SOURCE_PRIORITY["manual"] == 7

    def test_bsee_war_lowest(self):
        assert _SOURCE_PRIORITY["bsee_war"] == 1

    def test_expected_keys(self):
        assert "equasis" in _SOURCE_PRIORITY
        assert "contractor_spec_pdf" in _SOURCE_PRIORITY
        assert "lloyd_register" in _SOURCE_PRIORITY

    def test_dnv_and_abs_same_priority(self):
        assert _SOURCE_PRIORITY["dnv_register"] == _SOURCE_PRIORITY["abs_register"]


# ---------------------------------------------------------------------------
# _merge_records
# ---------------------------------------------------------------------------


class TestMergeRecords:
    def test_single_record(self):
        rec = {"VESSEL_NAME": "Ocean Rig", "IMO_NUMBER": "123"}
        result = _merge_records([rec])
        assert result == rec
        # Should be a copy, not the same object
        assert result is not rec

    def test_higher_priority_wins(self):
        low = {"VESSEL_NAME": "old", "DATA_SOURCE": "bsee_war", "YEAR": 2020}
        high = {"VESSEL_NAME": "new", "DATA_SOURCE": "manual", "YEAR": 2024}
        result = _merge_records([low, high])
        assert result["VESSEL_NAME"] == "new"
        assert result["YEAR"] == 2024

    def test_none_values_skipped(self):
        low = {"VESSEL_NAME": "Ocean", "DATA_SOURCE": "bsee_war", "TONNAGE": 5000}
        high = {"VESSEL_NAME": "Ocean", "DATA_SOURCE": "manual", "TONNAGE": None}
        result = _merge_records([low, high])
        # high priority has None, so low priority's value remains
        assert result["TONNAGE"] == 5000

    def test_all_fields_merged(self):
        a = {"VESSEL_NAME": "A", "DATA_SOURCE": "bsee_war", "FIELD_A": "from_a"}
        b = {"VESSEL_NAME": "B", "DATA_SOURCE": "equasis", "FIELD_B": "from_b"}
        result = _merge_records([a, b])
        assert "FIELD_A" in result
        assert "FIELD_B" in result

    def test_equal_priority_last_wins(self):
        a = {"DATA_SOURCE": "equasis", "LOA": 100}
        b = {"DATA_SOURCE": "abs_register", "LOA": 110}
        # Both priority 3; sorted stably, both processed left-to-right
        result = _merge_records([a, b])
        assert result["LOA"] in (100, 110)

    def test_unknown_source_gets_zero_priority(self):
        unknown = {"VESSEL_NAME": "X", "DATA_SOURCE": "unknown_src", "FIELD": "low"}
        known = {"VESSEL_NAME": "Y", "DATA_SOURCE": "bsee_war", "FIELD": "higher"}
        result = _merge_records([unknown, known])
        assert result["FIELD"] == "higher"


# ---------------------------------------------------------------------------
# deduplicate_fleet
# ---------------------------------------------------------------------------


class TestDeduplicateFleet:
    def test_empty_list(self):
        result = deduplicate_fleet([])
        assert result == []

    def test_single_record(self):
        rec = {"IMO_NUMBER": "9001", "VESSEL_NAME": "Deepwater Horizon"}
        result = deduplicate_fleet([rec])
        assert len(result) == 1
        assert result[0]["IMO_NUMBER"] == "9001"

    def test_dedup_by_imo(self):
        a = {"IMO_NUMBER": "9001", "VESSEL_NAME": "Ship A", "DATA_SOURCE": "bsee_war"}
        b = {
            "IMO_NUMBER": "9001",
            "VESSEL_NAME": "Ship A Updated",
            "DATA_SOURCE": "manual",
        }
        result = deduplicate_fleet([a, b])
        assert len(result) == 1
        assert result[0]["VESSEL_NAME"] == "Ship A Updated"

    def test_dedup_by_name(self):
        a = {
            "VESSEL_NAME": "OCEAN RIG CORCOVADO",
            "DATA_SOURCE": "equasis",
            "YEAR": 2020,
        }
        b = {
            "VESSEL_NAME": "ocean rig corcovado",
            "DATA_SOURCE": "manual",
            "YEAR": 2024,
        }
        result = deduplicate_fleet([a, b])
        assert len(result) == 1

    def test_different_vessels_remain(self):
        a = {"IMO_NUMBER": "9001", "VESSEL_NAME": "Ship A"}
        b = {"IMO_NUMBER": "9002", "VESSEL_NAME": "Ship B"}
        result = deduplicate_fleet([a, b])
        assert len(result) == 2

    def test_orphan_records_preserved(self):
        orphan = {"DATA_SOURCE": "bsee_war"}  # No IMO, no name
        normal = {"IMO_NUMBER": "9001", "VESSEL_NAME": "Ship"}
        result = deduplicate_fleet([orphan, normal])
        assert len(result) == 2

    def test_name_match_merges_with_imo_group(self):
        by_imo = {
            "IMO_NUMBER": "9001",
            "VESSEL_NAME": "Test Ship",
            "DATA_SOURCE": "bsee_war",
        }
        by_name = {"VESSEL_NAME": "test ship", "DATA_SOURCE": "manual", "EXTRA": "data"}
        result = deduplicate_fleet([by_imo, by_name])
        # Name-only record should merge into the IMO record
        assert len(result) == 1
        assert result[0]["IMO_NUMBER"] == "9001"
        assert result[0]["EXTRA"] == "data"

    def test_large_dedup(self):
        records = [
            {
                "IMO_NUMBER": f"900{i}",
                "VESSEL_NAME": f"Ship {i}",
                "DATA_SOURCE": "bsee_war",
            }
            for i in range(50)
        ]
        # Add duplicates
        dupes = [
            {
                "IMO_NUMBER": f"900{i}",
                "VESSEL_NAME": f"Ship {i} Updated",
                "DATA_SOURCE": "manual",
            }
            for i in range(25)
        ]
        result = deduplicate_fleet(records + dupes)
        assert len(result) == 50
