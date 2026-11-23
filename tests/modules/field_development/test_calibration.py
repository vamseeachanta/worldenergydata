"""Calibration mechanics use synthetic inputs; the private benchmark is unavailable."""

import pytest

from worldenergydata.field_development import (
    ConceptType,
    FieldConcept,
    backtest_fields,
    compare_enrichment,
    concept_recall,
    recommend,
)


@pytest.mark.parametrize("enrich", [False, True])
def test_default_private_benchmark_is_unavailable(enrich):
    with pytest.raises(RuntimeError, match="redistribution-terms review"):
        backtest_fields(enrich=enrich)


def test_comparison_requires_available_benchmark():
    with pytest.raises(RuntimeError, match="redistribution-terms review"):
        compare_enrichment()


def test_shallow_synthetic_sample_backtests_to_fixed_jacket():
    sample = [
        FieldConcept(
            name=f"Synthetic shelf {i}",
            water_depth_m=d,
            concept_type=ConceptType.FIXED_JACKET,
        )
        for i, d in enumerate([60, 90, 120, 200, 250])
    ]
    report = backtest_fields(sample, k=1)
    assert report.n == 5
    assert report.top1_acc >= 0.8
    assert sum(report.confusion.values()) == report.n
    assert concept_recall(report)["fixed_jacket"][1] == 5


def test_unknown_truth_or_depth_is_not_scored():
    fields = [
        FieldConcept(name="Synthetic unknown truth", water_depth_m=100),
        FieldConcept(name="Synthetic unknown depth", concept_type=ConceptType.SPAR),
    ]
    report = backtest_fields(fields)
    assert report.n == 0
    assert report.confusion == {}
    assert report.top1_acc == report.topk_acc == 0


def test_recommendation_is_invariant_to_input_label():
    base = FieldConcept(
        name="Synthetic probe", water_depth_m=1500, recoverable_reserves_mmboe=120
    )
    blind = [r.concept_type for r in recommend(base)]
    for label in (ConceptType.SPAR, ConceptType.FPSO, ConceptType.SUBSEA_TIEBACK):
        labeled = base.model_copy(
            update={"concept_type": label, "operator": "Synthetic"}
        )
        assert [r.concept_type for r in recommend(labeled)] == blind
