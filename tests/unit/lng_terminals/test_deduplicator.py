"""Tests for LNG terminals deduplicator module."""

import pytest

from worldenergydata.lng_terminals.processors.deduplicator import (
    Deduplicator,
    _MANUAL_ALIASES,
    _STRIP_WORDS,
)


# ---------------------------------------------------------------------------
# Static helper methods (no LNGTerminal needed)
# ---------------------------------------------------------------------------

class TestNormalizeName:
    def test_basic(self):
        result = Deduplicator._normalize_name("Sabine Pass LNG Terminal")
        # Strips "lng" and "terminal"
        assert "lng" not in result
        assert "terminal" not in result
        assert "sabine" in result
        assert "pass" in result

    def test_strips_all_keywords(self):
        result = Deduplicator._normalize_name("LNG Liquefaction Plant Facility")
        assert result == ""

    def test_unicode_normalization(self):
        result = Deduplicator._normalize_name("Hammerfest LNG")
        assert "hammerfest" in result

    def test_accent_handling(self):
        result = Deduplicator._normalize_name("Réseau Terminal LNG")
        assert "reseau" in result


class TestStringSimilarity:
    def test_identical(self):
        assert Deduplicator._string_similarity("hello", "hello") == 1.0

    def test_empty_strings(self):
        assert Deduplicator._string_similarity("", "") == 0.0
        assert Deduplicator._string_similarity("hello", "") == 0.0

    def test_similar(self):
        sim = Deduplicator._string_similarity("sabine pass", "sabine pas")
        assert sim > 0.7

    def test_dissimilar(self):
        sim = Deduplicator._string_similarity("cameron", "driftwood")
        assert sim < 0.3

    def test_single_char(self):
        # Single char strings use the char itself as a bigram
        sim = Deduplicator._string_similarity("a", "a")
        assert sim == 1.0


class TestAliasMatch:
    def test_known_alias(self):
        assert Deduplicator._alias_match("sabine pass", "sabine pass liquefaction") is True

    def test_no_match(self):
        assert Deduplicator._alias_match("cameron", "driftwood") is False

    def test_ras_laffan_aliases(self):
        assert Deduplicator._alias_match("ras laffan", "qatargas") is True

    def test_nigeria_aliases(self):
        assert Deduplicator._alias_match("nigeria", "nlng") is True


class TestDifferOnlyByNumber:
    def test_different_numbers(self):
        assert Deduplicator._differ_only_by_number("train 1", "train 2") is True

    def test_same_number(self):
        assert Deduplicator._differ_only_by_number("train 1", "train 1") is False

    def test_no_number(self):
        assert Deduplicator._differ_only_by_number("cameron", "sabine") is False

    def test_different_bases(self):
        assert Deduplicator._differ_only_by_number("train 1", "vessel 2") is False

    def test_multi_digit(self):
        assert Deduplicator._differ_only_by_number("module 10", "module 20") is True


class TestHaversineKm:
    def test_same_point(self):
        dist = Deduplicator._haversine_km(0, 0, 0, 0)
        assert dist == pytest.approx(0.0)

    def test_known_distance(self):
        # London to Paris ~344 km
        dist = Deduplicator._haversine_km(51.5074, -0.1278, 48.8566, 2.3522)
        assert 340 < dist < 350

    def test_opposite_poles(self):
        dist = Deduplicator._haversine_km(90, 0, -90, 0)
        # Half circumference ~ 20015 km
        assert 20000 < dist < 20100


class TestStripWords:
    def test_strip_words_set(self):
        assert "lng" in _STRIP_WORDS
        assert "terminal" in _STRIP_WORDS
        assert "liquefaction" in _STRIP_WORDS


class TestManualAliases:
    def test_sabine_pass(self):
        assert "sabine-pass-lng" in _MANUAL_ALIASES
        assert "sabine pass" in _MANUAL_ALIASES["sabine-pass-lng"]

    def test_ras_laffan(self):
        assert "ras-laffan" in _MANUAL_ALIASES
