"""Tests for the XLS fleet parser."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.vessel_fleet.parsers.xls import XlsFleetParser


@pytest.fixture
def sample_xls(tmp_path):
    """Create a minimal transposed XLS file for testing."""
    # Row 0: blank + rig names
    # Rows 1+: field label + values per rig
    data = {
        0: ["", "DEEPWATER TITAN", "OCEAN STAR", "TEST RIG"],
        1: ["VESSEL TYPE", "DS", "SS", "DS"],
        2: ["VESSEL DESIGN", "Samsung 12000", "Aker H-6e", "RBS-8M"],
        3: ["CONSTRUCTION DATE (yr.)", "2014", "2008", ""],
        4: [
            "MAXIMUM WATER DEPTH RATING (ft.)",
            "12,000 ft.",
            "8000",
            "7,500 ft.",
        ],
        5: [
            "MAXIMUM DRILLING DEPTH (ft.)",
            "40000",
            "30,000 ft.",
            "35000",
        ],
        6: ["LENGTH (ft.)", "750 ft.", "392", ""],
        7: ["WIDTH (ft.)", "120", "256 ft.", ""],
        8: ["D.P. RATING", "DP3", "DP2", "N/A"],
        9: [
            "MOONPOOL LENGTH (ft.)",
            "89.2 ft. x 36.7 ft.",
            "20 x 40",
            "25",
        ],
        10: ["BOP OPERATING PRESSURE (Ksi)", "15", "10", ""],
        11: ["QUARTERS CAPACITY (persons)", "200", "150", ""],
        12: ["MUD PUMPS No.", "4", "3", ""],
    }

    df = pd.DataFrame(data).T
    xls_path = tmp_path / "test_rigs.xlsx"
    df.to_excel(str(xls_path), index=False, header=False, engine="openpyxl")
    return xls_path


class TestXlsFleetParser:
    def test_parse_returns_list(self, sample_xls):
        parser = XlsFleetParser(sample_xls)
        records = parser.parse()
        assert isinstance(records, list)

    def test_parse_correct_count(self, sample_xls):
        parser = XlsFleetParser(sample_xls)
        records = parser.parse()
        assert len(records) == 3

    def test_vessel_name(self, sample_xls):
        parser = XlsFleetParser(sample_xls)
        records = parser.parse()
        assert records[0]["VESSEL_NAME"] == "DEEPWATER TITAN"

    def test_rig_type_mapping(self, sample_xls):
        parser = XlsFleetParser(sample_xls)
        records = parser.parse()
        assert records[0]["RIG_TYPE"] == "drillship"
        assert records[1]["RIG_TYPE"] == "semi_submersible"

    def test_water_depth_parsed(self, sample_xls):
        parser = XlsFleetParser(sample_xls)
        records = parser.parse()
        assert records[0]["WATER_DEPTH_RATING_FT"] == 12000.0
        assert records[1]["WATER_DEPTH_RATING_FT"] == 8000.0
        assert records[2]["WATER_DEPTH_RATING_FT"] == 7500.0

    def test_year_built(self, sample_xls):
        parser = XlsFleetParser(sample_xls)
        records = parser.parse()
        assert records[0]["YEAR_BUILT"] == 2014
        assert records[1]["YEAR_BUILT"] == 2008

    def test_loa_converted_to_metres(self, sample_xls):
        parser = XlsFleetParser(sample_xls)
        records = parser.parse()
        # 750 ft * 0.3048 = 228.6 m
        assert abs(records[0]["LOA_M"] - 228.6) < 0.1

    def test_dp_class_parsed(self, sample_xls):
        parser = XlsFleetParser(sample_xls)
        records = parser.parse()
        assert records[0]["DP_CLASS"] == 3
        assert records[1]["DP_CLASS"] == 2

    def test_moonpool_compound(self, sample_xls):
        parser = XlsFleetParser(sample_xls)
        records = parser.parse()
        # "89.2 ft. x 36.7 ft." -> 27.19m x 11.19m
        assert abs(records[0]["MOONPOOL_LENGTH_M"] - 27.19) < 0.1
        assert abs(records[0]["MOONPOOL_WIDTH_M"] - 11.19) < 0.1

    def test_bop_pressure_converted(self, sample_xls):
        parser = XlsFleetParser(sample_xls)
        records = parser.parse()
        # 15 Ksi = 15000 PSI
        assert records[0]["BOP_PRESSURE_PSI"] == 15000.0

    def test_data_source_set(self, sample_xls):
        parser = XlsFleetParser(sample_xls)
        records = parser.parse()
        assert records[0]["DATA_SOURCE"] == "xls_historical"

    def test_is_offshore_set(self, sample_xls):
        parser = XlsFleetParser(sample_xls)
        records = parser.parse()
        assert records[0]["IS_OFFSHORE"] is True

    def test_hull_form_type_drillship(self, sample_xls):
        parser = XlsFleetParser(sample_xls)
        records = parser.parse()
        assert records[0]["HULL_FORM_TYPE"] == "drillship"

    def test_hull_form_type_semi_sub(self, sample_xls):
        parser = XlsFleetParser(sample_xls)
        records = parser.parse()
        assert records[1]["HULL_FORM_TYPE"] == "semi_sub"

    def test_rig_name_set(self, sample_xls):
        parser = XlsFleetParser(sample_xls)
        records = parser.parse()
        assert records[0]["RIG_NAME"] == "DEEPWATER TITAN"
        assert records[0]["RIG_NAME"] == records[0]["VESSEL_NAME"]


class TestXlsRealData:
    """Integration test with real XLS data (skipped if file not present)."""

    @pytest.fixture
    def real_xls_output(self):
        # vessel_fleet data ships INSIDE the member as package data (#529 batch
        # 4, option (i)); the XLS-ingest output (if generated) lives under the
        # member's _data/ tree, not the repo-root data/modules tree.
        pq = (
            Path(__file__).resolve().parents[4]
            / "packages"
            / "worldenergydata-vessel_fleet"
            / "src"
            / "worldenergydata"
            / "vessel_fleet"
            / "_data"
            / "raw"
            / "xls_historical"
            / "floaters.parquet"
        )
        if not pq.exists():
            pytest.skip("XLS ingest not run (floaters.parquet missing)")
        return pd.read_parquet(pq).to_dict("records")

    def test_real_count_at_least_150(self, real_xls_output):
        assert len(real_xls_output) >= 150

    def test_real_hull_form_type_populated(self, real_xls_output):
        populated = sum(1 for r in real_xls_output if r.get("HULL_FORM_TYPE"))
        assert populated >= 140

    def test_real_rig_name_matches_vessel_name(self, real_xls_output):
        for r in real_xls_output:
            assert r.get("RIG_NAME") == r.get("VESSEL_NAME")

    def test_real_loa_populated(self, real_xls_output):
        populated = sum(1 for r in real_xls_output if r.get("LOA_M"))
        assert populated >= 140

    def test_real_only_floater_types(self, real_xls_output):
        import math

        expected = {"semi_submersible", "drillship"}
        for r in real_xls_output:
            rig_type = r.get("RIG_TYPE")
            # Parquet round-trip turns None → NaN; allow both
            if rig_type is None or (
                isinstance(rig_type, float) and math.isnan(rig_type)
            ):
                continue
            assert rig_type in expected, f"Unexpected type: {rig_type}"


class TestXlsFleetParserMalformedTypes:
    """Verify multi-word vessel type codes are handled correctly."""

    @pytest.fixture
    def malformed_xls(self, tmp_path):
        data = {
            0: ["", "RIG ALPHA", "RIG BETA"],
            1: ["VESSEL TYPE", "SS F&G 9500", "DS Gusto, MSC Bully PRD"],
            2: ["MAXIMUM WATER DEPTH RATING (ft.)", "8000", "12000"],
        }
        df = pd.DataFrame(data).T
        xls_path = tmp_path / "malformed.xlsx"
        df.to_excel(str(xls_path), index=False, header=False, engine="openpyxl")
        return xls_path

    def test_malformed_ss_maps_correctly(self, malformed_xls):
        parser = XlsFleetParser(malformed_xls)
        records = parser.parse()
        assert records[0]["RIG_TYPE"] == "semi_submersible"
        assert records[0]["HULL_FORM_TYPE"] == "semi_sub"

    def test_malformed_ds_maps_correctly(self, malformed_xls):
        parser = XlsFleetParser(malformed_xls)
        records = parser.parse()
        assert records[1]["RIG_TYPE"] == "drillship"
        assert records[1]["HULL_FORM_TYPE"] == "drillship"
