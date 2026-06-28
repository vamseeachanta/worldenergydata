# ABOUTME: Regression test pinning recommendation-engine calibration accuracy.
# ABOUTME: Issue #570 (epic #567) — back-test vs real enriched field concepts.
"""Tests for ``worldenergydata.field_development.calibration``.

Pins the engine's accuracy against the real development concepts of the enriched
SubseaIQ catalog, so a future change that regresses the heuristics fails loudly.
Floors sit below the achieved figures (top-1 ≈ 53% base / ≈ 55% enriched, top-3
≈ 61%) with margin. These are **in-sample** figures — the bands were fit to the
same catalog the back-test scores, with no holdout (see calibration-v2.md).
"""

from __future__ import annotations

from worldenergydata.field_development import (
    ConceptType,
    FieldConcept,
    backtest_fields,
    compare_enrichment,
    concept_recall,
    recommend,
)


def test_backtest_runs_over_a_large_real_sample():
    rep = backtest_fields()
    assert rep.n > 800  # enriched fields with a real concept + depth


def test_top1_accuracy_meets_calibrated_floor():
    rep = backtest_fields()
    # depth_fit + NUI fix took top-1 ~10%→43%; the basin prior (v2) → ~50% and
    # the v3 moored-floater depth recalibration → ~52% on the un-enriched set.
    assert rep.top1_acc >= 0.50, f"top-1 regressed to {rep.top1_acc:.0%}"


def test_top3_accuracy_meets_floor():
    rep = backtest_fields()
    assert rep.topk_acc >= 0.58, f"top-3 regressed to {rep.topk_acc:.0%}"


def test_host_enrichment_lifts_top1_above_baseline():
    cmp = compare_enrichment()
    base, enr = cmp["baseline"], cmp["enriched"]
    # The SubseaIQ host layer (label fix + host-proximity) must not regress, and
    # lifts top-1 to ~55% on the enriched catalog (with the v3 depth bands).
    assert enr.top1_acc >= base.top1_acc
    assert enr.top1_acc >= 0.52, f"enriched top-1 regressed to {enr.top1_acc:.0%}"


def test_v3_depth_bands_recover_spar_and_tlp():
    # v2 left spar at 0 recall and TLP under-predicted because the moored-floater
    # depth bands overlapped. The v3 recalibration must recover both.
    recall = concept_recall(backtest_fields(enrich=True))
    assert recall.get("spar", (0, 0))[0] >= 4, "spar still zero-recall"
    assert recall.get("tlp", (0, 0))[0] >= 25, "TLP recall not recovered"


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


def test_recommendation_is_invariant_to_the_input_label():
    # No-leakage property pinned at the engine boundary: recommend() must rank
    # identically whether the field carries its real concept_type/operator or
    # not. backtest_fields strips them into a probe, but that only stays honest
    # if the engine genuinely ignores the label — so assert it here rather than
    # relying on the strip being remembered. A future change that made the engine
    # consume concept_type would fail this and not silently inflate accuracy.
    base = FieldConcept(
        name="probe", water_depth_m=1500.0, recoverable_reserves_mmboe=120.0
    )
    blind = [r.concept_type for r in recommend(base)]
    for label in (ConceptType.SPAR, ConceptType.FPSO, ConceptType.SUBSEA_TIEBACK):
        labeled = base.model_copy(update={"concept_type": label, "operator": "Acme"})
        assert [r.concept_type for r in recommend(labeled)] == blind
