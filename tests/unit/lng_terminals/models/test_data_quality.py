"""Tests for LNG terminal data quality models."""

from datetime import date, datetime

from worldenergydata.lng_terminals.constants import SourceReliability
from worldenergydata.lng_terminals.models.data_quality import (
    ENGINEERING_PREFIXES,
    REQUIRED_FIELDS,
    QualityScore,
    SourceCitation,
    _is_engineering_field,
)


class TestSourceCitation:
    def test_basic(self):
        citation = SourceCitation(
            source_name="GIIGNL",
            access_date=date(2024, 6, 15),
            fields_sourced=["capacity_mtpa", "status"],
            reliability=SourceReliability.HIGH,
        )
        assert citation.source_name == "GIIGNL"
        assert citation.reliability == SourceReliability.HIGH
        assert len(citation.fields_sourced) == 2

    def test_with_url(self):
        citation = SourceCitation(
            source_name="FERC",
            source_url="https://example.com",
            access_date=date(2024, 1, 1),
            fields_sourced=["operator"],
            reliability=SourceReliability.MEDIUM,
        )
        assert citation.source_url == "https://example.com"

    def test_without_url(self):
        citation = SourceCitation(
            source_name="Manual",
            access_date=date(2024, 1, 1),
            fields_sourced=["notes"],
            reliability=SourceReliability.LOW,
        )
        assert citation.source_url is None


class TestIsEngineeringField:
    def test_hull_field(self):
        assert _is_engineering_field("hull_type") is True

    def test_pipeline_field(self):
        assert _is_engineering_field("pipeline_diameter") is True

    def test_process_field(self):
        assert _is_engineering_field("process_trains") is True

    def test_storage_field(self):
        assert _is_engineering_field("storage_capacity") is True

    def test_marine_field(self):
        assert _is_engineering_field("marine_depth") is True

    def test_non_engineering_field(self):
        assert _is_engineering_field("operator") is False
        assert _is_engineering_field("country") is False
        assert _is_engineering_field("capacity_mtpa") is False


class TestRequiredFields:
    def test_expected_fields(self):
        assert "name" in REQUIRED_FIELDS
        assert "country" in REQUIRED_FIELDS
        assert "type" in REQUIRED_FIELDS
        assert "status" in REQUIRED_FIELDS


class TestEngineeringPrefixes:
    def test_expected_prefixes(self):
        assert "hull" in ENGINEERING_PREFIXES
        assert "pipeline" in ENGINEERING_PREFIXES
        assert "process" in ENGINEERING_PREFIXES
        assert "storage" in ENGINEERING_PREFIXES
        assert "marine" in ENGINEERING_PREFIXES


class TestQualityScore:
    def test_basic(self):
        score = QualityScore(
            total_score=75.0,
            required_fields_score=100.0,
            optional_fields_score=50.0,
            engineering_score=60.0,
            source_count=2,
            computed_at=datetime(2024, 6, 15),
        )
        assert score.total_score == 75.0
        assert score.source_count == 2

    def test_compute_all_present(self):
        field_presence = {
            "name": True,
            "country": True,
            "type": True,
            "status": True,
            "operator": True,
            "hull_type": True,
        }
        score = QualityScore.compute(field_presence, source_count=3)
        assert score.required_fields_score == 100.0
        assert score.optional_fields_score == 100.0
        assert score.engineering_score == 100.0
        assert score.total_score == 100.0
        assert score.source_count == 3

    def test_compute_none_present(self):
        field_presence = {
            "name": False,
            "country": False,
            "type": False,
            "status": False,
            "operator": False,
            "hull_type": False,
        }
        score = QualityScore.compute(field_presence)
        assert score.required_fields_score == 0.0
        assert score.optional_fields_score == 0.0
        assert score.engineering_score == 0.0
        assert score.total_score == 0.0

    def test_compute_partial(self):
        field_presence = {
            "name": True,
            "country": True,
            "type": False,
            "status": False,
            "operator": True,
            "hull_type": False,
            "pipeline_dia": True,
        }
        score = QualityScore.compute(field_presence)
        assert score.required_fields_score == 50.0
        assert score.optional_fields_score == 100.0
        assert score.engineering_score == 50.0

    def test_compute_custom_required_fields(self):
        field_presence = {"a": True, "b": False, "c": True}
        score = QualityScore.compute(field_presence, required_fields=["a", "b"])
        assert score.required_fields_score == 50.0

    def test_compute_no_optional_or_engineering(self):
        field_presence = {"name": True, "country": True}
        score = QualityScore.compute(
            field_presence, required_fields=["name", "country"]
        )
        assert score.required_fields_score == 100.0
        assert score.optional_fields_score == 100.0
        assert score.engineering_score == 100.0

    def test_field_scores_preserved(self):
        field_presence = {"name": True, "country": False}
        score = QualityScore.compute(
            field_presence, required_fields=["name", "country"]
        )
        assert score.field_scores == {"name": True, "country": False}

    def test_weights_sum_to_one(self):
        total = (
            QualityScore._WEIGHT_REQUIRED
            + QualityScore._WEIGHT_OPTIONAL
            + QualityScore._WEIGHT_ENGINEERING
        )
        assert abs(total - 1.0) < 1e-10
