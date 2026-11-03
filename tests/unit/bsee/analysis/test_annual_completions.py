"""Annual planning-area/depth counts requested by issue #1704.

All dates, identifiers, depths and counts below are synthetic hand calculations,
not engineering observations. Default bin boundaries are from activity.Parameters;
the custom boundaries are a synthetic example of caller-supplied bins.
"""

from copy import deepcopy
from datetime import date, datetime

import pytest

from worldenergydata.bsee.analysis.completion_intervention.activity import Parameters
from worldenergydata.bsee.analysis.completion_intervention.annual_completions import (
    annual_completion_counts,
)

SOURCE = "synthetic hand tally for issue #1704"


def aggregate(rows, **kwargs):
    options = {"grain": "completion", "source": SOURCE, "parameters": Parameters()}
    options.update(kwargs)
    return annual_completion_counts(rows, **options)


def completion(identifier="completion-a", **kwargs):
    row = {
        "completion_id": identifier,
        "completion_date": "2020-01-01",
        "planning_area": "Area A",
        "water_depth_ft": 500,
    }
    row.update(kwargs)
    return row


def synthetic_rows():
    # Independent tally (row letters refer to identifiers below):
    # 2020 / Area A / below 1000 ft: a,b -> 2
    # 2020 / Area A / 1000-3000 ft: c,d -> 2
    # 2020 / Area B / 3000-5000 ft: e -> 1
    # 2020 / Area B / 5000-10000 ft: f -> 1
    # 2021 / Area A / at least 10000 ft: g -> 1
    # 2021 / Area A / unknown: j -> 1
    # 2021 / Area B / below 1000 ft: l -> 1
    # 2021 / unknown / 1000-3000 ft: h -> 1
    # 2021 / unknown / unknown: i,k -> 2
    # Total: 2 + 2 + 1 + 1 + 1 + 1 + 1 + 1 + 2 = 12 completion rows.
    table = [
        ("a", "2020-01-01", "Area A", 500),
        ("b", "2020-12-31", "Area A", 999),
        ("c", "2020-02-29", "Area A", 1000),
        ("d", "2020-06-30", "Area A", 2999),
        ("e", "2020-07-01", "Area B", 3000),
        ("f", "2020-08-01", "Area B", 5000),
        ("g", "2021-01-01", "Area A", 10000),
        ("h", "2021-02-01", None, 1000),
        ("i", "2021-03-01", "", None),
        ("j", "2021-04-01", "Area A", None),
        ("k", "2021-05-01", None, None),
        ("l", "2021-06-01", "Area B", 0),
    ]
    return [
        completion(
            "completion-" + identifier,
            completion_date=day,
            planning_area=area,
            water_depth_ft=depth,
            well_id="shared well",  # Distinct completions can share a well.
        )
        for identifier, day, area, depth in table
    ]


def test_annual_area_depth_counts_match_hand_tally():
    rows = synthetic_rows()
    result = aggregate(rows)
    assert [
        (cell["year"], cell["planning_area"], cell["water_depth_band"], cell["count"])
        for cell in result["counts"]
    ] == [
        (2020, "Area A", "1000-3000 ft", 2),
        (2020, "Area A", "below 1000 ft", 2),
        (2020, "Area B", "3000-5000 ft", 1),
        (2020, "Area B", "5000-10000 ft", 1),
        (2021, "Area A", "at least 10000 ft", 1),
        (2021, "Area A", "unknown", 1),
        (2021, "Area B", "below 1000 ft", 1),
        (2021, "unknown", "1000-3000 ft", 1),
        (2021, "unknown", "unknown", 2),
    ]
    assert len(rows) == 12
    assert sum(cell["count"] for cell in result["counts"]) == len(rows)
    assert result["grain"] == "completion"
    assert result["source"] == SOURCE
    assert result["unit"] == "completions"
    assert result["depth_edges_ft"] == [1000, 3000, 5000, 10000]
    assert set(result) == {"grain", "source", "unit", "depth_edges_ft", "counts"}


def test_input_order_invariance_and_no_input_mutation():
    rows = synthetic_rows()
    original = deepcopy(rows)
    expected = aggregate(rows)
    assert aggregate(reversed(rows)) == expected
    assert aggregate(rows[::2] + rows[1::2]) == expected
    assert rows == original


@pytest.mark.parametrize("changed", [{}, {"completion_date": "2021-01-01"}])
def test_duplicate_completion_ids_are_rejected(changed):
    with pytest.raises(ValueError, match="duplicate completion_id"):
        aggregate([completion(), completion(**changed)])


