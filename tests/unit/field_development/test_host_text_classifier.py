# ABOUTME: Tests for the free-text host-type -> dry/wet tree classifier.
# ABOUTME: Pins the 10 Lower-Tertiary acceptance strings + dry-before-wet order.
"""Tests for ``worldenergydata.field_development.host_text_classifier``.

The classifier backs the dev-type badge on the Lower-Tertiary life-cycle
posters. These tests pin the exact dry/wet verdict for each field's authored
``host_type`` string, the dry-before-wet keyword precedence (the eTLP case,
whose text also mentions "FPU"), and the unknown-text fallback.
"""

from __future__ import annotations

import pytest

from worldenergydata.field_development.host_text_classifier import (
    classify_tree_type,
)

# (host_type string, expected tree, expected concept label) for the 10 fields.
ACCEPTANCE = [
    ("Extended Tension-Leg Platform (eTLP)", "dry", "eTLP"),  # big_foot
    ("Semisubmersible FPU", "wet", "Semisub FPU"),  # anchor
    ("FPSO (BW Pioneer) with subsea tieback", "wet", "FPSO"),  # cascade
    ("Semisubmersible FPU", "wet", "Semisub FPU"),  # jack_st_malo
    (
        "Subsea tieback to Jack/St. Malo semisubmersible FPU",
        "wet",
        "Subsea tieback",
    ),  # julia
    ("Semisubmersible FPU (20,000 psi)", "wet", "Semisub FPU"),  # kaskida
    ("Newbuild Semisubmersible FPU", "wet", "Semisub FPU"),  # north_platte
    ("Semisubmersible FPU (FPS, 20,000-psi)", "wet", "Semisub FPU"),  # shenandoah
    ("FPSO (Turritella / Stones FPSO, disconnectable)", "wet", "FPSO"),  # stones
    (
        "Semisubmersible FPU (single-lift topsides, Kaskida-derived design)",
        "wet",
        "Semisub FPU",
    ),  # tiber
]


@pytest.mark.parametrize("text,tree,label", ACCEPTANCE)
def test_acceptance_strings_classify(text, tree, label):
    got_tree, got_label = classify_tree_type(text)
    assert got_tree == tree
    assert got_label == label


def test_acceptance_split_is_one_dry_nine_wet():
    verdicts = [classify_tree_type(t)[0] for t, _, _ in ACCEPTANCE]
    assert verdicts.count("dry") == 1
    assert verdicts.count("wet") == 9


def test_dry_keywords_checked_before_wet():
    # "Extended Tension-Leg Platform" also mentions an FPU downstream in the
    # real host strings; the dry (TLP) match must win over the wet keywords.
    tree, label = classify_tree_type("Tension-Leg Platform with FPU support")
    assert tree == "dry"
    assert label == "TLP"


def test_fpso_beats_tieback_within_wet():
    tree, label = classify_tree_type("FPSO with a long subsea tieback")
    assert (tree, label) == ("wet", "FPSO")


def test_unknown_text_returns_none():
    assert classify_tree_type("Gravity-based concrete island") == (None, "")
    assert classify_tree_type("") == (None, "")
    assert classify_tree_type(None) == (None, "")
