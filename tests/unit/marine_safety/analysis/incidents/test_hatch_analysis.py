"""Tests for hatch maloperation analysis module."""

from worldenergydata.marine_safety.analysis.incidents.hatch_analysis import (
    HatchAnalyzer,
)


class TestHatchAnalyzerInit:
    def test_compiles_patterns(self):
        ha = HatchAnalyzer()
        assert len(ha.compiled_engine_room_patterns) >= 3
        assert len(ha.compiled_enclosure_patterns) >= 4


class TestClassifyLocation:
    def test_engine_room(self):
        ha = HatchAnalyzer()
        incident = {"description": "Fire broke out in the engine room"}
        assert ha.classify_location(incident) == "engine_room"

    def test_machinery_space(self):
        ha = HatchAnalyzer()
        incident = {"description": "Flooding detected in machinery space"}
        assert ha.classify_location(incident) == "engine_room"

    def test_other_enclosure_cargo_hold(self):
        ha = HatchAnalyzer()
        incident = {"description": "Water ingress found in cargo hold"}
        assert ha.classify_location(incident) == "other_enclosure"

    def test_deck_access(self):
        ha = HatchAnalyzer()
        incident = {"description": "Failure at deck access hatch"}
        assert ha.classify_location(incident) == "deck_access"

    def test_unknown(self):
        ha = HatchAnalyzer()
        incident = {"description": "An incident occurred on the vessel"}
        assert ha.classify_location(incident) == "unknown"

    def test_empty_description(self):
        ha = HatchAnalyzer()
        assert ha.classify_location({}) == "unknown"

    def test_no_description(self):
        ha = HatchAnalyzer()
        assert ha.classify_location({"description": ""}) == "unknown"


class TestAnalyzeConsequences:
    def test_flooding_detected(self):
        ha = HatchAnalyzer()
        incident = {"description": "The vessel experienced severe flooding"}
        consequences = ha.analyze_consequences(incident)
        assert "flooding" in consequences

    def test_fire_detected(self):
        ha = HatchAnalyzer()
        incident = {"description": "A fire broke out on the main deck"}
        consequences = ha.analyze_consequences(incident)
        assert "fire" in consequences

    def test_fatality_from_count(self):
        ha = HatchAnalyzer()
        incident = {"description": "An accident occurred", "fatalities": 2}
        consequences = ha.analyze_consequences(incident)
        assert "fatality" in consequences

    def test_injury_from_count(self):
        ha = HatchAnalyzer()
        incident = {"description": "An accident occurred", "injuries": 3}
        consequences = ha.analyze_consequences(incident)
        assert "personnel_injury" in consequences

    def test_no_consequences(self):
        ha = HatchAnalyzer()
        incident = {"description": "Routine inspection completed"}
        consequences = ha.analyze_consequences(incident)
        assert len(consequences) == 0

    def test_multiple_consequences(self):
        ha = HatchAnalyzer()
        incident = {
            "description": "Fire and flooding in the vessel",
            "fatalities": 1,
        }
        consequences = ha.analyze_consequences(incident)
        assert len(consequences) >= 2


class TestIdentifyContributingFactors:
    def test_human_error(self):
        ha = HatchAnalyzer()
        incident = {"description": "Crew failed to secure the hatch properly"}
        factors = ha.identify_contributing_factors(incident)
        assert "human_error" in factors

    def test_weather(self):
        ha = HatchAnalyzer()
        incident = {"description": "During heavy seas the cover opened"}
        factors = ha.identify_contributing_factors(incident)
        assert "weather" in factors

    def test_equipment_failure(self):
        ha = HatchAnalyzer()
        incident = {"description": "The hatch mechanism suffered equipment failure"}
        factors = ha.identify_contributing_factors(incident)
        assert "equipment_failure" in factors

    def test_no_factors(self):
        ha = HatchAnalyzer()
        incident = {"description": "Routine check completed"}
        factors = ha.identify_contributing_factors(incident)
        assert len(factors) == 0


class TestCalculateRiskScore:
    def test_minor_incident(self):
        ha = HatchAnalyzer()
        incident = {"description": "Minor hatch issue", "severity": "Minor"}
        score = ha.calculate_risk_score(incident)
        assert 0 <= score <= 100

    def test_fatalities_increase_score(self):
        ha = HatchAnalyzer()
        no_fatalities = {"description": "Issue", "severity": "Minor"}
        with_fatalities = {"description": "Issue", "severity": "Minor", "fatalities": 2}
        score_no = ha.calculate_risk_score(no_fatalities)
        score_yes = ha.calculate_risk_score(with_fatalities)
        assert score_yes > score_no

    def test_injuries_increase_score(self):
        ha = HatchAnalyzer()
        no_injuries = {"description": "Issue", "severity": "Minor"}
        with_injuries = {"description": "Issue", "severity": "Minor", "injuries": 5}
        score_no = ha.calculate_risk_score(no_injuries)
        score_yes = ha.calculate_risk_score(with_injuries)
        assert score_yes > score_no

    def test_damage_increases_score(self):
        ha = HatchAnalyzer()
        low = {
            "description": "Issue",
            "severity": "Minor",
            "estimated_damage_usd": 1000,
        }
        high = {
            "description": "Issue",
            "severity": "Minor",
            "estimated_damage_usd": 2000000,
        }
        assert ha.calculate_risk_score(high) > ha.calculate_risk_score(low)

    def test_engine_room_adds_score(self):
        ha = HatchAnalyzer()
        generic = {"description": "Issue on vessel", "severity": "Minor"}
        engine = {"description": "Issue in engine room", "severity": "Minor"}
        assert ha.calculate_risk_score(engine) > ha.calculate_risk_score(generic)

    def test_capped_at_100(self):
        ha = HatchAnalyzer()
        extreme = {
            "description": "Massive fire and flooding in engine room",
            "severity": "Catastrophic",
            "fatalities": 20,
            "injuries": 50,
            "estimated_damage_usd": 10000000,
        }
        score = ha.calculate_risk_score(extreme)
        assert score == 100.0


