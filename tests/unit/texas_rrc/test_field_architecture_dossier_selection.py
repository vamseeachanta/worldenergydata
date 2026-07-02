"""Tests for Texas RRC field-architecture dossier candidate selection."""

from __future__ import annotations

import pandas as pd

from worldenergydata.texas_rrc.dossiers.selection import select_dossier_candidates


def test_selects_top_ranked_candidates_with_stable_reasons() -> None:
    rankings = pd.DataFrame(
        [
            {
                "opportunity_rank": 2,
                "district": "03",
                "field_number": "84750500",
                "field_name": "Southern Bay",
                "architecture_signal_class": "emerging_growth",
            },
            {
                "opportunity_rank": 1,
                "district": "05",
                "field_number": "00870500",
                "field_name": "Aguila Vado",
                "architecture_signal_class": "high_access_infill_redevelopment",
            },
            {
                "opportunity_rank": 3,
                "district": "02",
                "field_number": "27135750",
                "field_name": "Eagleville",
                "architecture_signal_class": "mature_harvest",
            },
        ]
    )

    selected = select_dossier_candidates(
        rankings,
        max_fields=2,
        class_coverage_limit=0,
    )

    assert selected["field_number"].tolist() == ["00870500", "84750500"]
    assert selected["dossier_rank"].tolist() == [1, 2]
    assert selected["selection_reason"].tolist() == ["top_ranked", "top_ranked"]
    assert selected["dossier_focus"].tolist() == [
        "infill_redevelopment_review",
        "growth_pattern_review",
    ]


def test_adds_class_coverage_only_for_absent_top_ranked_classes() -> None:
    rankings = pd.DataFrame(
        [
            _ranking(
                1, "05", "00000001", "Top High", "high_access_infill_redevelopment"
            ),
            _ranking(
                2, "05", "00000002", "Second High", "high_access_infill_redevelopment"
            ),
            _ranking(3, "03", "00000003", "Growth A", "emerging_growth"),
            _ranking(4, "03", "00000004", "Growth B", "emerging_growth"),
            _ranking(
                5,
                "02",
                "00000005",
                "Constrained",
                "infrastructure_constrained_activity",
            ),
            _ranking(6, "02", "00000006", "Mature", "mature_harvest"),
        ]
    )

    selected = select_dossier_candidates(
        rankings,
        max_fields=2,
        class_coverage_limit=1,
    )

    assert selected["field_number"].tolist() == [
        "00000001",
        "00000002",
        "00000003",
        "00000005",
        "00000006",
    ]
    assert selected["selection_reason"].tolist() == [
        "top_ranked",
        "top_ranked",
        "class_coverage:emerging_growth",
        "class_coverage:infrastructure_constrained_activity",
        "class_coverage:mature_harvest",
    ]


def _ranking(
    rank: int,
    district: str,
    field_number: str,
    field_name: str,
    architecture_class: str,
) -> dict[str, object]:
    return {
        "opportunity_rank": rank,
        "district": district,
        "field_number": field_number,
        "field_name": field_name,
        "architecture_signal_class": architecture_class,
    }
