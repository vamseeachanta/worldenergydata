"""Tests for hatch maloperation pattern definitions."""

import re

from worldenergydata.marine_safety.analysis.incidents.hatch_patterns import (
    CONSEQUENCE_PATTERNS,
    ENCLOSURE_PATTERNS,
    ENGINE_ROOM_PATTERNS,
    FACTOR_PATTERNS,
    HATCH_PATTERNS,
    HIGH_IMPACT_CONSEQUENCES,
)


class TestHatchPatterns:
    def test_has_patterns(self):
        assert len(HATCH_PATTERNS) > 20

    def test_all_compile(self):
        for pattern in HATCH_PATTERNS:
            compiled = re.compile(pattern, re.IGNORECASE)
            assert compiled is not None

    def test_matches_hatch_maloperation(self):
        text = "The hatch maloperation caused flooding"
        found = any(re.search(p, text, re.IGNORECASE) for p in HATCH_PATTERNS)
        assert found is True

    def test_matches_door_failure(self):
        text = "A watertight door failure was reported"
        found = any(re.search(p, text, re.IGNORECASE) for p in HATCH_PATTERNS)
        assert found is True

    def test_matches_seal_failure(self):
        text = "seal failure led to ingress"
        found = any(re.search(p, text, re.IGNORECASE) for p in HATCH_PATTERNS)
        assert found is True

    def test_no_false_match_unrelated(self):
        text = "engine oil temperature was normal"
        found = any(re.search(p, text, re.IGNORECASE) for p in HATCH_PATTERNS)
        assert found is False


class TestEngineRoomPatterns:
    def test_has_patterns(self):
        assert len(ENGINE_ROOM_PATTERNS) >= 3

    def test_matches_engine_room(self):
        text = "Fire in the engine room"
        found = any(re.search(p, text, re.IGNORECASE) for p in ENGINE_ROOM_PATTERNS)
        assert found is True

    def test_matches_machinery_space(self):
        text = "Flooding in machinery space"
        found = any(re.search(p, text, re.IGNORECASE) for p in ENGINE_ROOM_PATTERNS)
        assert found is True


class TestEnclosurePatterns:
    def test_has_patterns(self):
        assert len(ENCLOSURE_PATTERNS) >= 4

    def test_matches_cargo_hold(self):
        text = "Water ingress in cargo hold"
        found = any(re.search(p, text, re.IGNORECASE) for p in ENCLOSURE_PATTERNS)
        assert found is True


class TestConsequencePatterns:
    def test_has_flooding(self):
        assert "flooding" in CONSEQUENCE_PATTERNS

    def test_has_fire(self):
        assert "fire" in CONSEQUENCE_PATTERNS

    def test_has_fatality(self):
        assert "fatality" in CONSEQUENCE_PATTERNS

    def test_flooding_matches(self):
        patterns = CONSEQUENCE_PATTERNS["flooding"]
        text = "vessel was flooding rapidly"
        found = any(re.search(p, text, re.IGNORECASE) for p in patterns)
        assert found is True

    def test_all_compile(self):
        for category, patterns in CONSEQUENCE_PATTERNS.items():
            for pattern in patterns:
                re.compile(pattern, re.IGNORECASE)


class TestFactorPatterns:
    def test_has_human_error(self):
        assert "human_error" in FACTOR_PATTERNS

    def test_has_weather(self):
        assert "weather" in FACTOR_PATTERNS

    def test_has_equipment_failure(self):
        assert "equipment_failure" in FACTOR_PATTERNS

    def test_human_error_matches(self):
        patterns = FACTOR_PATTERNS["human_error"]
        text = "crew failed to secure the hatch"
        found = any(re.search(p, text, re.IGNORECASE) for p in patterns)
        assert found is True

    def test_weather_matches(self):
        patterns = FACTOR_PATTERNS["weather"]
        text = "during heavy seas the cover opened"
        found = any(re.search(p, text, re.IGNORECASE) for p in patterns)
        assert found is True


class TestHighImpactConsequences:
    def test_includes_flooding(self):
        assert "flooding" in HIGH_IMPACT_CONSEQUENCES

    def test_includes_fire(self):
        assert "fire" in HIGH_IMPACT_CONSEQUENCES

    def test_includes_fatality(self):
        assert "fatality" in HIGH_IMPACT_CONSEQUENCES

    def test_count(self):
        assert len(HIGH_IMPACT_CONSEQUENCES) == 4
