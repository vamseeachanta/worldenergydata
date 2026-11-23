"""Unit tests for the BSEE pipeline casing schematic generator.

Tests the CasingString dataclass, load_well_casing(), casing_matrix(),
and render_casing_svg() functions.  All tests use synthetic data --
no real CSV files required.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import FrozenInstanceError
from pathlib import Path
from textwrap import dedent

import pandas as pd
import pytest

from worldenergydata.bsee.pipeline.casing_schematic import (
    CasingString,
    casing_matrix,
    load_well_casing,
    render_casing_svg,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_string(
    interval_type: str = "C",
    hole_size: float = 12.25,
    casing_size: float = 9.625,
    casing_weight: float = 53.5,
    casing_grade: str = "P-110",
    top_md: float = 0.0,
    bottom_md: float = 10000.0,
    liner_test_psi: float | None = 5000.0,
    shoe_test_psi: float | None = 15.0,
    cement_vol_bbl: float | None = 800.0,
) -> CasingString:
    return CasingString(
        interval_type=interval_type,
        hole_size=hole_size,
        casing_size=casing_size,
        casing_weight=casing_weight,
        casing_grade=casing_grade,
        top_md=top_md,
        bottom_md=bottom_md,
        liner_test_psi=liner_test_psi,
        shoe_test_psi=shoe_test_psi,
        cement_vol_bbl=cement_vol_bbl,
    )


SAMPLE_STRINGS = [
    _make_string(
        interval_type="D",
        hole_size=36.0,
        casing_size=30.0,
        casing_weight=310.0,
        casing_grade="X-56",
        top_md=0.0,
        bottom_md=500.0,
        liner_test_psi=None,
        shoe_test_psi=None,
        cement_vol_bbl=1200.0,
    ),
    _make_string(
        interval_type="C",
        hole_size=26.0,
        casing_size=20.0,
        casing_weight=133.0,
        casing_grade="K-55",
        top_md=0.0,
        bottom_md=3000.0,
        liner_test_psi=2000.0,
        shoe_test_psi=12.5,
        cement_vol_bbl=3000.0,
    ),
    _make_string(
        interval_type="C",
        hole_size=17.5,
        casing_size=13.375,
        casing_weight=72.0,
        casing_grade="P-110",
        top_md=0.0,
        bottom_md=8000.0,
        liner_test_psi=4500.0,
        shoe_test_psi=14.8,
        cement_vol_bbl=1500.0,
    ),
    _make_string(
        interval_type="L",
        hole_size=12.25,
        casing_size=9.625,
        casing_weight=53.5,
        casing_grade="P-110",
        top_md=7500.0,
        bottom_md=12000.0,
        liner_test_psi=6000.0,
        shoe_test_psi=16.2,
        cement_vol_bbl=400.0,
    ),
]


CSV_HEADER = (
    "API_WELL_NUMBER,WELL_NAME,WAR_START_DT,WAR_END_DT,"
    "CSNG_INTV_TYPE_CD,CSNG_HOLE_SIZE,CASING_SIZE,CASING_WEIGHT,"
    "CASING_GRADE,CSNG_LINER_TEST_PRSS,CSNG_SHOE_TEST_PRSS,"
    "CSNG_CEMENT_VOL,SN_WAR_CSNG_INTV,CSNG_SETTING_BOTM_MD,"
    "CSNG_SETTING_TOP_MD"
)


def _write_csv(path: Path, rows: list[str]) -> Path:
    """Write a CSV with header and rows to *path*."""
    path.write_text(CSV_HEADER + "\n" + "\n".join(rows) + "\n")
    return path


# ---------------------------------------------------------------------------
# CasingString dataclass
# ---------------------------------------------------------------------------


class TestCasingString:
    def test_casing_string_creation(self):
        cs = _make_string()
        assert cs.interval_type == "C"
        assert cs.hole_size == 12.25
        assert cs.casing_size == 9.625
        assert cs.casing_weight == 53.5
        assert cs.casing_grade == "P-110"
        assert cs.top_md == 0.0
        assert cs.bottom_md == 10000.0
        assert cs.liner_test_psi == 5000.0
        assert cs.shoe_test_psi == 15.0
        assert cs.cement_vol_bbl == 800.0

    def test_casing_string_frozen(self):
        cs = _make_string()
        with pytest.raises(FrozenInstanceError):
            cs.hole_size = 99.0  # type: ignore[misc]

    def test_casing_string_optional_none(self):
        cs = _make_string(liner_test_psi=None, shoe_test_psi=None, cement_vol_bbl=None)
        assert cs.liner_test_psi is None
        assert cs.shoe_test_psi is None
        assert cs.cement_vol_bbl is None


# ---------------------------------------------------------------------------
# load_well_casing
# ---------------------------------------------------------------------------


class TestLoadWellCasing:
    def test_load_well_casing_missing_file(self):
        result = load_well_casing("999999999999", Path("/nonexistent/file.csv"))
        assert result == []

    def test_load_well_casing_empty_csv(self, tmp_path):
        csv = _write_csv(tmp_path / "tubulars.csv", [])
        result = load_well_casing("999999999999", csv)
        assert result == []

    def test_load_well_casing_filters_by_api12(self, tmp_path):
        rows = [
            "111111111111,W1,1/1/2024 12:01:00 AM,1/7/2024 11:59:00 PM,"
            "C,26.0,20.0,133.0,K-55,2000.0,12.5,3000.0,-100,3000,0",
            "222222222222,W2,1/1/2024 12:01:00 AM,1/7/2024 11:59:00 PM,"
            "C,17.5,13.375,72.0,P-110,4500.0,14.8,1500.0,-200,8000,0",
        ]
        csv = _write_csv(tmp_path / "tubulars.csv", rows)
        result = load_well_casing("111111111111", csv)
        assert len(result) == 1
        assert result[0].casing_size == 20.0

    def test_load_well_casing_latest_war(self, tmp_path):
        # Two WAR periods for same well; only latest kept.
        rows = [
            "111111111111,W1,1/1/2023 12:01:00 AM,1/7/2023 11:59:00 PM,"
            "C,26.0,20.0,100.0,K-55,2000.0,12.5,3000.0,-100,3000,0",
            "111111111111,W1,6/1/2024 12:01:00 AM,6/7/2024 11:59:00 PM,"
            "C,26.0,20.0,133.0,X-80,2500.0,13.0,3200.0,-200,3100,0",
            "111111111111,W1,6/1/2024 12:01:00 AM,6/7/2024 11:59:00 PM,"
            "C,17.5,13.375,72.0,P-110,4500.0,14.8,1500.0,-300,8000,0",
        ]
        csv = _write_csv(tmp_path / "tubulars.csv", rows)
        result = load_well_casing("111111111111", csv)
        # Old WAR row (K-55 from 2023) should be excluded
        assert len(result) == 2
        grades = [r.casing_grade for r in result]
        assert "K-55" not in grades
        assert "X-80" in grades
        assert "P-110" in grades

    def test_load_well_casing_sorted_by_hole_size(self, tmp_path):
        rows = [
            "111111111111,W1,1/1/2024 12:01:00 AM,1/7/2024 11:59:00 PM,"
            "C,12.25,9.625,53.5,P-110,5000.0,15.0,800.0,-100,10000,0",
            "111111111111,W1,1/1/2024 12:01:00 AM,1/7/2024 11:59:00 PM,"
            "C,26.0,20.0,133.0,K-55,2000.0,12.5,3000.0,-200,3000,0",
            "111111111111,W1,1/1/2024 12:01:00 AM,1/7/2024 11:59:00 PM,"
            "D,36.0,30.0,310.0,X-56,,,,0,500,0",
        ]
        csv = _write_csv(tmp_path / "tubulars.csv", rows)
        result = load_well_casing("111111111111", csv)
        assert len(result) == 3
        # Sorted descending by hole size
        assert result[0].hole_size == 36.0
        assert result[1].hole_size == 26.0
        assert result[2].hole_size == 12.25

    def test_load_well_casing_handles_missing_numeric_fields(self, tmp_path):
        rows = [
            "111111111111,W1,1/1/2024 12:01:00 AM,1/7/2024 11:59:00 PM,"
            "L,12.25,9.625,53.5,P-110,,,400.0,-100,10000,7500",
        ]
        csv = _write_csv(tmp_path / "tubulars.csv", rows)
        result = load_well_casing("111111111111", csv)
        assert len(result) == 1
        assert result[0].liner_test_psi is None
        assert result[0].shoe_test_psi is None
        assert result[0].cement_vol_bbl == 400.0


# ---------------------------------------------------------------------------
# casing_matrix
# ---------------------------------------------------------------------------


class TestCasingMatrix:
    def test_casing_matrix_columns(self):
        df = casing_matrix(SAMPLE_STRINGS)
        expected_cols = [
            "Type",
            "Hole Size (in)",
            "Casing OD (in)",
            "Weight (lb/ft)",
            "Grade",
            "Top MD (ft)",
            "Bottom MD (ft)",
            "Test Pressure (psi)",
            "Shoe Test (psi)",
            "Cement (bbl)",
        ]
        assert list(df.columns) == expected_cols

    def test_casing_matrix_type_labels(self):
        df = casing_matrix(SAMPLE_STRINGS)
        types = df["Type"].tolist()
        assert types[0] == "Drive Pipe"
        assert types[1] == "Casing"
        assert types[2] == "Casing"
        assert types[3] == "Liner"

    def test_casing_matrix_row_count(self):
        df = casing_matrix(SAMPLE_STRINGS)
        assert len(df) == len(SAMPLE_STRINGS)

    def test_casing_matrix_empty(self):
        df = casing_matrix([])
        assert df.empty
        assert len(df) == 0

    def test_casing_matrix_sorted_outer_to_inner(self):
        # Input in random order; output should be sorted by hole size desc
        shuffled = [
            SAMPLE_STRINGS[2],
            SAMPLE_STRINGS[0],
            SAMPLE_STRINGS[3],
            SAMPLE_STRINGS[1],
        ]
        df = casing_matrix(shuffled)
        hole_sizes = df["Hole Size (in)"].tolist()
        assert hole_sizes == sorted(hole_sizes, reverse=True)


# ---------------------------------------------------------------------------
# render_casing_svg
# ---------------------------------------------------------------------------


class TestRenderCasingSvg:
    def test_render_casing_svg_valid_xml(self):
        svg = render_casing_svg(SAMPLE_STRINGS, well_name="TEST-001")
        root = ET.fromstring(svg)
        assert root.tag == "{http://www.w3.org/2000/svg}svg" or root.tag == "svg"

    def test_render_casing_svg_contains_well_name(self):
        svg = render_casing_svg(SAMPLE_STRINGS, well_name="DEEP-BLUE-7")
        assert "DEEP-BLUE-7" in svg

    def test_render_casing_svg_empty_data(self):
        svg = render_casing_svg([], well_name="EMPTY")
        root = ET.fromstring(svg)
        assert "No casing data available" in svg

    def test_render_casing_svg_contains_annotations(self):
        svg = render_casing_svg(SAMPLE_STRINGS, well_name="TEST")
        # Each casing shoe should have an annotation with size and grade
        assert "9.625" in svg
        assert "P-110" in svg
        assert "30.0" in svg or "30" in svg

    def test_render_casing_svg_has_depth_axis(self):
        svg = render_casing_svg(SAMPLE_STRINGS, well_name="TEST")
        # Should contain depth labels along the y-axis
        # The max depth is 12000 ft, so we expect at least some depth ticks
        assert "Measured Depth" in svg or "MD" in svg

    def test_render_casing_svg_default_title_no_name(self):
        svg = render_casing_svg(SAMPLE_STRINGS)
        assert "Casing Program" in svg

    def test_render_casing_svg_color_coded(self):
        svg = render_casing_svg(SAMPLE_STRINGS, well_name="TEST")
        # Should contain the color codes for each type
        assert "#795548" in svg  # Drive Pipe (brown)
        assert "#1565c0" in svg  # Casing (blue)
        assert "#2e7d32" in svg  # Liner (green)

    def test_render_casing_svg_escapes_special_chars(self):
        # Well name with special XML characters
        strings = [_make_string(casing_grade="L&T <special>")]
        svg = render_casing_svg(strings, well_name="Well <A&B>")
        # Must be valid XML despite special characters
        root = ET.fromstring(svg)
        assert "Well" in svg

    def test_render_casing_svg_canvas_dimensions(self):
        svg = render_casing_svg(SAMPLE_STRINGS, well_name="TEST")
        root = ET.fromstring(svg)
        assert root.attrib.get("width") == "600"
        assert root.attrib.get("height") == "800"
