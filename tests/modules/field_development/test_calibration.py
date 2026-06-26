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
    compare_enrichment,
    concept_recall,
)


def test_backtest_runs_over_a_large_real_sample():
    rep = backtest_fields()
    assert rep.n > 800  # enriched fields with a real concept + depth


def test_top1_accuracy_meets_calibrated_floor():
    rep = backtest_fields()
    # depth_fit + NUI fix took top-1 ~10%→43%; the basin prior (calibration v2)
    # took it to ~50% on the un-enriched set. Pin a floor with margin.
    assert rep.top1_acc >= 0.48, f"top-1 regressed to {rep.top1_acc:.0%}"


def test_top3_accuracy_meets_floor():
    rep = backtest_fields()
    assert rep.topk_acc >= 0.58, f"top-3 regressed to {rep.topk_acc:.0%}"


def test_host_enrichment_lifts_top1_above_baseline():
    cmp = compare_enrichment()
    base, enr = cmp["baseline"], cmp["enriched"]
    # The SubseaIQ host layer (label fix + host-proximity) must not regress, and
    # lifts top-1 to ~52% on the enriched catalog.
    assert enr.top1_acc >= base.top1_acc
    assert enr.top1_acc >= 0.50, f"enriched top-1 regressed to {enr.top1_acc:.0%}"


def test_enrichment_recovers_subsea_tieback_recall():
    # Baseline never predicts subsea_tieback (no host distance); enrichment must
    # recover the og_host satellites whose host proximity is now known.
    base = concept_recall(backtest_fields(enrich=False))
    enr = concept_recall(backtest_fields(enrich=True))
    assert base.get("subsea_tieback", (0, 0))[0] == 0
    assert enr.get("subsea_tieback", (0, 0))[0] >= 15


def test_basin_prior_cracks_fpso_recall():
    # FPSO was structurally 0-recall without a regional signal; the basin prior
    # (Brazil/West-Africa/North-Sea FPSO culture) must recover a large share.
    recall = concept_recall(backtest_fields())
    correct, total = recall.get("fpso", (0, 0))
    assert total > 100  # FPSO is a big bucket
    assert correct >= 50, f"basin prior failed to predict FPSO ({correct}/{total})"


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
