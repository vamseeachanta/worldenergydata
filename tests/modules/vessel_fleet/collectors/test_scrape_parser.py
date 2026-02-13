"""Tests for the Puppeteer scrape JSON parser.

Validates Noble and Seadrill JSON parsing into vessel fleet records
with correct field mapping, type classification, and water depth parsing.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any

import pytest

from worldenergydata.vessel_fleet.collectors.scrape_parser import (
    classify_rig_type_by_water_depth,
    parse_noble_scrape,
    parse_seadrill_scrape,
    parse_water_depth_string,
)

# ---------------------------------------------------------------------------
# Paths to real scrape data
# ---------------------------------------------------------------------------
_DATA_DIR = Path(
    "/mnt/local-analysis/workspace-hub/worldenergydata"
    "/data/modules/vessel_fleet/raw/contractor_scrape"
)
NOBLE_JSON = _DATA_DIR / "noble.json"
SEADRILL_JSON = _DATA_DIR / "seadrill.json"


# ===================================================================
# classify_rig_type_by_water_depth
# ===================================================================
class TestClassifyRigTypeByWaterDepth:
    """Rig type classification based on water depth rating."""

    def test_jack_up_shallow(self):
        assert classify_rig_type_by_water_depth(350.0) == "jack_up"

    def test_jack_up_boundary(self):
        assert classify_rig_type_by_water_depth(500.0) == "jack_up"

    def test_semi_submersible_mid(self):
        assert classify_rig_type_by_water_depth(6000.0) == "semi_submersible"

    def test_semi_submersible_lower_boundary(self):
        # Just above 500
        assert classify_rig_type_by_water_depth(501.0) == "semi_submersible"

    def test_drillship_deep(self):
        assert classify_rig_type_by_water_depth(12000.0) == "drillship"

    def test_drillship_boundary(self):
        # At 10000 ft threshold
        assert classify_rig_type_by_water_depth(10000.0) == "drillship"

    def test_zero_depth(self):
        assert classify_rig_type_by_water_depth(0.0) == "jack_up"

    def test_negative_depth_returns_jack_up(self):
        assert classify_rig_type_by_water_depth(-10.0) == "jack_up"


# ===================================================================
# parse_water_depth_string
# ===================================================================
class TestParseWaterDepthString:
    """Water depth string parsing to float."""

    def test_comma_separated_with_ft(self):
        assert parse_water_depth_string("12,000 ft") == 12000.0

    def test_comma_separated_no_unit(self):
        assert parse_water_depth_string("6,000") == 6000.0

    def test_plain_number(self):
        assert parse_water_depth_string("492") == 492.0

    def test_with_extra_spaces(self):
        assert parse_water_depth_string("  1,500 ft ") == 1500.0

    def test_none_returns_none(self):
        assert parse_water_depth_string(None) is None

    def test_empty_string_returns_none(self):
        assert parse_water_depth_string("") is None

    def test_non_numeric_returns_none(self):
        assert parse_water_depth_string("Available") is None

    def test_with_ft_period(self):
        assert parse_water_depth_string("8,000 ft.") == 8000.0


# ===================================================================
# parse_noble_scrape — full data
# ===================================================================
class TestParseNobleScrape:
    """Parse Noble Corporation scrape JSON into vessel fleet records."""

    @pytest.fixture(scope="class")
    def noble_records(self) -> list[dict[str, Any]]:
        return parse_noble_scrape(NOBLE_JSON)

    def test_record_count(self, noble_records):
        assert len(noble_records) == 31

    def test_all_have_vessel_name(self, noble_records):
        for rec in noble_records:
            assert rec["VESSEL_NAME"], f"Missing VESSEL_NAME: {rec}"

    def test_all_have_data_source(self, noble_records):
        for rec in noble_records:
            assert rec["DATA_SOURCE"] == "contractor_fleet_page"

    def test_all_have_vessel_category(self, noble_records):
        for rec in noble_records:
            assert rec["VESSEL_CATEGORY"] == "drilling_rig"

    def test_all_have_owner(self, noble_records):
        for rec in noble_records:
            assert rec["OWNER"] == "Noble Corporation plc"

    def test_known_vessel_present(self, noble_records):
        names = {r["VESSEL_NAME"] for r in noble_records}
        assert "Noble BlackHawk" in names

    def test_water_depth_parsed_as_float(self, noble_records):
        blackhawk = next(
            r for r in noble_records if r["VESSEL_NAME"] == "Noble BlackHawk"
        )
        assert blackhawk["WATER_DEPTH_RATING_FT"] == 12000.0

    def test_rig_design_extracted(self, noble_records):
        blackhawk = next(
            r for r in noble_records if r["VESSEL_NAME"] == "Noble BlackHawk"
        )
        assert blackhawk.get("RIG_DESIGN") == "Gusto P10000"

    def test_rig_type_classification(self, noble_records):
        # Noble Innovator has 492 ft WD -> jack_up
        innovator = next(
            r for r in noble_records if r["VESSEL_NAME"] == "Noble Innovator"
        )
        assert innovator["RIG_TYPE"] == "jack_up"

    def test_drillship_classification(self, noble_records):
        # BlackHawk 12,000 ft WD -> drillship
        blackhawk = next(
            r for r in noble_records if r["VESSEL_NAME"] == "Noble BlackHawk"
        )
        assert blackhawk["RIG_TYPE"] == "drillship"

    def test_semi_submersible_classification(self, noble_records):
        # Ocean Apex 6,000 ft WD -> semi_submersible
        apex = next(
            r for r in noble_records if r["VESSEL_NAME"] == "Ocean Apex"
        )
        assert apex["RIG_TYPE"] == "semi_submersible"

    def test_pdf_spec_link_extracted(self, noble_records):
        blackhawk = next(
            r for r in noble_records if r["VESSEL_NAME"] == "Noble BlackHawk"
        )
        url = blackhawk.get("DATA_SOURCE_URL", "")
        assert url.endswith(".pdf")

    def test_no_duplicate_names(self, noble_records):
        names = [r["VESSEL_NAME"] for r in noble_records]
        assert len(names) == len(set(names))


# ===================================================================
# parse_seadrill_scrape — full data
# ===================================================================
class TestParseSeadrillScrape:
    """Parse Seadrill scrape JSON into vessel fleet records."""

    @pytest.fixture(scope="class")
    def seadrill_records(self) -> list[dict[str, Any]]:
        return parse_seadrill_scrape(SEADRILL_JSON)

    def test_record_count(self, seadrill_records):
        assert len(seadrill_records) == 17

    def test_all_have_vessel_name(self, seadrill_records):
        for rec in seadrill_records:
            assert rec["VESSEL_NAME"], f"Missing VESSEL_NAME: {rec}"

    def test_all_have_data_source(self, seadrill_records):
        for rec in seadrill_records:
            assert rec["DATA_SOURCE"] == "contractor_fleet_page"

    def test_all_have_vessel_category(self, seadrill_records):
        for rec in seadrill_records:
            assert rec["VESSEL_CATEGORY"] == "drilling_rig"

    def test_known_vessel_present(self, seadrill_records):
        names = {r["VESSEL_NAME"] for r in seadrill_records}
        assert "West Neptune" in names

    def test_rig_type_from_explicit_label(self, seadrill_records):
        neptune = next(
            r for r in seadrill_records if r["VESSEL_NAME"] == "West Neptune"
        )
        assert neptune["RIG_TYPE"] == "drillship"

    def test_semi_submersible_type(self, seadrill_records):
        aquarius = next(
            r for r in seadrill_records if r["VESSEL_NAME"] == "West Aquarius"
        )
        assert aquarius["RIG_TYPE"] == "semi_submersible"

    def test_jack_up_type(self, seadrill_records):
        elara = next(
            r for r in seadrill_records if r["VESSEL_NAME"] == "West Elara"
        )
        assert elara["RIG_TYPE"] == "jack_up"

    def test_owner_varies(self, seadrill_records):
        """Seadrill has mixed ownership (Seadrill Limited, Sonadrill)."""
        libongos = next(
            r for r in seadrill_records
            if r["VESSEL_NAME"] == "Sonangol Libongos"
        )
        assert libongos["OWNER"] == "Sonadrill Holding Ltd"

    def test_default_owner_is_seadrill(self, seadrill_records):
        neptune = next(
            r for r in seadrill_records if r["VESSEL_NAME"] == "West Neptune"
        )
        assert neptune["OWNER"] == "Seadrill Limited"

    def test_tech_sheet_link_extracted(self, seadrill_records):
        neptune = next(
            r for r in seadrill_records if r["VESSEL_NAME"] == "West Neptune"
        )
        url = neptune.get("DATA_SOURCE_URL", "")
        assert url.endswith(".pdf")

    def test_no_duplicate_names(self, seadrill_records):
        names = [r["VESSEL_NAME"] for r in seadrill_records]
        assert len(names) == len(set(names))


# ===================================================================
# Edge cases / graceful handling
# ===================================================================
class TestEdgeCases:
    """Graceful handling of missing or malformed data."""

    def test_noble_missing_fields_handled(self):
        """Records with partial data should still parse."""
        records = parse_noble_scrape(NOBLE_JSON)
        for rec in records:
            # All records must have at least these required fields
            assert "VESSEL_NAME" in rec
            assert "DATA_SOURCE" in rec
            assert "VESSEL_CATEGORY" in rec

    def test_seadrill_missing_fields_handled(self):
        records = parse_seadrill_scrape(SEADRILL_JSON)
        for rec in records:
            assert "VESSEL_NAME" in rec
            assert "DATA_SOURCE" in rec
            assert "VESSEL_CATEGORY" in rec

    def test_noble_nonexistent_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            parse_noble_scrape(tmp_path / "nonexistent.json")

    def test_seadrill_nonexistent_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            parse_seadrill_scrape(tmp_path / "nonexistent.json")

    def test_noble_empty_json_returns_empty(self, tmp_path):
        empty = tmp_path / "empty.json"
        empty.write_text(json.dumps({
            "name": "noble",
            "owner": "Noble Corporation",
            "links": [],
            "rawHtml": "",
        }))
        result = parse_noble_scrape(empty)
        assert result == []

    def test_seadrill_empty_json_returns_empty(self, tmp_path):
        empty = tmp_path / "empty.json"
        empty.write_text(json.dumps({
            "name": "seadrill",
            "owner": "Seadrill Limited",
            "links": [],
            "rawHtml": "",
        }))
        result = parse_seadrill_scrape(empty)
        assert result == []
