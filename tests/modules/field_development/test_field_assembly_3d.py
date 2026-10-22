# ABOUTME: Hand-calculated field-scene placement, routing and STEP tests.
# ABOUTME: CadQuery remains optional for the field-development package.
"""Synthetic geometry, not equipment design values or acceptance criteria.

All dimensions below are chosen test inputs. Expected positions follow the
independent arithmetic in each test. Millimetre conversions use NIST, Metric
(SI) Prefixes (2025), table: kilo = 10**3, milli = 10**-3.
https://www.nist.gov/pml/owm/metric-si-prefixes
Volume basis: OpenStax, Prealgebra 2e (2020), section 9.6, cylinder volume
V = pi * r**2 * h. Equal circular mitres exchange equal wedge volumes, leaving
the sum of straight-cylinder volumes used in the hand calculations below.
https://openstax.org/books/prealgebra-2e/pages/9-6-solve-geometry-applications-volume-and-surface-area
Floating comparisons use pytest.approx's default software tolerances only.
"""

from __future__ import annotations

import copy
import math
from dataclasses import replace

import pytest

pytest.importorskip("cadquery")

from worldenergydata.field_development.field_assembly_3d import (
    FieldDimensions,
    build_field_assembly,
    export_field_step,
)
from worldenergydata.field_development.layout_optimization import (
    LayoutSolution,
    Well,
    optimize_layout,
)


@pytest.fixture
def dimensions():
    """Arbitrary positive envelope sizes in metres, supplied by the caller."""
    return FieldDimensions(
        tree_diameter_m=2,
        tree_height_m=4,
        manifold_size_m=(6, 4, 2),
        host_size_m=(20, 10, 5),
        flowline_diameter_m=0.4,
        umbilical_diameter_m=0.2,
    )


@pytest.fixture
def inputs(dimensions):
    """Two synthetic wells; centroid = (1, 2) km; host = (4, 6) km."""
    wells = [Well("a", 0, 2), Well("b", 2, 2)]
    return {
        "layout_solution": optimize_layout(wells, host=(4, 6)),
        "wells": wells,
        "dimensions": dimensions,
        "seabed_z_m": -100,
        "host_z_m": 0,
        "umbilical_offset_m": (0, 2),
    }


def _group(assembly, name):
    return next(child for child in assembly.children if child.name == name)


def test_equipment_count_validity_and_placement(inputs):
    """2 wells -> 2 trees; mean x=(0+2)/2=1 km -> 1 manifold.

    Tree a: centre (0, 2000) m, base -100 m, top -96 m.
    Manifold: centre (1000, 2000) m; width 6 m -> x=[997,1003] m.
    Host: centre (4000,6000) m; base 0 m, height 5 m.
    Multiply metre coordinates by 1000 to get each expected bound in mm.
    """
    assembly = build_field_assembly(**inputs)
    assert assembly.name == "field"
    trees = _group(assembly, "trees")
    manifolds = _group(assembly, "manifolds")
    assert len(trees.children) == 2
    assert len(manifolds.children) == 1
    tree = trees.children[0]
    assert tree.metadata["well_id"] == "a"
    bounds = tree.toCompound().BoundingBox()
    assert (bounds.xmin, bounds.xmax) == pytest.approx((-1000, 1000))
    assert (bounds.ymin, bounds.ymax) == pytest.approx((1999000, 2001000))
    assert (bounds.zmin, bounds.zmax) == pytest.approx((-100000, -96000))
    bounds = manifolds.toCompound().BoundingBox()
    assert (bounds.xmin, bounds.xmax) == pytest.approx((997000, 1003000))
    assert (bounds.ymin, bounds.ymax) == pytest.approx((1998000, 2002000))
    assert (bounds.zmin, bounds.zmax) == pytest.approx((-100000, -98000))
    bounds = _group(assembly, "host").toCompound().BoundingBox()
    assert (bounds.xmin, bounds.xmax) == pytest.approx((3990000, 4010000))
    assert (bounds.ymin, bounds.ymax) == pytest.approx((5995000, 6005000))
    assert (bounds.zmin, bounds.zmax) == pytest.approx((0, 5000))
    assert assembly.toCompound().isValid()
    assert all(solid.isValid() for solid in assembly.toCompound().Solids())


