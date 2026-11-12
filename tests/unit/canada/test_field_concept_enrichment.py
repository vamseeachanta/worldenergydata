"""Synthetic enrichment tests with expected values calculated independently.

Median definition: Python statistics.median documentation (2026),
https://docs.python.org/3/library/statistics.html#statistics.median.
Depth positivity follows field_development.models.FieldConcept's contract.
"""

import pytest

from worldenergydata.canada.development_wells import (
    DevelopmentWell,
    DevelopmentWellMapping,
    parse_development_wells,
)
from worldenergydata.canada.field_concept import (
    CANADA_WATER_DEPTH_M,
    build_canada_field_concept,
    canada_field_to_concept,
)


def well(uwi, depth, field="Example"):
    return DevelopmentWell(uwi, field, depth, None, None, "synthetic-wells")


@pytest.mark.parametrize("build", [build_canada_field_concept, canada_field_to_concept])
def test_linked_wells_supply_depth_inventory_count_and_provenance(build):
    """[1, 3, 5, null] => median 3 m; four distinct inventory wells.

    The non-null median is Python's published [1, 3, 5] example. The fifth
    record belongs to another field and cannot affect the count or depth.
    """
    meta = {"field": "Example", "operator": "Example operator", "source": "synthetic"}
    wells = [
        well("example-a", 1),
        well("example-b", 3),
        well("example-c", 5),
        well("example-d", None),
        well("example-e", 7, field="Elsewhere"),
    ]
    concept = build(meta, development_wells=iter(wells))
    assert concept.name == "Example"
    assert concept.region == "canada"
    assert concept.operator == "Example operator"
    assert concept.water_depth_m == 3.0
    assert concept.num_wells == 4
    assert "water_depth=development_wells_median" in concept.data_source
    assert "synthetic-wells" in concept.data_source
    assert meta == {
        "field": "Example",
        "operator": "Example operator",
        "source": "synthetic",
    }


def test_explicit_metadata_takes_precedence_and_keeps_well_provenance():
    """Explicit 7 m / 5 planned wells win over one inventory well at 3 m."""
    concept = build_canada_field_concept(
        {"field_name": "Example", "water_depth_m": 7, "num_wells": 5},
        development_wells=[well("example-a", 3)],
    )
    assert concept.water_depth_m == 7.0
    assert concept.num_wells == 5
    assert "water_depth=provided" in concept.data_source


def test_measured_zero_is_not_replaced_by_legacy_default():
    """Zero is a supplied magnitude under the FieldConcept non-negative contract."""
    field = next(iter(CANADA_WATER_DEPTH_M))
    concept = build_canada_field_concept(
        {"field_name": field}, development_wells=[well("example-a", 0, field)]
    )
    assert concept.water_depth_m == 0.0
    assert "water_depth=development_wells_median" in concept.data_source


def test_measured_depth_replaces_a_legacy_default():
    """Synthetic [3, 7] => (3 + 7) / 2 = 5 m, independent of the default."""
    field = next(iter(CANADA_WATER_DEPTH_M))
    concept = build_canada_field_concept(
        {"field_name": field},
        development_wells=[well("example-a", 3, field), well("example-b", 7, field)],
    )
    assert concept.water_depth_m == 5.0


def test_null_linked_depth_retains_default_with_distinct_provenance():
    """Freeze the first legacy fallback at 80 m, assumed from previous experience.

    This compatibility oracle is independent of production depth values; public
    source validation remains deferred and this is not a measured depth.
    """
    field = next(iter(CANADA_WATER_DEPTH_M))
    expected_default = 80.0
    concept = build_canada_field_concept(
        {"field_name": field}, development_wells=[well("example-a", None, field)]
    )
    assert concept.water_depth_m == expected_default
    assert concept.num_wells == 1
    assert "water_depth=legacy_default" in concept.data_source
    assert "development_wells_median" not in concept.data_source


def test_unknown_field_with_no_depth_stays_unknown():
    concept = build_canada_field_concept(
        {"field_name": "Example"}, development_wells=[well("example-a", None)]
    )
    assert concept.water_depth_m is None
    assert concept.num_wells == 1
    assert "water_depth=unknown" in concept.data_source


def test_unrelated_wells_cannot_set_count_depth_or_provenance():
    concept = build_canada_field_concept(
        {"field_name": "Example"},
        development_wells=[well("example-a", 3, "Elsewhere")],
    )
    assert concept.water_depth_m is None
    assert concept.num_wells is None
    assert "synthetic-wells" not in concept.data_source


def test_explicit_zero_is_retained():
    """Zero is explicit under the existing non-negative magnitude contract."""
    concept = build_canada_field_concept(
        {"field_name": "Example", "water_depth_m": 0},
        development_wells=[well("example-a", 3)],
    )
    assert concept.water_depth_m == 0.0


def test_summary_conflicts_are_not_hidden_by_explicit_depth():
    with pytest.raises(ValueError, match="Conflicting UWI"):
        build_canada_field_concept(
            {"field_name": "Example", "water_depth_m": 7},
            development_wells=[well("example-a", 3), well("example-a", 5)],
        )


def test_arcgis_attributes_feed_concept_without_geometry_or_column_assumptions():
    """One linked well with string depth '3' => median 3 m and one inventory UWI.

    Single-value median is the middle value, per the cited median definition.
    Geometry is deliberately different; only the explicitly mapped attributes
    are preserved on the well record. All coordinates are synthetic inputs.
    """
    payload = {
        "features": [
            {
                "attributes": {
                    "id": "example-a",
                    "linked": "Example",
                    "metres": "3",
                    "north": "1",
                    "east": "-1",
                },
                "geometry": {"x": 7, "y": 5},
            }
        ]
    }
    wells = parse_development_wells(
        payload,
        mapping=DevelopmentWellMapping("id", "linked", "metres", "north", "east"),
        source="synthetic-arcgis",
    )
    concept = build_canada_field_concept(
        {"field_name": "Example"}, development_wells=wells
    )
    assert concept.water_depth_m == 3.0
    assert concept.num_wells == 1
    assert "synthetic-arcgis" in concept.data_source
    assert wells[0].latitude == 1.0
    assert wells[0].longitude == -1.0


@pytest.mark.parametrize("depth", ["", "   ", "\t\n"])
def test_blank_explicit_depth_uses_linked_median(depth):
    concept = build_canada_field_concept(
        {"field_name": "Example", "water_depth_m": depth},
        development_wells=[well("example-a", 3)],
    )
    assert concept.water_depth_m == 3.0
    assert "water_depth=development_wells_median" in concept.data_source


@pytest.mark.parametrize("depth", ["unavailable", "3 metres", "nan", "inf"])
def test_malformed_explicit_depth_is_rejected(depth):
    with pytest.raises(ValueError, match="water_depth_m"):
        build_canada_field_concept(
            {"field_name": "Example", "water_depth_m": depth},
            development_wells=[well("example-a", 3)],
        )


@pytest.mark.parametrize("depth, expected", [(0, 0.0), ("0", 0.0), (" 7 ", 7.0)])
def test_numeric_explicit_depth_has_provided_provenance(depth, expected):
    meta = {"field_name": "Example", "water_depth_m": depth}
    concept = build_canada_field_concept(meta, development_wells=[well("example-a", 3)])
    assert concept.water_depth_m == expected
    assert "water_depth=provided" in concept.data_source
    assert meta["water_depth_m"] == depth
