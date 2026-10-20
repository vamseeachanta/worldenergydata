"""Inventory tests use synthetic records and independent set/count arithmetic.

Depths are chosen test inputs, not equipment ratings or acceptance limits.
No operational suitability can be inferred from these fixtures.
"""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from worldenergydata.vessel_fleet.constants import InterventionClass
from worldenergydata.vessel_fleet.fleet_catalog import classify_asset_class
from worldenergydata.vessel_fleet.intervention_inventory import (
    load_intervention_inventory,
    query_intervention_inventory,
    summarize_intervention_inventory,
)
from worldenergydata.vessel_fleet.schemas.intervention_vessel import (
    InterventionVesselSchema,
)


def write_roster(tmp_path: Path, filename: str, rows: list[dict]) -> Path:
    path = tmp_path / filename
    path.write_text(yaml.safe_dump({"vessels": rows}), encoding="utf-8")
    return path


@pytest.mark.parametrize("kind", ["rlwi_monohull", "heavy_intervention_semi"])
def test_rig_types_classify_without_a_known_name(kind):
    assert classify_asset_class(rig_type=kind) == kind


@pytest.mark.parametrize("value", ["light", " LIGHT ", InterventionClass.LIGHT])
def test_schema_normalizes_typed_intervention_class(value):
    record = InterventionVesselSchema(VESSEL_NAME="synthetic", INTERVENTION_CLASS=value)
    assert record.INTERVENTION_CLASS is InterventionClass.LIGHT
    assert record.model_dump(mode="json")["INTERVENTION_CLASS"] == "light"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), -1])
def test_depth_must_be_finite_and_nonnegative(value):
    """Zero is the physical lower bound of a water depth, not a design limit."""
    with pytest.raises(ValidationError):
        InterventionVesselSchema(VESSEL_NAME="synthetic", WATER_DEPTH_RATING_M=value)


def test_observations_merge_with_unknown_conflicts(tmp_path):
    """Two listings of one hull: {100, 200} conflicts; {True} agrees.

    A missing observation does not oppose a known value. Distinct source
    ratings are deliberately not averaged, maximized or selected by file order.
    """
    a = write_roster(
        tmp_path,
        "a.yml",
        [
            {
                "name": "synthetic-alpha",
                "vessel_type": "rlwi_monohull",
                "water_depth_rating_m": 100,
                "gom_resident": True,
                "intervention_class": "light",
                "riser_capable": False,
                "source": "synthetic test observation A",
            }
        ],
    )
    b = write_roster(
        tmp_path,
        "b.yml",
        [
            {
                "vessel_name": "synthetic-alpha",
                "vessel_type": "rlwi_monohull",
                "water_depth_rating_m": 200,
                "gom_resident": True,
                "source_url": "https://example.org/synthetic",
            }
        ],
    )
    assets = load_intervention_inventory([a, b])
    assert len(assets) == 1
    asset = assets[0]
    assert asset.vessel.WATER_DEPTH_RATING_M is None
    assert asset.vessel.GOM_RESIDENT is True
    assert asset.vessel.RISER_CAPABLE is False
    assert asset.conflicts == ("WATER_DEPTH_RATING_M",)
    assert len(asset.observations) == 2
    assert {o.vessel.WATER_DEPTH_RATING_M for o in asset.observations} == {100, 200}
    assert asset.observations[0].locator == "a.yml:vessels[0]"
    assert asset.observations[1].source == "https://example.org/synthetic"


def test_query_uses_inclusive_depth_and_explicit_residency(tmp_path):
    """At input depth 100: 100 >= 100 passes; 50 < 100 fails.

    A third record's depth is unknown. A resident filter matches only True,
    not unknown; passing False selects non-residents rather than all records.
    """
    path = write_roster(
        tmp_path,
        "roster.yml",
        [
            {
                "name": "synthetic-alpha",
                "vessel_type": "rlwi_monohull",
                "water_depth_rating_m": 100,
                "gom_resident": True,
            },
            {
                "name": "synthetic-beta",
                "vessel_type": "mpsv",
                "water_depth_rating_m": 50,
                "gom_resident": False,
            },
            {"name": "synthetic-gamma", "vessel_type": "lift_boat"},
        ],
    )
    assets = load_intervention_inventory([path])
    assert len(query_intervention_inventory(assets, minimum_depth_m=100)) == 1
    assert len(query_intervention_inventory(assets, gom_resident=True)) == 1
    assert len(query_intervention_inventory(assets, gom_resident=False)) == 1
    assert len(query_intervention_inventory(assets, asset_class="mpsv_osv")) == 1
    assert len(query_intervention_inventory(assets, riser_capable=True)) == 0
    assert len(query_intervention_inventory(assets)) == 3


