"""Synthetic, offline checks for the public interventions example."""

import sys
from pathlib import Path

import pandas as pd
import pytest

EXAMPLE = Path(__file__).resolve().parents[3] / "examples/bsee/interventions_by_depth"
sys.path.insert(0, str(EXAMPLE))
from count_interventions import (
    BANDS,
    attach_depth,
    band_from_feet,
    classify_operation,
    dedupe_permits,
    full_year_average,
    gulf_only,
    normalize_api,
    rate_per_100,
    standing_wells,
)
from estimate_costs import event_cost


@pytest.mark.parametrize(
    "metres,expected",
    [(0, 0), (99.999, 0), (100, 1), (499.999, 1), (500, 2), (1499.999, 2), (1500, 3)],
)
def test_band_edges(metres, expected):
    assert band_from_feet(metres / 0.3048) == BANDS[expected]


def test_conversion_and_unknown():
    assert band_from_feet(1000) == BANDS[1]
    for value in [None, -1, float("nan"), float("inf")]:
        assert band_from_feet(value) == "no depth"


def test_api_and_fallback():
    assert normalize_api(
        pd.Series([608174087500.0, " 6081740875 ", None])
    ).tolist() == ["608174087500", "6081740875", ""]
    bore = pd.DataFrame(
        {
            "API_WELL_NUMBER": ["608174087500", "608174087501"],
            "WATER_DEPTH": [1000, 1000],
        }
    )
    result = attach_depth(
        pd.DataFrame(
            {"API_WELL_NUMBER": ["608174087599", "608174087500", "999999999999"]}
        ),
        bore,
    )
    assert result.band.tolist() == [BANDS[1], BANDS[1], "no depth"]
    assert result.depth_join.tolist() == ["api10", "api12", "missing"]
    bore.loc[1, "WATER_DEPTH"] = 2000
    assert (
        attach_depth(
            pd.DataFrame({"API_WELL_NUMBER": ["608174087599"]}), bore
        ).band.iloc[0]
        == "no depth"
    )


def test_region_precedence():
    bore = pd.DataFrame(
        {"API_WELL_NUMBER": ["608174087500", "301234567800"], "REGION_CODE": ["G", "P"]}
    )
    f = pd.DataFrame(
        {
            "API_WELL_NUMBER": ["608174087599", "301234567800", "", ""],
            "SURF_LEASE_NUM": ["", "G12345", "G12345", "P12345"],
        }
    )
    assert gulf_only(f, bore).region.tolist() == ["G", "P", "G", "unknown"]


def test_dedupe_and_conflict():
    f = pd.DataFrame(
        {
            "SN_APM": ["1", "1", "2"],
            "API_WELL_NUMBER": ["a", "a", "b"],
            "ACC_STATUS_DATE": ["1/1/2025"] * 3,
            "APM_OP_CD": ["WORKOVER"] * 3,
        }
    )
    assert len(dedupe_permits(f)) == 2
    f.loc[1, "APM_OP_CD"] = "ENHANCE"
    with pytest.raises(ValueError, match="conflicting"):
        dedupe_permits(f)


@pytest.mark.parametrize(
    "code,subcodes,group",
    [
        ("WORKOVER", set(), "workover and recompletion"),
        ("COMP", {"ZONE"}, "workover and recompletion"),
        ("COMP", {"INITCOMP"}, "initial completion excluded"),
        ("ENHANCE", {"ACIDIZE"}, "production enhancement"),
        ("ABANDON", {"TEMPABAN"}, "temporary abandonment"),
        ("ABANDON", {"PERMABAN", "TEMPABAN"}, "permanent abandonment"),
        ("ABANDON", set(), "abandonment unspecified"),
        ("OTHER", set(), "other well work"),
        ("ABANDON", {"PLUGBACK"}, "new hole excluded"),
        ("SIDETRACK", set(), "new hole excluded"),
        ("BYPASS", set(), "new hole excluded"),
        ("DEEPEN", set(), "new hole excluded"),
    ],
)
def test_mapping(code, subcodes, group):
    assert classify_operation(code, subcodes) == group


def test_new_hole_narratives_and_false_positives():
    assert (
        classify_operation("OTHER", set(), "Deepening of original batch set well")
        == "new hole excluded"
    )
    assert (
        classify_operation(
            "OTHER",
            set(),
            "APM in lieu of Application for Permit to Drill to sidetrack",
        )
        == "new hole excluded"
    )
    assert (
        classify_operation(
            "ABANDON", {"TEMPABAN"}, "TA now, deepen under a subsequent permit"
        )
        == "temporary abandonment"
    )
    assert (
        classify_operation("ENHANCE", set(), "deepen gas lift injection point")
        == "production enhancement"
    )
    assert (
        classify_operation("OTHER", set(), "bypass scale obstruction")
        == "other well work"
    )


def test_standing_wells_dates_and_original_hole():
    b = pd.DataFrame(
        {
            "API_WELL_NUMBER": [
                "608000000100",
                "608000000101",
                "608000000200",
                "608000000300",
                "608000000400",
            ],
            "WELL_NAME_SUFFIX": [
                "ST00BP00",
                "ST01BP00",
                "ST00BP00",
                "ST00BP00",
                "ST00BP00",
            ],
            "WELL_SPUD_DATE": [
                "1/1/2020",
                "1/1/2020",
                "1/1/2026",
                "1/1/2020",
                "1/1/2020",
            ],
            "BOREHOLE_STAT_CD": ["COM", "COM", "COM", "PA", "PA"],
            "BOREHOLE_STAT_DT": ["1/1/2020"] * 3 + ["12/31/2025", "1/1/2026"],
            "WATER_DEPTH": [100] * 5,
            "REGION_CODE": ["G"] * 5,
        }
    )
    assert standing_wells(b, [2025]).standing_wells.sum() == 2


def test_rate_zero_is_missing():
    assert rate_per_100(5, 20) == 25
    assert pd.isna(rate_per_100(5, 0))


def test_inventory_duplicate_original_suffix_and_snapshot_cutoff():
    b = pd.DataFrame(
        {
            "API_WELL_NUMBER": ["608000000100", "608000000170", "608000000200"],
            "WELL_NAME_SUFFIX": ["ST00BP00"] * 3,
            "WELL_SPUD_DATE": ["1/1/2020", "1/1/2021", "12/1/2026"],
            "BOREHOLE_STAT_CD": ["COM"] * 3,
            "BOREHOLE_STAT_DT": [""] * 3,
            "WATER_DEPTH": [100] * 3,
            "REGION_CODE": ["G"] * 3,
        }
    )
    assert standing_wells(b, [2026], as_of="2026-11-12").standing_wells.sum() == 1


def test_cost_and_mobilisation():
    assert event_cost(100, 5, 200) == 700
    assert [
        event_cost(r, d, m) for r, d, m in [(100, 2, 0), (200, 3, 10), (300, 4, 20)]
    ] == [200, 610, 1220]
    with pytest.raises(ValueError):
        event_cost(-1, 5, 0)


def test_partial_never_in_average():
    f = pd.DataFrame({"year": [2024, 2025, 2026], "count": [10, 20, 1000]})
    assert full_year_average(f, "count", 2025) == 15
