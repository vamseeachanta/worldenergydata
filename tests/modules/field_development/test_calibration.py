# ABOUTME: Regression test pinning recommendation-engine calibration accuracy.
# ABOUTME: Issue #570 (epic #567) — back-test vs real enriched field concepts.
"""Tests for ``worldenergydata.field_development.calibration``.

Pins the engine's accuracy against the real development concepts of the enriched
SubseaIQ catalog, so a future change that regresses the heuristics fails loudly.
Thresholds sit below the achieved figures (top-1 ≈ 43%, top-3 ≈ 51%) with margin.
"""

from __future__ import annotations

from worldenergydata.field_development import (
    ConceptType,
    FieldConcept,
    backtest_fields,
)


def test_backtest_runs_over_a_large_real_sample():
    rep = backtest_fields()
    assert rep.n > 800  # enriched fields with a real concept + depth


def test_top1_accuracy_meets_calibrated_floor():
    rep = backtest_fields()
    # depth_fit + NUI fix lifted top-1 from ~10% to ~43%; pin a floor with margin.
    assert rep.top1_acc >= 0.40, f"top-1 regressed to {rep.top1_acc:.0%}"


def test_top3_accuracy_meets_floor():
    rep = backtest_fields()
    assert rep.topk_acc >= 0.48, f"top-3 regressed to {rep.topk_acc:.0%}"


def test_shallow_field_back_tests_to_fixed_jacket():
    # A small synthetic sample: shallow fields should resolve to fixed_jacket
    # (the NUI over-pick that calibration fixed).
    sample = [
        FieldConcept(
            name=f"shelf{i}", water_depth_m=d, concept_type=ConceptType.FIXED_JACKET
        )
        for i, d in enumerate([60, 90, 120, 200, 250])
    ]
    rep = backtest_fields(sample, k=1)
    assert rep.top1_acc >= 0.8  # was ~0 before the NUI fix


def test_report_confusion_is_populated():
    rep = backtest_fields()
    assert rep.confusion and sum(rep.confusion.values()) == rep.n