class TestGenerateRecommendations:
    def test_human_error_recommendations(self):
        ha = HatchAnalyzer()
        incident = {"description": "Crew failed to secure the hatch"}
        recs = ha.generate_recommendations(incident)
        assert any("training" in r.lower() for r in recs)

    def test_weather_recommendations(self):
        ha = HatchAnalyzer()
        incident = {"description": "During heavy seas the cover opened"}
        recs = ha.generate_recommendations(incident)
        assert any("weather" in r.lower() for r in recs)

    def test_flooding_recommendations(self):
        ha = HatchAnalyzer()
        incident = {"description": "Flooding occurred due to hatch failure"}
        recs = ha.generate_recommendations(incident)
        assert any("bilge" in r.lower() or "flooding" in r.lower() for r in recs)

    def test_engine_room_recommendations(self):
        ha = HatchAnalyzer()
        incident = {"description": "Issue in the engine room"}
        recs = ha.generate_recommendations(incident)
        assert any("engine room" in r.lower() for r in recs)

    def test_default_recommendation(self):
        ha = HatchAnalyzer()
        incident = {"description": "Routine issue"}
        recs = ha.generate_recommendations(incident)
        assert len(recs) >= 1


class TestIsSignificantIncident:
    def test_fatalities_significant(self):
        ha = HatchAnalyzer()
        assert ha.is_significant_incident({"description": "", "fatalities": 1}) is True

    def test_many_injuries_significant(self):
        ha = HatchAnalyzer()
        assert ha.is_significant_incident({"description": "", "injuries": 5}) is True

    def test_few_injuries_not_significant(self):
        ha = HatchAnalyzer()
        assert ha.is_significant_incident({"description": "", "injuries": 1}) is False

    def test_high_damage_significant(self):
        ha = HatchAnalyzer()
        assert (
            ha.is_significant_incident(
                {"description": "", "estimated_damage_usd": 1000000}
            )
            is True
        )

    def test_catastrophic_severity_significant(self):
        ha = HatchAnalyzer()
        assert (
            ha.is_significant_incident({"description": "", "severity": "Catastrophic"})
            is True
        )

    def test_minor_not_significant(self):
        ha = HatchAnalyzer()
        assert (
            ha.is_significant_incident(
                {"description": "Minor issue", "severity": "Minor"}
            )
            is False
        )


class TestExtractCaseStudy:
    def test_has_required_fields(self):
        ha = HatchAnalyzer()
        incident = {
            "incident_id": "INC-001",
            "date": "2024-01-01",
            "location": "Gulf of Mexico",
            "description": "Flooding in engine room due to hatch failure",
            "fatalities": 0,
            "injuries": 2,
            "estimated_damage_usd": 500000,
            "severity": "Major",
        }
        case = ha.extract_case_study(incident)
        assert case["incident_id"] == "INC-001"
        assert case["date"] == "2024-01-01"
        assert case["location"] == "Gulf of Mexico"
        assert "summary" in case
        assert "location_type" in case
        assert "contributing_factors" in case
        assert "consequences" in case
        assert "casualties" in case
        assert case["casualties"]["injuries"] == 2
        assert "risk_score" in case
        assert "lessons_learned" in case
        assert "recommendations" in case

    def test_summary_truncation(self):
        ha = HatchAnalyzer()
        long_desc = "A" * 300
        incident = {"description": long_desc}
        case = ha.extract_case_study(incident)
        assert len(case["summary"]) <= 210  # 200 + "..."


class TestGenerateSummary:
    def test_short_description(self):
        ha = HatchAnalyzer()
        incident = {"description": "Short text"}
        summary = ha._generate_summary(incident)
        assert summary == "Short text"

    def test_two_sentences(self):
        ha = HatchAnalyzer()
        incident = {"description": "First sentence. Second sentence. Third sentence."}
        summary = ha._generate_summary(incident)
        assert "First sentence" in summary
        assert "Second sentence" in summary


class TestExtractLessonsLearned:
    def test_human_error_lesson(self):
        ha = HatchAnalyzer()
        incident = {"description": "Crew failed to secure the hatch"}
        lessons = ha._extract_lessons_learned(incident)
        assert any(
            "training" in l.lower() or "procedures" in l.lower() for l in lessons
        )

    def test_maintenance_lesson(self):
        ha = HatchAnalyzer()
        incident = {"description": "Poor maintenance caused the failure"}
        lessons = ha._extract_lessons_learned(incident)
        assert any("maintenance" in l.lower() for l in lessons)

    def test_default_lesson(self):
        ha = HatchAnalyzer()
        incident = {"description": "An incident occurred"}
        lessons = ha._extract_lessons_learned(incident)
        assert len(lessons) >= 1