def test_summary_bounds_are_observed_not_population_estimates(tmp_path):
    """Hand count: three dedicated assets, one True, one False, one unknown.

    Observed resident interval = [1, 1 + 1] = [1, 2]. A support asset is
    excluded from this dedicated interval. Global observed RLWI count = 2.
    """
    path = write_roster(
        tmp_path,
        "roster.yml",
        [
            {
                "name": "synthetic-alpha",
                "vessel_type": "rlwi_monohull",
                "gom_resident": True,
            },
            {"name": "synthetic-beta", "vessel_type": "rlwi_monohull"},
            {
                "name": "synthetic-gamma",
                "vessel_type": "heavy_intervention_semi",
                "gom_resident": False,
            },
            {"name": "synthetic-delta", "vessel_type": "mpsv", "gom_resident": True},
        ],
    )
    summary = summarize_intervention_inventory(load_intervention_inventory([path]))
    assert summary["distinct_assets"] == 4
    assert summary["by_asset_class"]["rlwi_monohull"] == 2
    assert summary["gom_dedicated_observed"] == {"lower": 1, "upper": 2}
    assert summary["unknown_depth_assets"] == 4
    for item in summary["research_estimates"].values():
        assert item["status"] == "NOT_EVALUATED"
        assert item["source"]
        assert item["reason"]


def test_class_and_residency_conflicts_widen_observed_upper_bound(tmp_path):
    """One hull may be dedicated and resident; neither attribute is settled.

    Lower bound = 0 confirmed dedicated residents. Upper bound = 1 candidate.
    """
    a = write_roster(
        tmp_path,
        "a.yml",
        [
            {
                "name": "synthetic-alpha",
                "vessel_type": "rlwi_monohull",
                "gom_resident": True,
            }
        ],
    )
    b = write_roster(
        tmp_path,
        "b.yml",
        [
            {
                "name": "synthetic-alpha",
                "vessel_type": "mpsv",
                "gom_resident": False,
            }
        ],
    )
    assets = load_intervention_inventory([a, b])
    assert assets[0].asset_class == "other"
    assert "ASSET_CLASS" in assets[0].conflicts
    assert assets[0].vessel.GOM_RESIDENT is None
    assert not query_intervention_inventory(assets, gom_resident=True)
    summary = summarize_intervention_inventory(assets)
    assert summary["gom_dedicated_observed"] == {"lower": 0, "upper": 1}
    assert summary["conflicted_assets"] == 1


@pytest.mark.parametrize("depth", [-1, float("nan"), float("inf")])
def test_invalid_query_depth_rejected(depth):
    with pytest.raises(ValueError):
        query_intervention_inventory([], minimum_depth_m=depth)


def test_missing_or_malformed_roster_fails_explicitly(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_intervention_inventory([tmp_path / "absent.yml"])
    path = write_roster(tmp_path, "bad.yml", [{"vessel_type": "rlwi_monohull"}])
    with pytest.raises(TypeError, match="VESSEL_NAME"):
        load_intervention_inventory([path])
    path.write_text("vessels: invalid\n", encoding="utf-8")
    with pytest.raises(TypeError, match="vessels"):
        load_intervention_inventory([path])


def test_packaged_rosters_preserve_every_observation():
    """Expected rows come directly from the two committed YAML lists.

    Count conservation uses independent list lengths, not a hardcoded market
    figure. Duplicate source listings must survive as observations of a hull.
    """
    from worldenergydata.vessel_fleet.intervention_inventory import DEFAULT_ROSTERS

    expected = sum(
        len(yaml.safe_load(p.read_text())["vessels"]) for p in DEFAULT_ROSTERS
    )
    assets = load_intervention_inventory()
    assert sum(len(asset.observations) for asset in assets) == expected
    assert len(assets) < expected
    assert any(asset.conflicts for asset in assets)


def test_worked_example(capsys):
    """Five artificial listings -> four hulls; [one, one + one] residents.

    Alpha has conflicting depth; beta is the sole depth-qualified RLWI input.
    This independent arithmetic is written out in the example documentation.
    """
    import runpy

    script = (
        Path(__file__).resolve().parents[3]
        / "examples/vessel_fleet/intervention_inventory.py"
    )
    runpy.run_path(str(script), run_name="__main__")
    assert capsys.readouterr().out == (
        "Distinct assets: 4\n"
        "Observed dedicated resident bounds: 1 to 2\n"
        "Conflicted assets: 1\n"
        "RLWI depth matches: 1\n"
    )
