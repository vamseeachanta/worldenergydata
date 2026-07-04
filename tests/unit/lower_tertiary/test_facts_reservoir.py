"""Data-integrity tests for the reservoir/HPHT block merged into the Lower
Tertiary life-cycle poster facts (reports/lower_tertiary/lifecycle/_facts.json).

These guard the honesty-gated reservoir spec: required keys present, HPHT class
constrained, numeric-or-null fields well typed, and the two vetted anchors
(Big Foot pressure withheld; Anchor 25,000-psi reservoir vs 20,000-psi
equipment) preserved verbatim.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from tests.test_markers import unit  # noqa: E402

FACTS_PATH = PROJECT_ROOT / "reports" / "lower_tertiary" / "lifecycle" / "_facts.json"

REQUIRED_KEYS = {
    "formation",
    "hpht_class",
    "pressure_psi",
    "pressure_qual",
    "equip_rating_psi",
    "temp_f",
    "tvd_ft",
    "fluid",
    "api",
    "source_note",
}

NUMERIC_OR_NULL = ("pressure_psi", "temp_f", "tvd_ft", "api")


def _load_facts():
    return json.loads(FACTS_PATH.read_text())


def _by_id(facts, field_id):
    return next(rec for rec in facts if rec["id"] == field_id)


@unit
class TestFactsReservoir:
    """Validate the merged reservoir block on every field record."""

    def test_every_record_has_reservoir_dict(self):
        facts = _load_facts()
        assert len(facts) == 10
        for rec in facts:
            assert isinstance(
                rec.get("reservoir"), dict
            ), f"{rec['id']} missing reservoir dict"

    def test_reservoir_has_all_required_keys(self):
        for rec in _load_facts():
            res = rec["reservoir"]
            missing = REQUIRED_KEYS - set(res)
            assert not missing, f"{rec['id']} reservoir missing keys: {missing}"

    def test_hpht_class_constrained(self):
        for rec in _load_facts():
            assert rec["reservoir"]["hpht_class"] in {"ultra-HPHT", "HPHT", None}

    def test_numeric_fields_none_or_number(self):
        for rec in _load_facts():
            res = rec["reservoir"]
            for key in NUMERIC_OR_NULL:
                val = res[key]
                assert val is None or isinstance(
                    val, (int, float)
                ), f"{rec['id']} reservoir.{key} not None-or-number: {val!r}"

    def test_big_foot_pressure_withheld(self):
        # Honesty anchor: Big Foot reservoir pressure is not publicly disclosed.
        big_foot = _by_id(_load_facts(), "big_foot")
        assert big_foot["reservoir"]["pressure_psi"] is None

    def test_anchor_reservoir_vs_equipment_distinction(self):
        # Vetted distinction: 25,000-psi reservoir vs 20,000-psi equipment rating.
        anchor = _by_id(_load_facts(), "anchor")
        assert anchor["reservoir"]["pressure_psi"] == 25000
        assert anchor["reservoir"]["equip_rating_psi"] == 20000
