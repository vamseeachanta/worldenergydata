"""Integration tests for the LT comprehensive report assembly (#377).

End-to-end exercise: assemble_comprehensive_report() → render_all() → 3 outputs.

Asserts the falsifiable post-implementation checks from the approved plan:
- All 10 fields covered
- Citations panel ≥80 rows total (8 inputs × 10 fields, minimum)
- Markdown contains every field's section heading
- HTML renders with both #366 + #343 caveats
- PDF rendering invoked (placeholder OK on hosts without Chrome)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from tests.test_markers import integration  # noqa: E402
from worldenergydata.lower_tertiary.comprehensive_report import (  # noqa: E402
    ComprehensiveReportResult,
    assemble_comprehensive_report,
    render_all,
    render_html,
    render_markdown,
)
from worldenergydata.lower_tertiary.portfolio import LT_FIELDS_2026  # noqa: E402

EXPECTED_FIELDS = LT_FIELDS_2026
MIN_CITATIONS_TOTAL = 80  # 8 inputs × 10 fields, minimum


@pytest.fixture(scope="module")
def report() -> ComprehensiveReportResult:
    """Single shared assembly run — slow (runs economics + analytics)."""
    return assemble_comprehensive_report()


@integration
class TestAssembleComprehensiveReport:
    """The orchestrator runs end-to-end against fixtures."""

    def test_returns_result_dataclass(self, report):
        assert isinstance(report, ComprehensiveReportResult)
        assert report.timestamp_utc

    def test_economics_run_covers_all_roster_fields(self, report):
        ids = {r.field_id for r in report.economics_run.results}
        assert ids == set(EXPECTED_FIELDS)

    def test_analytics_run_has_all_four_sections(self, report):
        for name in ("technology", "operator", "hse", "cost_benchmark"):
            assert isinstance(report.analytics_run.section(name), pd.DataFrame)
            assert not report.analytics_run.section(name).empty

    def test_field_payloads_present_for_every_field(self, report):
        assert set(report.field_payloads.keys()) == set(EXPECTED_FIELDS)

    def test_executive_summary_has_findings(self, report):
        assert len(report.executive_summary) >= 5
        # Every finding should be a non-empty string.
        for finding in report.executive_summary:
            assert finding.strip()


@integration
class TestCitationsCoverage:
    """Plan acceptance: ≥80 citation rows total across all fields."""

    def test_total_citations_count(self, report):
        total = sum(len(r.citations) for r in report.economics_run.results)
        assert total >= MIN_CITATIONS_TOTAL, (
            f"Expected ≥{MIN_CITATIONS_TOTAL} citations across all fields; "
            f"got {total} ({total / len(EXPECTED_FIELDS):.1f} per field)"
        )

    def test_every_field_has_citations(self, report):
        for r in report.economics_run.results:
            assert (
                len(r.citations) >= 8
            ), f"{r.field_id}: only {len(r.citations)} citations (<8)"


@integration
class TestRendering:
    """End-to-end MD + HTML + PDF rendering."""

    def test_render_markdown_includes_every_field(self, tmp_path, report):
        out = render_markdown(report, tmp_path / "report.md")
        assert out.is_file()
        contents = out.read_text(encoding="utf-8")
        for fid in EXPECTED_FIELDS:
            # Each field's per-field detail section uses its display name.
            payload = report.field_payloads[fid]
            display = str(payload.get("display_name") or fid)
            assert display in contents, f"Markdown missing field display: {display}"

    def test_render_markdown_includes_caveats(self, tmp_path, report):
        out = render_markdown(report, tmp_path / "report.md")
        contents = out.read_text(encoding="utf-8")
        assert "#366" in contents
        assert "#343" in contents
        assert "#367" in contents
        assert "Caveats" in contents

    def test_render_html_includes_caveat_banners(self, tmp_path, report):
        out = render_html(report, tmp_path / "report.html")
        contents = out.read_text(encoding="utf-8")
        assert "#366" in contents
        assert "#343" in contents
        assert "Executive Summary" in contents
        # Each field id should appear at least once.
        for fid in EXPECTED_FIELDS:
            assert fid in contents

    def test_render_all_writes_three_outputs(self, tmp_path, report):
        paths = render_all(report, tmp_path)
        assert set(paths.keys()) == {"markdown", "html", "pdf"}
        for name, path in paths.items():
            assert path.is_file(), f"{name} output not written: {path}"
        # Markdown must be non-trivial.
        assert paths["markdown"].stat().st_size > 1000
        # HTML must be non-trivial.
        assert paths["html"].stat().st_size > 1000
        # PDF either rendered (Chrome available) or contains placeholder text.
        # Both cases produce a file ≥ a few bytes.
        assert paths["pdf"].stat().st_size > 0


@integration
class TestSupersessionMarker:
    """The original summary doc carries a supersession header per the plan."""

    def test_supersession_header_present(self):
        summary_path = PROJECT_ROOT / "reports" / "lower_tertiary_field_summary.md"
        contents = summary_path.read_text(encoding="utf-8")
        assert "SUPERSEDED" in contents
        assert "comprehensive_2026.md" in contents
        assert "#377" in contents
