"""Tests for quality dashboard dataclasses and helper functions."""

import json
from datetime import date, datetime
from decimal import Decimal

import pytest

from worldenergydata.marine_safety.reports.quality_dashboard import (
    CompletenessReport,
    CoverageReport,
    DuplicateReport,
    QualitySummary,
    _decimal_default,
)


class TestDecimalDefault:
    def test_decimal(self):
        result = _decimal_default(Decimal("3.14"))
        assert result == 3.14
        assert isinstance(result, float)

    def test_date(self):
        result = _decimal_default(date(2022, 1, 15))
        assert result == "2022-01-15"

    def test_datetime(self):
        result = _decimal_default(datetime(2022, 1, 15, 10, 30))
        assert "2022-01-15" in result

    def test_unsupported_type(self):
        with pytest.raises(TypeError, match="not JSON serializable"):
            _decimal_default(set())


class TestCoverageReport:
    def test_init(self):
        report = CoverageReport(
            by_source={"atsb": 100, "ntsb": 200},
            by_year={2020: 50, 2021: 150},
            by_source_year={"atsb": {2020: 25}},
            total_records=300,
            date_range=(date(2020, 1, 1), date(2021, 12, 31)),
        )
        assert report.total_records == 300
        assert report.by_source["atsb"] == 100
        assert report.metadata == {}

    def test_to_dict(self):
        report = CoverageReport(
            by_source={"atsb": 100},
            by_year={2020: 100},
            by_source_year={},
            total_records=100,
            date_range=(date(2020, 1, 1), date(2020, 12, 31)),
        )
        d = report.to_dict()
        assert d["total_records"] == 100
        assert d["date_range"]["start"] == "2020-01-01"
        assert d["date_range"]["end"] == "2020-12-31"

    def test_to_dict_none_dates(self):
        report = CoverageReport(
            by_source={},
            by_year={},
            by_source_year={},
            total_records=0,
            date_range=(None, None),
        )
        d = report.to_dict()
        assert d["date_range"]["start"] is None
        assert d["date_range"]["end"] is None

    def test_to_json(self):
        report = CoverageReport(
            by_source={"atsb": 10},
            by_year={2020: 10},
            by_source_year={},
            total_records=10,
            date_range=(date(2020, 1, 1), date(2020, 12, 31)),
        )
        j = report.to_json()
        parsed = json.loads(j)
        assert parsed["total_records"] == 10

    def test_metadata(self):
        report = CoverageReport(
            by_source={},
            by_year={},
            by_source_year={},
            total_records=0,
            date_range=(None, None),
            metadata={"version": "1.0"},
        )
        assert report.metadata["version"] == "1.0"


class TestCompletenessReport:
    def test_init(self):
        report = CompletenessReport(
            field_completeness={"vessel_name": 95.0},
            by_source={"atsb": {"vessel_name": 90.0}},
            total_records=100,
            critical_fields={"vessel_name": 95.0},
        )
        assert report.total_records == 100

    def test_to_dict(self):
        report = CompletenessReport(
            field_completeness={"vessel_name": 95.0},
            by_source={},
            total_records=50,
            critical_fields={},
        )
        d = report.to_dict()
        assert d["total_records"] == 50
        assert "field_completeness" in d

    def test_to_json(self):
        report = CompletenessReport(
            field_completeness={},
            by_source={},
            total_records=0,
            critical_fields={},
        )
        j = report.to_json()
        parsed = json.loads(j)
        assert parsed["total_records"] == 0


class TestDuplicateReport:
    def test_init(self):
        report = DuplicateReport(
            total_links=20,
            verified_duplicates=5,
            potential_duplicates=15,
            by_confidence={"high": 5, "medium": 10, "low": 5},
            by_match_type={"exact": 5, "fuzzy": 15},
        )
        assert report.total_links == 20
        assert report.verified_duplicates == 5

    def test_to_dict(self):
        report = DuplicateReport(
            total_links=10,
            verified_duplicates=3,
            potential_duplicates=7,
            by_confidence={},
            by_match_type={},
        )
        d = report.to_dict()
        assert d["total_links"] == 10
        assert d["potential_duplicates"] == 7

    def test_to_json(self):
        report = DuplicateReport(
            total_links=0,
            verified_duplicates=0,
            potential_duplicates=0,
            by_confidence={},
            by_match_type={},
        )
        j = report.to_json()
        parsed = json.loads(j)
        assert parsed["verified_duplicates"] == 0


class TestQualitySummary:
    def _make_summary(self):
        coverage = CoverageReport(
            by_source={"atsb": 10},
            by_year={2020: 10},
            by_source_year={},
            total_records=10,
            date_range=(date(2020, 1, 1), date(2020, 12, 31)),
        )
        completeness = CompletenessReport(
            field_completeness={"vessel_name": 90.0},
            by_source={},
            total_records=10,
            critical_fields={},
        )
        duplicates = DuplicateReport(
            total_links=2,
            verified_duplicates=1,
            potential_duplicates=1,
            by_confidence={},
            by_match_type={},
        )
        return QualitySummary(
            coverage=coverage,
            completeness=completeness,
            duplicates=duplicates,
            incident_type_distribution={"collision": 5},
            severity_distribution={1: 5, 2: 3},
            geographic_coverage={"Australia": 10},
            overall_quality_score=85.0,
            generated_at=datetime(2022, 6, 15, 12, 0),
        )

    def test_init(self):
        summary = self._make_summary()
        assert summary.overall_quality_score == 85.0
        assert summary.coverage.total_records == 10

    def test_to_dict(self):
        summary = self._make_summary()
        d = summary.to_dict()
        assert d["overall_quality_score"] == 85.0
        assert "coverage" in d
        assert "completeness" in d
        assert "duplicates" in d
        assert "2022-06-15" in d["generated_at"]

    def test_to_json(self):
        summary = self._make_summary()
        j = summary.to_json()
        parsed = json.loads(j)
        assert parsed["overall_quality_score"] == 85.0

    def test_save_json(self, tmp_path):
        summary = self._make_summary()
        outfile = tmp_path / "quality.json"
        summary.save_json(outfile)
        assert outfile.exists()
        parsed = json.loads(outfile.read_text())
        assert parsed["overall_quality_score"] == 85.0

    def test_metadata_default(self):
        summary = self._make_summary()
        assert summary.metadata == {}
