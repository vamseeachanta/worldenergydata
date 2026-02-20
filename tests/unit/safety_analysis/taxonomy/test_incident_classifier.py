"""Tests for cross-source incident classifier."""

import pytest

from worldenergydata.safety_analysis.taxonomy.incident_classifier import (
    CONFIDENCE_DEFAULT,
    CONFIDENCE_DIRECT_CODE,
    CONFIDENCE_INCIDENT_TYPE,
    CONFIDENCE_KEYWORD_HIGH,
    CONFIDENCE_KEYWORD_LOW,
    CONFIDENCE_KEYWORD_MEDIUM,
    CONFIDENCE_SIC_NAICS,
    VALID_SOURCES,
    ClassificationResult,
    IncidentClassifier,
    _count_keyword_hits,
    _extract_text,
    _get_field,
)


class TestClassificationResult:
    def test_to_dict(self):
        r = ClassificationResult(
            activity="DRILL",
            subactivity="well_control",
            confidence=0.95,
            match_method="bsee_accident_type",
            activity_name="Drilling",
            subactivity_name="Well Control",
            source="bsee",
            raw_value="Blowout",
        )
        d = r.to_dict()
        assert d["activity"] == "DRILL"
        assert d["confidence"] == 0.95
        assert d["source"] == "bsee"

    def test_defaults(self):
        r = ClassificationResult(
            activity="OTHER",
            subactivity="unknown",
            confidence=0.1,
            match_method="default",
        )
        assert r.activity_name == ""
        assert r.source == ""


class TestGetField:
    def test_finds_first_match(self):
        record = {"ACCIDENT_TYPE": "Fire"}
        assert _get_field(record, "ACCIDENT_TYPE") == "Fire"

    def test_fallback_fields(self):
        record = {"accident_type": "Blowout"}
        assert _get_field(record, "ACCIDENT_TYPE", "accident_type") == "Blowout"

    def test_skips_empty(self):
        record = {"ACCIDENT_TYPE": "", "accident_type": "Fire"}
        assert _get_field(record, "ACCIDENT_TYPE", "accident_type") == "Fire"

    def test_skips_none(self):
        record = {"ACCIDENT_TYPE": None, "accident_type": "Fire"}
        assert _get_field(record, "ACCIDENT_TYPE", "accident_type") == "Fire"

    def test_returns_none_if_missing(self):
        assert _get_field({}, "field1", "field2") is None

    def test_strips_whitespace(self):
        record = {"f": "  value  "}
        assert _get_field(record, "f") == "value"


class TestExtractText:
    def test_concatenates_fields(self):
        record = {
            "description": "Fire on platform",
            "NARRATIVE": "Major incident",
        }
        text = _extract_text(record)
        assert "Fire on platform" in text
        assert "Major incident" in text

    def test_empty_record(self):
        assert _extract_text({}) == ""

    def test_skips_none_values(self):
        record = {"description": None, "narrative": "text"}
        text = _extract_text(record)
        assert "text" in text


class TestCountKeywordHits:
    def test_single_word_match(self):
        assert _count_keyword_hits("drilling operation", ("drilling",)) == 1

    def test_no_partial_match(self):
        # "fire" should not match "firewall"
        assert _count_keyword_hits("firewall", ("fire",)) == 0

    def test_multi_word_keyword(self):
        assert _count_keyword_hits("the top drive failed", ("top drive",)) == 1

    def test_no_hits(self):
        assert _count_keyword_hits("nothing here", ("fire", "explosion")) == 0

    def test_multiple_hits(self):
        assert _count_keyword_hits("fire and explosion", ("fire", "explosion")) == 2

    def test_case_insensitive(self):
        # keywords are lowered by the caller
        assert _count_keyword_hits("fire detected", ("fire",)) == 1


class TestIncidentClassifier:
    @pytest.fixture
    def classifier(self):
        return IncidentClassifier()

    def test_taxonomy_accessible(self, classifier):
        assert classifier.taxonomy is not None
        assert len(classifier.taxonomy.activities) == 14

    def test_invalid_source_raises(self, classifier):
        with pytest.raises(ValueError, match="Unknown source"):
            classifier.classify({}, source="unknown_source")

    def test_valid_sources_constant(self):
        assert "bsee" in VALID_SOURCES
        assert "osha" in VALID_SOURCES
        assert "marine_safety" in VALID_SOURCES
        assert "phmsa" in VALID_SOURCES
        assert "epa_tri" in VALID_SOURCES