def test_routes_reuse_layout_and_lift_to_host(inputs):
    """Flowline: (1000,2000,-100)->(4000,6000,-100)->(4000,6000,0) m.

    Plan leg length sqrt(3000**2+4000**2)=5000 m; riser=100 m.
    Umbilical adds the caller's (0,2) m landing offset to both endpoints.
    Metadata records exact centreline points, independently checked here;
    cylinder/sweep solids must span the horizontal leg and vertical riser.
    For circular mitred sweeps, V=pi*r**2*L: L=5,100,000 mm;
    r=200 mm for the flowline and 100 mm for the umbilical.
    """
    assembly = build_field_assembly(**inputs)
    for group, name, expected in [
        (
            "flowlines",
            "flowline_0",
            ((1000, 2000, -100), (4000, 6000, -100), (4000, 6000, 0)),
        ),
        (
            "umbilicals",
            "umbilical_0",
            ((1000, 2002, -100), (4000, 6002, -100), (4000, 6002, 0)),
        ),
    ]:
        routes = _group(assembly, group)
        assert len(routes.children) == 1
        route = routes.children[0]
        assert route.name == name
        assert route.metadata["waypoints_m"] == expected
        shape = route.toCompound()
        assert shape.isValid()
        assert len(shape.Solids()) == 1
        radius = 200 if group == "flowlines" else 100
        assert shape.Volume() == pytest.approx(math.pi * radius**2 * 5100000)
        bounds = shape.BoundingBox()
        assert bounds.xmin < 1000000
        assert bounds.xmax > 4000000
        assert bounds.zmin < -100000
        assert bounds.zmax == pytest.approx(0)


def test_multiple_manifolds_and_deterministic_names(inputs):
    """With one cluster per well, 2 wells -> 2 manifolds and 2 routes of each kind."""
    inputs["layout_solution"] = optimize_layout(
        inputs["wells"], n_manifolds=2, host=(4, 6)
    )
    first = build_field_assembly(**inputs)
    inputs["wells"] = list(reversed(inputs["wells"]))
    inputs["layout_solution"].manifolds = dict(
        reversed(list(inputs["layout_solution"].manifolds.items()))
    )
    second = build_field_assembly(**inputs)
    for group in ("trees", "manifolds", "flowlines", "umbilicals"):
        children = _group(first, group).children
        assert len(children) == 2
        assert [c.name for c in children] == [
            c.name for c in _group(second, group).children
        ]
        assert [c.metadata for c in children] == [
            c.metadata for c in _group(second, group).children
        ]


def test_host_above_manifold_needs_only_vertical_routes(inputs):
    """Coincident plan endpoints remove the zero-length plan leg; rise = 100 m."""
    inputs["layout_solution"].host = (1, 2)
    inputs["umbilical_offset_m"] = (0, 0)
    assembly = build_field_assembly(**inputs)
    for group in ("flowlines", "umbilicals"):
        route = _group(assembly, group).children[0]
        assert route.metadata["waypoints_m"] == ((1000, 2000, -100), (1000, 2000, 0))
        assert route.toCompound().isValid()


@pytest.mark.parametrize(
    "host", [(4, 6), (-2, -2), (1, 7), (6, 2), (1, -3), (-4, 2), (4, -2), (-2, 6)]
)
def test_route_volume_in_different_plan_directions(inputs, host):
    """From (1,2) km each host has a 5 km plan leg (3-4-5 or axis-aligned).

    Translate the entire field by (1234,-2345) km; length stays 5100 m.
    Route volumes remain pi * radius**2 * 5100000 mm, with radii 200/100 mm.
    This checks CAD construction at a large nonzero local-frame origin.
    """
    inputs["wells"] = [Well(w.id, w.x + 1234, w.y - 2345) for w in inputs["wells"]]
    inputs["layout_solution"] = optimize_layout(
        inputs["wells"], host=(host[0] + 1234, host[1] - 2345)
    )
    assembly = build_field_assembly(**inputs)
    assert assembly.toCompound().isValid()
    for group, radius in (("flowlines", 200), ("umbilicals", 100)):
        shape = _group(assembly, group).children[0].toCompound()
        assert shape.isValid()
        assert len(shape.Solids()) == 1
        assert shape.Volume() == pytest.approx(math.pi * radius**2 * 5100000)


def test_input_layout_and_wells_unchanged(inputs):
    before = copy.deepcopy(inputs)
    build_field_assembly(**inputs)
    assert inputs == before


def _route_inputs(inputs, horizontal_m, riser_m):
    inputs["wells"] = [Well("a", 0, 0)]
    inputs["layout_solution"] = optimize_layout(
        inputs["wells"], host=(horizontal_m / 1000, 0)
    )
    inputs["seabed_z_m"] = 0
    inputs["host_z_m"] = riser_m
    return inputs


@pytest.mark.parametrize("leg", ["horizontal", "riser"])
@pytest.mark.parametrize("length_m", [0.1, 0.2])
@pytest.mark.parametrize("field", ["flowline_diameter_m", "umbilical_diameter_m"])
def test_mitred_route_legs_at_or_below_radius_rejected(inputs, leg, length_m, field):
    """A 90-degree mitre needs each leg longer than the 0.2 m radius."""
    inputs = _route_inputs(
        inputs,
        horizontal_m=length_m if leg == "horizontal" else 100,
        riser_m=length_m if leg == "riser" else 100,
    )
    inputs["dimensions"] = replace(
        inputs["dimensions"], flowline_diameter_m=0.1, umbilical_diameter_m=0.1
    )
    inputs["dimensions"] = replace(inputs["dimensions"], **{field: 0.4})
    with pytest.raises(ValueError, match="route.*radius"):
        build_field_assembly(**inputs)


