"""Synthetic, offline checks for the public interventions example."""

import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

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
from estimate_costs import estimate, event_cost


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


def test_standing_wells_at_start_of_year():
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
    assert standing_wells(b, [2025]).standing_wells.sum() == 3
    assert standing_wells(b, [2026]).standing_wells.sum() == 2


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


def well_bores(statuses, status_dates, spuds=None):
    return pd.DataFrame(
        {
            "API_WELL_NUMBER": [f"6080000001{i:02d}" for i in range(len(statuses))],
            "WELL_NAME_SUFFIX": ["ST00BP00"] + ["ST01BP00"] * (len(statuses) - 1),
            "WELL_SPUD_DATE": spuds or ["2020-01-01"] * len(statuses),
            "BOREHOLE_STAT_CD": statuses,
            "BOREHOLE_STAT_DT": status_dates,
            "WATER_DEPTH": [100] * len(statuses),
            "REGION_CODE": ["G"] * len(statuses),
        }
    )


def test_superseded_original_with_abandoned_sidetrack():
    b = well_bores(["ST", "PA"], ["2021-01-01", "2025-06-01"])
    assert standing_wells(b, [2025]).standing_wells.sum() == 1
    assert standing_wells(b, [2026]).standing_wells.sum() == 0
    assert standing_wells(b, [2025], at="year_end").standing_wells.sum() == 0


def test_superseded_original_with_live_sidetrack():
    b = well_bores(["ST", "COM"], ["2021-01-01", "2022-01-01"])
    assert standing_wells(b, [2026]).standing_wells.sum() == 1


def test_cancelled_bore_ignored_in_status_and_first_spud():
    b = well_bores(["CNL", "PA"], ["", "2025-06-01"], ["2000-01-01", "2020-01-01"])
    assert standing_wells(b, [2010]).standing_wells.sum() == 0
    assert standing_wells(b, [2026]).standing_wells.sum() == 0
    assert standing_wells(b.iloc[:1], [2025]).standing_wells.sum() == 0


@pytest.mark.parametrize(
    "statuses, dates_", [(["ST", "BP"], ["", ""]), (["ST", "PA"], ["2021-01-01", ""])]
)
def test_unresolved_terminal_status_kept_and_counted(statuses, dates_):
    f = standing_wells(well_bores(statuses, dates_), [2026])
    assert f.standing_wells.sum() == 1
    assert f.assumed_standing.sum() == 1


def test_all_terminal_bores_must_be_abandoned_and_dates_inclusive():
    b = well_bores(["ST", "PA", "PA"], ["2020-01-01", "2024-01-01", "2026-01-01"])
    assert standing_wells(b, [2025]).standing_wells.sum() == 1
    assert standing_wells(b, [2026]).standing_wells.sum() == 0


def test_unit_type_mapping():
    from count_interventions import unit_category

    assert unit_category("DS", "DRILLSHIP", "1") == "drillship / semisubmersible"
    assert unit_category("SD", "SEMI", "2") == "drillship / semisubmersible"
    assert unit_category("CT", "COILED TUBING", "3") == "coiled tubing"
    assert unit_category("SB", "SNUBBING", "4") == "hydraulic workover / snubbing"
    assert unit_category("NR", "NON RIG PA", "5") == "none named"
    assert unit_category("", "", "") == "none named"
    assert unit_category("UNKNOWN", "UNKNOWN RIG", "6") == "other"
    assert unit_category("", "", "999") == "other"


@pytest.mark.parametrize(
    "scenario_id,case,expected",
    [
        ("platform_casing_work", "low_usd", 554454),  # 68,424 x 7 + 75,486 = 554,454
        ("platform_rigless_pa", "low_usd", 269076),  # 64,530 x 3 + 75,486 = 269,076
        ("subsea_work", "low_usd", 4722200),  # 674,600 x 7 + 0 = 4,722,200
        ("deep_platform_pa", "high_usd", 1374570),  # Table 8-4, 5,000 ft
    ],
)
def test_real_cost_literals_from_yaml(scenario_id, case, expected):
    basis = yaml.safe_load((EXAMPLE / "cost_basis.yml").read_text(encoding="utf-8"))
    assert estimate(basis).set_index("scenario_id").loc[scenario_id, case] == expected


def test_deep_platform_work_is_unpriced():
    basis = yaml.safe_load((EXAMPLE / "cost_basis.yml").read_text(encoding="utf-8"))
    row = estimate(basis).set_index("scenario_id").loc["deep_platform_work"]
    assert pd.isna(row.low_usd)
    assert row.pricing_method == "not priced"