class TestClassifyBSEE:
    @pytest.fixture
    def classifier(self):
        return IncidentClassifier()

    def test_blowout(self, classifier):
        r = classifier.classify({"ACCIDENT_TYPE": "Blowout"}, source="bsee")
        assert r.activity == "DRILL"
        assert r.confidence == CONFIDENCE_DIRECT_CODE
        assert r.source == "bsee"

    def test_fire(self, classifier):
        r = classifier.classify({"ACCIDENT_TYPE": "Fire"}, source="bsee")
        assert r.activity == "PSAFE"
        assert r.confidence == CONFIDENCE_DIRECT_CODE

    def test_collision(self, classifier):
        r = classifier.classify({"ACCIDENT_TYPE": "Collision"}, source="bsee")
        assert r.activity == "MARINE"

    def test_crane(self, classifier):
        r = classifier.classify({"ACCIDENT_TYPE": "Crane"}, source="bsee")
        assert r.activity == "CRANE"

    def test_pollution(self, classifier):
        r = classifier.classify({"ACCIDENT_TYPE": "Pollution"}, source="bsee")
        assert r.activity == "ENV"

    def test_injury(self, classifier):
        r = classifier.classify({"ACCIDENT_TYPE": "Injury"}, source="bsee")
        assert r.activity == "PERS"

    def test_empty_record_defaults(self, classifier):
        r = classifier.classify({}, source="bsee")
        assert r.activity == "OTHER"
        assert r.confidence == CONFIDENCE_DEFAULT

    def test_keyword_fallback(self, classifier):
        r = classifier.classify(
            {"description": "drilling mud pump failure"},
            source="bsee",
        )
        assert r.activity != "OTHER"
        assert r.match_method == "keyword_match"


class TestClassifyOSHA:
    @pytest.fixture
    def classifier(self):
        return IncidentClassifier()

    def test_sic_code(self, classifier):
        r = classifier.classify({"sic_code": "1311"}, source="osha")
        assert r.confidence == CONFIDENCE_SIC_NAICS
        assert r.match_method == "osha_sic_code"

    def test_naics_code(self, classifier):
        r = classifier.classify({"naics_code": "211120"}, source="osha")
        assert r.confidence == CONFIDENCE_SIC_NAICS
        assert r.match_method == "osha_naics_code"

    def test_keyword_fallback(self, classifier):
        r = classifier.classify(
            {"event_desc": "explosion in the tank farm"},
            source="osha",
        )
        assert r.match_method == "keyword_match"

    def test_empty_record(self, classifier):
        r = classifier.classify({}, source="osha")
        assert r.activity == "OTHER"


class TestClassifyMarine:
    @pytest.fixture
    def classifier(self):
        return IncidentClassifier()

    def test_collision(self, classifier):
        r = classifier.classify(
            {"incident_type": "COLLISION"},
            source="marine_safety",
        )
        assert r.activity == "MARINE"
        assert r.confidence == CONFIDENCE_INCIDENT_TYPE

    def test_fire(self, classifier):
        r = classifier.classify(
            {"incident_type": "FIRE"},
            source="marine_safety",
        )
        assert r.activity == "PSAFE"

    def test_pollution(self, classifier):
        r = classifier.classify(
            {"incident_type": "POLLUTION"},
            source="marine_safety",
        )
        assert r.activity == "ENV"

    def test_empty_record(self, classifier):
        r = classifier.classify({}, source="marine_safety")
        assert r.activity == "OTHER"


class TestClassifyPHMSA:
    @pytest.fixture
    def classifier(self):
        return IncidentClassifier()

    def test_corrosion(self, classifier):
        r = classifier.classify(
            {"cause_category": "CORROSION"},
            source="phmsa",
        )
        assert r.activity == "PIPE"
        assert r.confidence == CONFIDENCE_INCIDENT_TYPE

    def test_all_other_causes(self, classifier):
        r = classifier.classify(
            {"cause_category": "ALL OTHER CAUSES"},
            source="phmsa",
        )
        assert r.activity == "OTHER"

    def test_empty_record(self, classifier):
        r = classifier.classify({}, source="phmsa")
        assert r.activity == "OTHER"


class TestClassifyEPATRI:
    @pytest.fixture
    def classifier(self):
        return IncidentClassifier()

    def test_epa_tri(self, classifier):
        r = classifier.classify(
            {"chemical_name": "Benzene"},
            source="epa_tri",
        )
        assert r.activity == "ENV"
        assert r.confidence == CONFIDENCE_DIRECT_CODE
        assert r.match_method == "epa_tri_source"
        assert r.raw_value == "Benzene"

    def test_empty_epa_tri(self, classifier):
        r = classifier.classify({}, source="epa_tri")
        assert r.activity == "ENV"


class TestClassifyBatch:
    def test_batch(self):
        classifier = IncidentClassifier()
        records = [
            {"ACCIDENT_TYPE": "Fire"},
            {"ACCIDENT_TYPE": "Blowout"},
            {},
        ]
        results = classifier.classify_batch(records, source="bsee")
        assert len(results) == 3
        assert results[0].activity == "PSAFE"
        assert results[1].activity == "DRILL"
        assert results[2].activity == "OTHER"


class TestGetTaxonomySummary:
    def test_summary_structure(self):
        classifier = IncidentClassifier()
        s = classifier.get_taxonomy_summary()
        assert s["total_activities"] == 14
        assert s["total_subactivities"] > 0
        assert "DRILL" in s["activities"]
        assert "source_coverage" in s
        assert "bsee" in s["source_coverage"]
