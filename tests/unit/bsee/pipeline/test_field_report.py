"""Tests for BSEE pipeline HTML report generation.

TDD red phase: these tests define the expected behaviour of
``field_report.render_html`` and ``field_report.save_report``.
"""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee.pipeline.casing_schematic import CasingString
from worldenergydata.bsee.pipeline.field_query import FieldContext
from worldenergydata.bsee.pipeline.pipeline_runner import FieldReport

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_context(**overrides) -> FieldContext:
    defaults = dict(
        field_code="001",
        field_name="BUCKSKIN",
        leases=("G12345", "G12346"),
        area_code="GC",
        geological_era="Miocene",
        well_count=5,
        query_type="field_name",
    )
    defaults.update(overrides)
    return FieldContext(**defaults)


def _make_casing_string(**overrides) -> CasingString:
    defaults = dict(
        interval_type="C",
        hole_size=26.0,
        casing_size=20.0,
        casing_weight=133.0,
        casing_grade="X-56",
        top_md=0.0,
        bottom_md=2500.0,
        liner_test_psi=3000.0,
        shoe_test_psi=2500.0,
        cement_vol_bbl=800.0,
    )
    defaults.update(overrides)
    return CasingString(**defaults)


@pytest.fixture
def sample_report() -> FieldReport:
    """Build a FieldReport with synthetic data for testing."""
    context = _make_context()
    production = pd.DataFrame(
        {
            "FIELD_CODE": ["001"],
            "FIELD_NAME": ["BUCKSKIN"],
            "CUM_OIL_MMBBL": [45.2],
            "CUM_GAS_BCF": [120.5],
            "PEAK_OIL_BOPD": [25000.0],
            "WELL_COUNT": [5],
        }
    )

    cs1 = _make_casing_string()
    cs2 = _make_casing_string(
        interval_type="L",
        hole_size=12.25,
        casing_size=9.625,
        casing_weight=53.5,
        casing_grade="P-110",
        top_md=8000.0,
        bottom_md=12000.0,
        liner_test_psi=8500.0,
        shoe_test_psi=7200.0,
        cement_vol_bbl=350.0,
    )

    from worldenergydata.bsee.pipeline.casing_schematic import (
        casing_matrix,
        render_casing_svg,
    )

    strings = [cs1, cs2]
    matrix_df = casing_matrix(strings)
    svg_str = render_casing_svg(strings, well_name="608174000100")

    activity = {
        "drilling_efficiency": {
            "by_rig_type": pd.DataFrame(
                {
                    "RIG_TYPE": ["SS", "JU"],
                    "AVG_DAYS": [45.2, 32.1],
                    "WELL_COUNT": [3, 2],
                }
            ),
        },
        "well_depth": {
            "by_depth_class": pd.DataFrame(
                {
                    "DEPTH_CLASS": ["Deep", "Ultra-Deep"],
                    "COUNT": [3, 2],
                    "AVG_DEPTH_FT": [18500.0, 25000.0],
                }
            ),
        },
    }

    return FieldReport(
        context=context,
        generated_at="2026-02-13T12:00:00+00:00",
        production_summary=production,
        activity_analysis=activity,
        casing_strings={"608174000100": strings},
        casing_matrices={"608174000100": matrix_df},
        casing_svgs={"608174000100": svg_str},
        wellbore_count=5,
        lease_count=2,
        warnings=["LFS stub detected", "Casing analysis partial"],
    )


@pytest.fixture
def empty_report() -> FieldReport:
    """Build a FieldReport with all-empty optional data."""
    context = _make_context(field_name="EMPTY FIELD", well_count=0)
    return FieldReport(
        context=context,
        generated_at="2026-02-13T12:00:00+00:00",
        production_summary=pd.DataFrame(),
        activity_analysis={},
        casing_strings={},
        casing_matrices={},
        casing_svgs={},
        wellbore_count=0,
        lease_count=0,
        warnings=[],
    )


# ---------------------------------------------------------------------------
# Tests — render_html basic behaviour
# ---------------------------------------------------------------------------


class TestRenderHtmlBasic:
    """Basic return type and structure checks."""

    def test_render_html_returns_string(self, sample_report: FieldReport) -> None:
        from worldenergydata.bsee.pipeline.field_report import render_html

        result = render_html(sample_report)
        assert isinstance(result, str)

    def test_render_html_valid_html(self, sample_report: FieldReport) -> None:
        from worldenergydata.bsee.pipeline.field_report import render_html

        result = render_html(sample_report)
        assert "<!DOCTYPE html>" in result
        assert "<html" in result
        assert "</html>" in result

    def test_render_html_contains_field_name(self, sample_report: FieldReport) -> None:
        from worldenergydata.bsee.pipeline.field_report import render_html

        result = render_html(sample_report)
        assert "BUCKSKIN" in result

    def test_render_html_contains_field_code(self, sample_report: FieldReport) -> None:
        from worldenergydata.bsee.pipeline.field_report import render_html

        result = render_html(sample_report)
        assert "001" in result

    def test_render_html_contains_era(self, sample_report: FieldReport) -> None:
        from worldenergydata.bsee.pipeline.field_report import render_html

        result = render_html(sample_report)
        assert "Miocene" in result

    def test_render_html_contains_timestamp(self, sample_report: FieldReport) -> None:
        from worldenergydata.bsee.pipeline.field_report import render_html

        result = render_html(sample_report)
        assert "2026-02-13" in result

    def test_render_html_contains_summary_cards(
        self, sample_report: FieldReport
    ) -> None:
        from worldenergydata.bsee.pipeline.field_report import render_html

        result = render_html(sample_report)
        # Should show well count, lease count, area code, query type
        assert "Well Count" in result or "well-count" in result.lower()
        assert "5" in result  # well count value
        assert "GC" in result  # area code