@pytest.mark.parametrize("identifier", [None, "", " ", 12])
def test_completion_ids_must_be_explicit_nonempty_strings(identifier):
    with pytest.raises(ValueError, match="completion_id"):
        aggregate([completion(identifier)])


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "invalid",
        "2021-02-29",
        "2020-13-01",
        "2020",
        2020,
        "20200101",
        "2020-W01-1",
        "01/02/2020",
        "2020-01-01T00:00:00",
        datetime(2020, 1, 1),
    ],
)
def test_invalid_completion_dates_are_rejected_before_grouping(value):
    with pytest.raises(ValueError, match="completion_date"):
        aggregate([completion(), completion("completion-b", completion_date=value)])


def test_calendar_date_objects_are_accepted_without_inventing_a_year():
    result = aggregate([completion(completion_date=date(2020, 2, 29))])
    assert result["counts"] == [
        {
            "year": 2020,
            "planning_area": "Area A",
            "water_depth_band": "below 1000 ft",
            "count": 1,
        }
    ]


@pytest.mark.parametrize("key", ["completion_id", "completion_date"])
def test_missing_identity_or_date_is_rejected(key):
    row = completion()
    del row[key]
    with pytest.raises(ValueError, match=key):
        aggregate([row])


@pytest.mark.parametrize(
    "depth, expected",
    [
        (0, "below 1000 ft"),
        (999, "below 1000 ft"),
        (1000, "1000-3000 ft"),
        (2999, "1000-3000 ft"),
        (3000, "3000-5000 ft"),
        (4999, "3000-5000 ft"),
        (5000, "5000-10000 ft"),
        (9999, "5000-10000 ft"),
        (10000, "at least 10000 ft"),
    ],
)
def test_depth_edge_membership(depth, expected):
    result = aggregate([completion(water_depth_ft=depth)])
    assert result["counts"] == [
        {
            "year": 2020,
            "planning_area": "Area A",
            "water_depth_band": expected,
            "count": 1,
        }
    ]


def test_caller_supplied_depth_bins_are_used():
    # Hand calculation: 10 belongs to [10,20); 20 belongs to [20,infinity).
    result = aggregate(
        [completion(water_depth_ft=10), completion("completion-b", water_depth_ft=20)],
        parameters=Parameters(depth_edges=(10, 20)),
    )
    assert result["depth_edges_ft"] == [10, 20]
    assert [cell["water_depth_band"] for cell in result["counts"]] == [
        "10-20 ft",
        "at least 20 ft",
    ]
    assert [cell["count"] for cell in result["counts"]] == [1, 1]


@pytest.mark.parametrize("depth", [None, "", "invalid", -1, float("nan"), float("inf")])
def test_unusable_depths_remain_unknown(depth):
    result = aggregate([completion(water_depth_ft=depth)])
    assert result["counts"][0]["water_depth_band"] == "unknown"
    assert result["counts"][0]["count"] == 1


def test_missing_area_and_depth_are_retained_without_geographic_inference():
    row = completion(field="field abbreviation", area="area abbreviation")
    del row["planning_area"]
    del row["water_depth_ft"]
    assert aggregate([row])["counts"] == [
        {
            "year": 2020,
            "planning_area": "unknown",
            "water_depth_band": "unknown",
            "count": 1,
        }
    ]


@pytest.mark.parametrize("area", [None, "", " "])
def test_absent_planning_area_is_an_explicit_unknown(area):
    assert (
        aggregate([completion(planning_area=area)])["counts"][0]["planning_area"]
        == "unknown"
    )


def test_planning_area_requires_a_normalized_label():
    with pytest.raises(ValueError, match="planning_area"):
        aggregate([completion(planning_area=12)])


@pytest.mark.parametrize("grain", [None, "", "well", "completion record"])
def test_grain_must_declare_unique_completions(grain):
    with pytest.raises(ValueError, match="grain"):
        aggregate([], grain=grain)


@pytest.mark.parametrize("source", [None, "", " ", 12])
def test_source_metadata_is_required(source):
    with pytest.raises(ValueError, match="source"):
        aggregate([], source=source)


@pytest.mark.parametrize("key", ["grain", "source", "parameters"])
def test_metadata_and_parameters_have_no_implicit_defaults(key):
    options = {"grain": "completion", "source": SOURCE, "parameters": Parameters()}
    del options[key]
    with pytest.raises(TypeError):
        annual_completion_counts([], **options)


def test_depth_parameters_cannot_be_absent():
    with pytest.raises(ValueError, match="parameters"):
        aggregate([], parameters=None)


def test_empty_input_preserves_metadata_without_synthetic_cells():
    assert aggregate([]) == {
        "grain": "completion",
        "source": SOURCE,
        "unit": "completions",
        "depth_edges_ft": [1000, 3000, 5000, 10000],
        "counts": [],
    }
