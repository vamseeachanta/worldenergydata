"""Independent synthetic cases for the duration-summary contract in #1686.

All numbers here are constructed test inputs, not source-data claims. For the
four-value hand case, zero-based linear ranks are 0.75, 1.5 and 2.25, so
[2, 4, 6, 8] gives 3.5, 5 and 6.5. The rig series [1, 3, 5, 7] is one day
lower throughout. Other expectations follow by counting synthetic wells or
interpolating the explicitly stated endpoints; no expectation calls the engine.
Years and band labels are arbitrary caller declarations.
"""

from copy import deepcopy
from itertools import permutations
from sys import float_info

import pytest

from worldenergydata.bsee.analysis.annual_duration_summary import (
    annual_duration_summary,
)


def row(well_id="well-a", calendar_days=2, rig_days=1, **labels):
    return {
        "year": 2020,
        "water_depth_band": "band-a",
        "basis": "declared-a",
        "well_id": well_id,
        "calendar_days": calendar_days,
        "rig_days": rig_days,
        **labels,
    }


def hand_rows():
    return [
        row("well-a", 2, 1),
        row("well-b", 4, 3),
        row("well-c", 6, 5),
        row("well-d", 8, 7),
    ]


def test_quartiles_match_independent_hand_case():
    result = annual_duration_summary(hand_rows(), min_cell_size=4)
    assert result["cells"] == [
        {
            "year": 2020,
            "water_depth_band": "band-a",
            "basis": "declared-a",
            "well_count": 4,
            "small_cell": False,
            "calendar_days": {"valid_count": 4, "q1": 3.5, "median": 5.0, "q3": 6.5},
            "rig_days": {"valid_count": 4, "q1": 2.5, "median": 4.0, "q3": 5.5},
        }
    ]


def test_bases_never_mix():
    # The same well under two declared rules contributes to two separate cells.
    rows = [row(calendar_days=2), row(calendar_days=8, basis="declared-b")]
    cells = annual_duration_summary(rows, min_cell_size=2)["cells"]
    assert [cell["basis"] for cell in cells] == ["declared-a", "declared-b"]
    assert [cell["calendar_days"]["median"] for cell in cells] == [2.0, 8.0]
    assert [cell["well_count"] for cell in cells] == [1, 1]
    assert all(cell["small_cell"] for cell in cells)


def test_year_and_band_remain_separate_and_sorted():
    rows = [
        row(year=2021),
        row("well-b", water_depth_band="band-b"),
        row(),
    ]
    cells = annual_duration_summary(rows, min_cell_size=1)["cells"]
    assert [(cell["year"], cell["water_depth_band"]) for cell in cells] == [
        (2020, "band-a"),
        (2020, "band-b"),
        (2021, "band-a"),
    ]


def test_missing_durations_have_metric_specific_counts():
    rows = [row("well-a", None, 0), row("well-b", 8, None), row("well-c", None, 4)]
    cell = annual_duration_summary(rows, min_cell_size=3)["cells"][0]
    assert cell["well_count"] == 3
    assert cell["calendar_days"] == {
        "valid_count": 1,
        "q1": 8.0,
        "median": 8.0,
        "q3": 8.0,
    }
    # Two endpoints [0, 4]: quarter, half and three-quarter distances are 1, 2, 3.
    assert cell["rig_days"] == {"valid_count": 2, "q1": 1.0, "median": 2.0, "q3": 3.0}
    assert not cell["small_cell"]  # Threshold counts wells, not valid metrics.


def test_no_valid_metric_values_stay_null():
    cell = annual_duration_summary([row(calendar_days=None, rig_days=None)], 2)[
        "cells"
    ][0]
    assert cell["well_count"] == 1
    assert cell["small_cell"]
    for metric in ("calendar_days", "rig_days"):
        assert cell[metric] == {
            "valid_count": 0,
            "q1": None,
            "median": None,
            "q3": None,
        }


def test_one_entirely_missing_metric_does_not_erase_other_metric():
    rows = [row("well-a", None, 2), row("well-b", None, 4)]
    cell = annual_duration_summary(rows, 1)["cells"][0]
    assert cell["calendar_days"]["median"] is None
    assert cell["calendar_days"]["valid_count"] == 0
    assert cell["rig_days"]["median"] == 3.0  # Midpoint of [2, 4].
    assert cell["rig_days"]["valid_count"] == 2


def test_empty_input_keeps_schema_and_declared_caveats():
    result = annual_duration_summary(
        [],
        3,
        year_floor=2020,
        year_floor_caveat="Declared floor; coverage unconfirmed.",
    )
    assert result["cells"] == []
    assert result["metadata"]["min_cell_size"] == 3
    assert result["metadata"]["year_floor"] == 2020
    assert result["metadata"]["source_completeness"] == "not_established"


@pytest.mark.parametrize("threshold, small", [(3, False), (4, False), (5, True)])
def test_boundary_size_cells_are_flagged_and_retained(threshold, small):
    cell = annual_duration_summary(hand_rows(), threshold)["cells"][0]
    assert cell["well_count"] == 4
    assert cell["small_cell"] is small
    assert cell["calendar_days"]["median"] == 5.0