# ---------------------------------------------------------------------------
# Tests — production section
# ---------------------------------------------------------------------------


class TestProductionSection:
    """Tests for the production summary section."""

    def test_render_html_contains_production_table(
        self, sample_report: FieldReport
    ) -> None:
        from worldenergydata.bsee.pipeline.field_report import render_html

        result = render_html(sample_report)
        assert "45.2" in result  # CUM_OIL_MMBBL
        assert "120.5" in result  # CUM_GAS_BCF

    def test_render_html_empty_production(self, empty_report: FieldReport) -> None:
        from worldenergydata.bsee.pipeline.field_report import render_html

        result = render_html(empty_report)
        assert "No production data available" in result


# ---------------------------------------------------------------------------
# Tests — casing section
# ---------------------------------------------------------------------------


class TestCasingSection:
    """Tests for the casing schematics section."""

    def test_render_html_contains_casing_svg(self, sample_report: FieldReport) -> None:
        from worldenergydata.bsee.pipeline.field_report import render_html

        result = render_html(sample_report)
        assert "<svg" in result

    def test_render_html_contains_casing_matrix(
        self, sample_report: FieldReport
    ) -> None:
        from worldenergydata.bsee.pipeline.field_report import render_html

        result = render_html(sample_report)
        # The casing matrix table should contain size data
        assert "20.0" in result or "20" in result  # casing_size
        assert "X-56" in result  # casing_grade

    def test_render_html_empty_casing(self, empty_report: FieldReport) -> None:
        from worldenergydata.bsee.pipeline.field_report import render_html

        result = render_html(empty_report)
        assert "No casing data available" in result


# ---------------------------------------------------------------------------
# Tests — activity section
# ---------------------------------------------------------------------------


class TestActivitySection:
    """Tests for the activity analysis section."""

    def test_render_html_contains_activity_analysis(
        self, sample_report: FieldReport
    ) -> None:
        from worldenergydata.bsee.pipeline.field_report import render_html

        result = render_html(sample_report)
        assert "drilling_efficiency" in result or "Drilling" in result

    def test_render_html_empty_activity(self, empty_report: FieldReport) -> None:
        from worldenergydata.bsee.pipeline.field_report import render_html

        result = render_html(empty_report)
        assert "No activity data available" in result


# ---------------------------------------------------------------------------
# Tests — warnings section
# ---------------------------------------------------------------------------


class TestWarningsSection:
    """Tests for the warnings section."""

    def test_render_html_warnings_displayed(self, sample_report: FieldReport) -> None:
        from worldenergydata.bsee.pipeline.field_report import render_html

        result = render_html(sample_report)
        assert "LFS stub detected" in result
        assert "Casing analysis partial" in result

    def test_render_html_no_warnings(self, empty_report: FieldReport) -> None:
        from worldenergydata.bsee.pipeline.field_report import render_html

        result = render_html(empty_report)
        # When there are no warnings the section should not appear
        assert "Warnings" not in result or "0 warnings" in result.lower()


# ---------------------------------------------------------------------------
# Tests — HTML escaping (XSS prevention)
# ---------------------------------------------------------------------------


class TestHtmlEscaping:
    """Verify user-derived values are HTML-escaped."""

    def test_render_html_escapes_html(self) -> None:
        from worldenergydata.bsee.pipeline.field_report import render_html

        malicious_name = '<script>alert("xss")</script>'
        context = _make_context(field_name=malicious_name)
        report = FieldReport(
            context=context,
            generated_at="2026-02-13T12:00:00+00:00",
            production_summary=pd.DataFrame(),
            activity_analysis={},
            casing_strings={},
            casing_matrices={},
            casing_svgs={},
            wellbore_count=0,
            lease_count=0,
            warnings=[],
        )
        result = render_html(report)
        # The raw <script> tag must NOT appear; it should be escaped
        assert "<script>alert" not in result
        assert html.escape(malicious_name) in result


# ---------------------------------------------------------------------------
# Tests — save_report
# ---------------------------------------------------------------------------


class TestSaveReport:
    """Tests for the save_report function."""

    def test_save_report_creates_file(
        self, sample_report: FieldReport, tmp_path: Path
    ) -> None:
        from worldenergydata.bsee.pipeline.field_report import save_report

        out_file = tmp_path / "report.html"
        save_report(sample_report, out_file)
        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "BUCKSKIN" in content

    def test_save_report_creates_parent_dirs(
        self, sample_report: FieldReport, tmp_path: Path
    ) -> None:
        from worldenergydata.bsee.pipeline.field_report import save_report

        out_file = tmp_path / "nested" / "deep" / "report.html"
        save_report(sample_report, out_file)
        assert out_file.exists()


# ---------------------------------------------------------------------------
# Tests — CSS and styling
# ---------------------------------------------------------------------------


class TestStyling:
    """Verify expected CSS classes and colour scheme."""

    def test_render_html_contains_css(self, sample_report: FieldReport) -> None:
        from worldenergydata.bsee.pipeline.field_report import render_html

        result = render_html(sample_report)
        assert "<style>" in result
        assert "#1a3a5c" in result  # dark blue header colour

    def test_render_html_contains_plotly_cdn(self, sample_report: FieldReport) -> None:
        from worldenergydata.bsee.pipeline.field_report import render_html

        result = render_html(sample_report)
        assert "plotly-basic-2.35.2.min.js" in result
