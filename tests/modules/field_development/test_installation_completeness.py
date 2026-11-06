"""Independent installation-filter examples and missing-basis checks.

Basis: issue 1323 requires populated installation results and sparse-input
checks. The filter contract is integrations.vessel_feasibility: rating >= input
water depth, and positive pipelay tension for wet trees. These are catalog
screening predicates, not engineering acceptance limits or design qualification.
All tabulated numbers below are synthetic test inputs, not measured ratings.
"""

import pandas as pd
import pytest

from worldenergydata.field_development import ConceptType, FieldConcept
from worldenergydata.field_development.enums import TreeType
from worldenergydata.field_development.integrations import vessel_feasibility
from worldenergydata.field_development.recommendation import ScoredConcept
from worldenergydata.vessel_fleet.loaders import construction_vessel_loader


@pytest.fixture
def catalog(monkeypatch, tmp_path):
    """Use the real Parquet loader; substitute only its data directory."""
    monkeypatch.setattr(construction_vessel_loader, "_DATA_DIR", tmp_path)

    def write(frame):
        frame.to_parquet(tmp_path / "construction_vessels.parquet", index=False)

    return write


def fleet():
    """Synthetic given table; boundary rating equals the input depth."""
    return pd.DataFrame(
        {
            "VESSEL_NAME": ["shallow", "boundary", "deep", "no-pipelay"],
            "WATER_DEPTH_RATING_M": [500, 1000, 1500, 2000],
            "PIPELAY_TENSION_T": [100, 100, 200, 0],
            "MAIN_CRANE_CAPACITY_T": [50, 80, 120, 300],
        }
    )


def screen(tree_type=TreeType.WET):
    return vessel_feasibility(
        FieldConcept(name="Synthetic", water_depth_m=1000),
        ScoredConcept(concept_type=ConceptType.SEMISUB_FPS, tree_type=tree_type),
    )


@pytest.mark.parametrize(
    "tree_type,names,crane",
    [
        (TreeType.WET, ["boundary", "deep"], 120),
        (TreeType.DRY, ["boundary", "deep", "no-pipelay"], 300),
    ],
)
def test_populated_catalog_matches_hand_count(catalog, tree_type, names, crane):
    """At 1000 m, rows boundary/deep/no-pipelay pass depth (3 rows).

    Wet trees remove no-pipelay (zero tension): 2 rows, max(80,120)=120 t.
    Dry trees retain all 3: max(80,120,300)=300 t. Expected identities are
    listed independently above; no expected value calls the filter under test.
    """
    catalog(fleet())
    result = screen(tree_type)
    assert result.water_depth_reachable is True
    assert result.capable_vessel_count == len(names)
    assert result.example_vessels == names
    assert result.max_crane_capacity_t == crane
    assert result.note == ""


@pytest.mark.parametrize(
    "column", ["WATER_DEPTH_RATING_M", "PIPELAY_TENSION_T", "VESSEL_NAME"]
)
def test_missing_required_column_is_not_evaluated(catalog, column):
    catalog(fleet().drop(columns=[column]))
    result = screen()
    assert result.water_depth_reachable is None
    assert result.capable_vessel_count == 0
    assert result.example_vessels == []
    assert result.max_crane_capacity_t is None
    assert "not evaluated" in result.note.lower()
    assert column in result.note


@pytest.mark.parametrize("column", ["WATER_DEPTH_RATING_M", "PIPELAY_TENSION_T"])
def test_sparse_ratings_do_not_become_zero_capability(catalog, column):
    frame = fleet()
    frame.loc[0, column] = float("nan")
    catalog(frame)
    result = screen()
    assert result.water_depth_reachable is None
    assert result.capable_vessel_count == 0
    assert "not evaluated" in result.note.lower()
    assert column in result.note


def test_dry_tree_does_not_require_pipelay_basis(catalog):
    """Three depth-qualified rows remain; no pipelay predicate applies."""
    catalog(fleet().drop(columns=["PIPELAY_TENSION_T"]))
    result = screen(TreeType.DRY)
    assert result.water_depth_reachable is True
    assert result.capable_vessel_count == 3


def test_complete_catalog_with_no_match_is_evaluated(catalog):
    """Only the 500 m row is retained; 500 < 1000 so count is zero."""
    catalog(fleet().iloc[:1])
    result = screen()
    assert result.water_depth_reachable is False
    assert result.capable_vessel_count == 0
    assert result.note == ""


def test_empty_catalog_does_not_establish_no_capability(catalog):
    catalog(fleet().iloc[:0])
    result = screen()
    assert result.water_depth_reachable is None
    assert "not evaluated" in result.note.lower()
    assert "empty" in result.note.lower()


@pytest.mark.parametrize("empty", [True, False])
def test_report_distinguishes_missing_basis_from_evaluated_zero(catalog, empty):
    """Empty evidence is unevaluated; a sole 500 m row gives a known zero."""
    from worldenergydata.field_development.fdp_report import _economics_block
    from worldenergydata.field_development.integrations import (
        Economics,
        EnrichedConcept,
        HardwarePicks,
    )

    catalog(fleet().iloc[:0] if empty else fleet().iloc[:1])
    vessel = screen()
    enriched = EnrichedConcept(
        scored=ScoredConcept(
            concept_type=ConceptType.SEMISUB_FPS, tree_type=TreeType.WET
        ),
        vessel=vessel,
        hardware=HardwarePicks(),
    )
    html = _economics_block(Economics(), [enriched], None)
    card = html.split('Install vessels</div><div class="v">', 1)[1].split("<", 1)[0]
    assert card == ("Not evaluated" if empty else "0")
    if empty:
        assert "Not evaluated: construction vessel catalog empty" in html