def test_exact_duplicates_count_once_including_nulls():
    rows = hand_rows() + [row("well-e", None, None)]
    result = annual_duration_summary(rows + deepcopy(rows), 6)
    assert result == annual_duration_summary(rows, 6)
    assert result["cells"][0]["well_count"] == 5
    assert result["cells"][0]["calendar_days"]["valid_count"] == 4


@pytest.mark.parametrize(
    "changed",
    [
        {"calendar_days": 4},
        {"rig_days": 4},
        {"calendar_days": None},
        {"water_depth_band": "band-b"},
    ],
)
def test_conflicting_duplicate_well_rows_are_rejected(changed):
    rows = [row(), row(**changed)]
    for ordered in (rows, rows[::-1]):
        with pytest.raises(ValueError, match="conflicting duplicate well"):
            annual_duration_summary(ordered, 1)


def test_all_permutations_leave_rows_unchanged():
    rows = hand_rows() + [row("well-a", 2, 1)]
    before = deepcopy(rows)
    expected = annual_duration_summary(rows, 4)
    for permuted in permutations(rows):
        assert annual_duration_summary(iter(permuted), 4) == expected
    assert rows == before


def test_permutation_order_is_stable_across_groups_and_bases():
    rows = [row(year=2021), row(), row(basis="declared-b")]
    expected = annual_duration_summary(rows, 1)
    for permuted in permutations(rows):
        assert annual_duration_summary(permuted, 1) == expected


def test_caveats_are_preserved_without_filtering_or_claiming_completeness():
    declared = {
        "year_floor": 2021,
        "year_floor_caveat": "Declared year floor, not confirmed source coverage.",
        "quantization_caveat": "Weekly boundaries may be quantized; no error bound.",
    }
    before = deepcopy(declared)
    result = annual_duration_summary([row()], 1, **declared)
    assert all(result["metadata"][key] == value for key, value in declared.items())
    assert result["metadata"]["source_completeness"] == "not_established"
    assert result["metadata"]["quantile_method"] == "linear: rank = (n - 1) * p"
    assert result["cells"][0]["year"] == 2020  # Metadata does not filter rows.
    assert declared == before


def test_no_caveats_are_invented():
    metadata = annual_duration_summary([], 1)["metadata"]
    assert metadata["year_floor"] is None
    assert metadata["year_floor_caveat"] is None
    assert metadata["quantization_caveat"] is None


@pytest.mark.parametrize("metric", ["calendar_days", "rig_days"])
@pytest.mark.parametrize(
    "invalid", [-1, float("nan"), float("inf"), -float("inf"), True, "2"]
)
def test_invalid_durations_are_rejected_explicitly(metric, invalid):
    with pytest.raises(ValueError, match=metric):
        annual_duration_summary([row(**{metric: invalid})], 1)


@pytest.mark.parametrize("threshold", [0, -1, True, 1.5, None])
def test_minimum_cell_size_requires_positive_integer(threshold):
    with pytest.raises(ValueError, match="min_cell_size"):
        annual_duration_summary([], threshold)


@pytest.mark.parametrize(
    "field",
    ["year", "water_depth_band", "basis", "well_id", "calendar_days", "rig_days"],
)
def test_required_fields_cannot_be_omitted(field):
    incomplete = row()
    del incomplete[field]
    with pytest.raises(ValueError, match=field):
        annual_duration_summary([incomplete], 1)


@pytest.mark.parametrize("field", ["water_depth_band", "basis", "well_id"])
@pytest.mark.parametrize("invalid", [None, "", " ", 1])
def test_group_and_well_labels_are_explicit_nonempty_strings(field, invalid):
    with pytest.raises(ValueError, match=field):
        annual_duration_summary([row(**{field: invalid})], 1)


@pytest.mark.parametrize("year", [None, True, 2020.5, "2020"])
def test_year_requires_explicit_integer(year):
    with pytest.raises(ValueError, match="year"):
        annual_duration_summary([row(year=year)], 1)


def test_fractional_durations_are_not_quantized_again():
    cell = annual_duration_summary([row(calendar_days=0.5, rig_days=0)], 1)["cells"][0]
    assert cell["calendar_days"]["median"] == 0.5
    assert cell["rig_days"]["median"] == 0.0


def test_large_finite_durations_do_not_overflow_interpolation():
    # Synthetic endpoints: half the endpoints is three quarters of the maximum.
    high = float_info.max
    cell = annual_duration_summary([row("well-a", high / 2), row("well-b", high)], 1)[
        "cells"
    ][0]
    assert cell["calendar_days"]["median"] == pytest.approx(high * 0.75)


@pytest.mark.parametrize(
    "declared",
    [
        {"year_floor": True},
        {"year_floor": "2020"},
        {"year_floor_caveat": 1},
        {"quantization_caveat": []},
    ],
)
def test_invalid_metadata_is_rejected(declared):
    with pytest.raises(ValueError, match=next(iter(declared))):
        annual_duration_summary([], 1, **declared)


def test_distinct_numeric_duplicates_cannot_merge_after_float_rounding():
    # Binary floats cannot distinguish adjacent integers beyond their mantissa.
    # This constructs that boundary from Python's declared float precision.
    large = 1 << float_info.mant_dig
    with pytest.raises(ValueError, match="conflicting duplicate well"):
        annual_duration_summary(
            [row(calendar_days=large), row(calendar_days=large + 1)], 1
        )