@pytest.mark.parametrize("leg", ["horizontal", "riser"])
def test_mitred_route_just_above_radius_is_valid(inputs, leg):
    """0.201 m clears a 0.2 m radius; total path length is 100.201 m."""
    inputs = _route_inputs(
        inputs,
        horizontal_m=0.201 if leg == "horizontal" else 100,
        riser_m=0.201 if leg == "riser" else 100,
    )
    assembly = build_field_assembly(**inputs)
    for group, radius in (("flowlines", 200), ("umbilicals", 100)):
        shape = _group(assembly, group).children[0].toCompound()
        assert shape.isValid()
        assert len(shape.Solids()) == 1
        assert shape.Volume() == pytest.approx(math.pi * radius**2 * 100201)


def test_short_vertical_only_route_is_valid(inputs):
    """A straight 0.1 m riser has no mitre; volume is pi*r**2*100 mm."""
    assembly = build_field_assembly(**_route_inputs(inputs, 0, 0.1))
    for group, radius in (("flowlines", 200), ("umbilicals", 100)):
        shape = _group(assembly, group).children[0].toCompound()
        assert shape.isValid()
        assert len(shape.Solids()) == 1
        assert shape.Volume() == pytest.approx(math.pi * radius**2 * 100)


def test_step_export_keeps_named_hierarchy(inputs, tmp_path):
    """Export must write ISO-10303 STEP with every scene part's product name."""
    assembly = build_field_assembly(**inputs)
    path = tmp_path / "field.step"
    assert export_field_step(assembly, path) == path
    assert path.stat().st_size > 0
    contents = path.read_text()
    assert "ISO-10303" in contents
    for name in (
        "field",
        "tree_0",
        "tree_1",
        "manifold_0",
        "host",
        "flowline_0",
        "umbilical_0",
    ):
        assert f"'{name}'" in contents


@pytest.mark.parametrize("as_string", [False, True])
def test_step_export_missing_parent_raises(inputs, tmp_path, as_string):
    assembly = build_field_assembly(**inputs)
    path = tmp_path / "missing" / "field.step"
    with pytest.raises(OSError, match="STEP"):
        export_field_step(assembly, str(path) if as_string else path)
    assert not path.exists()


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf")])
@pytest.mark.parametrize(
    "field",
    ["tree_diameter_m", "tree_height_m", "flowline_diameter_m", "umbilical_diameter_m"],
)
def test_invalid_dimensions_rejected(inputs, value, field):
    inputs["dimensions"] = replace(inputs["dimensions"], **{field: value})
    with pytest.raises(ValueError, match=field):
        build_field_assembly(**inputs)


@pytest.mark.parametrize("field", ["manifold_size_m", "host_size_m"])
@pytest.mark.parametrize("value", [(1, 2), (1, 0, 3), (1, float("inf"), 3)])
def test_invalid_box_sizes_rejected(inputs, field, value):
    inputs["dimensions"] = replace(inputs["dimensions"], **{field: value})
    with pytest.raises(ValueError, match=field):
        build_field_assembly(**inputs)


@pytest.mark.parametrize(
    "field,value",
    [
        ("host_z_m", -100),
        ("host_z_m", -101),
        ("host_z_m", float("nan")),
        ("seabed_z_m", float("inf")),
        ("umbilical_offset_m", (float("nan"), 0)),
    ],
)
def test_invalid_elevation_or_offset_rejected(inputs, field, value):
    inputs[field] = value
    with pytest.raises(ValueError):
        build_field_assembly(**inputs)


@pytest.mark.parametrize(
    "case",
    [
        "empty",
        "duplicate",
        "assignment",
        "target",
        "count",
        "well_nan",
        "host_nan",
        "manifold_nan",
    ],
)
def test_inconsistent_layout_rejected(inputs, case):
    layout = inputs["layout_solution"]
    if case == "empty":
        inputs["wells"] = []
        inputs["layout_solution"] = LayoutSolution()
    elif case == "duplicate":
        inputs["wells"].append(inputs["wells"][0])
    elif case == "assignment":
        layout.assignment.pop("a")
    elif case == "target":
        layout.assignment["a"] = "missing"
    elif case == "count":
        layout.n_manifolds += 1
    elif case == "well_nan":
        inputs["wells"][0] = Well("a", float("nan"), 0)
    elif case == "host_nan":
        layout.host = (float("nan"), 0)
    elif case == "manifold_nan":
        layout.manifolds["mf-1"] = (float("nan"), 0)
    with pytest.raises(ValueError):
        build_field_assembly(**inputs)
