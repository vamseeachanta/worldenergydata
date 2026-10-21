"""Financial convention and missing-input regressions; pack equations E2–E4."""

from xml.etree import ElementTree as ET

import pytest

from worldenergydata.field_development import FieldConcept, build_fdp_html
from worldenergydata.field_development.cost_estimator import (
    PerConceptCostEstimate,
    estimate_field_cost_portfolio,
)
from worldenergydata.field_development.enums import ConceptType, TreeType
from worldenergydata.field_development.integrations import estimate_economics
from worldenergydata.field_development.recommendation import ScoredConcept


def full_concept(**changes):
    values = dict(
        name="Synthetic",
        water_depth_m=1500,
        num_wells=6,
        plateau_rate_boed=60000,
        oil_price_usd_bbl=70,
        field_life_years=15,
        discount_rate=0.10,
    )
    return FieldConcept(**(values | changes))


@pytest.fixture
def fdas():
    config = pytest.importorskip("worldenergydata.fdas.core.config")
    pytest.importorskip("worldenergydata.fdas.api")
    return config


def test_proxy_has_hand_checked_npv_and_label(fdas):
    result = estimate_economics(full_concept())
    # DEFAULT_ASSUMPTIONS subsea15: 300 + 6*8 = 348 MM.
    # E3: 60,000*365/1e6 * (70*(1-.1875)-12) - 25 = 957.7625 MM/yr.
    # E4: -348 + 957.7625*(1-1.1**-15)/.1 = 6936.817723... MM.
    assert result.capex_mm == 348.0
    assert result.npv_mm == pytest.approx(6936.8, abs=0.05)
    assert "undeclined oil-price proxy" in result.note.lower()
    assert "gas price" in result.note.lower()
    assert "Undeclined oil-price proxy NPV" in build_fdp_html(full_concept())


def test_fractional_life_is_not_silently_truncated(fdas):
    result = estimate_economics(full_concept(field_life_years=15.5))
    assert result.capex_mm == 348.0
    assert result.npv_mm is None
    assert "whole" in result.note and "field_life_years" in result.note


def test_explicit_zero_discount_preserved(fdas):
    result = estimate_economics(full_concept(discount_rate=0.0))
    assert result.discount_rate == 0.0
    # Zero-discount E4: -348 + 15*957.7625 = 14018.4375 MM.
    assert result.npv_mm == pytest.approx(14018.4, abs=0.05)


def test_missing_well_count_blocks_economics(fdas):
    result = estimate_economics(full_concept(num_wells=None))
    assert result.capex_mm is None and result.npv_mm is None
    assert "num_wells" in result.note


@pytest.mark.parametrize(
    "key",
    [
        "HOST_CAPEX_MM",
        "SURF_PER_WELL_MM",
        "FIXED_OPEX_MM_PER_YEAR",
        "VARIABLE_OPEX_$/BBL",
        "ROYALTY_RATE",
        "DISCOUNT_RATE_ANNUAL",
    ],
)
def test_missing_assumption_cannot_be_zero_cost(fdas, monkeypatch, key):
    manager = fdas.AssumptionsManager()
    manager.assumptions = manager.assumptions.drop(columns=[key])
    monkeypatch.setattr(fdas, "AssumptionsManager", lambda: manager)
    result = estimate_economics(full_concept(discount_rate=None))
    assert result.npv_mm is None
    if key in ("HOST_CAPEX_MM", "SURF_PER_WELL_MM"):
        assert result.capex_mm is None
    assert key in result.note
    if key == "FIXED_OPEX_MM_PER_YEAR":
        portfolio = estimate_field_cost_portfolio(
            full_concept(), [_scored(ConceptType.FPSO)]
        )
        est = portfolio[ConceptType.FPSO]
        assert est.capex_mm is not None
        assert est.annual_opex_mm is None
        assert key in est.note
        table = build_fdp_html(full_concept()).split("Per-concept cost comparison", 1)[
            1
        ]
        table = table.split("</table>", 1)[0]
        assert "0.0 $MM/yr" not in table
        assert key in table
        rows = ET.fromstring("<table" + table.split("<table", 1)[1] + "</table>")
        assert len(rows.findall("tr")) > 1
        for row in rows.findall("tr")[1:]:
            assert row.findall("td")[2].text == "—"
            assert key in row.findall("td")[5].text


def _scored(concept_type):
    return ScoredConcept(concept_type=concept_type, tree_type=TreeType.WET)


@pytest.mark.parametrize("value", [-1, float("inf"), float("nan")])
def test_invalid_fixed_opex_is_not_evaluated(fdas, monkeypatch, value):
    manager = fdas.AssumptionsManager()
    key = "FIXED_OPEX_MM_PER_YEAR"
    manager.assumptions.loc[manager.assumptions.DEV_SYSTEM == "subsea15", key] = value
    monkeypatch.setattr(fdas, "AssumptionsManager", lambda: manager)
    est = estimate_field_cost_portfolio(full_concept(), [_scored(ConceptType.FPSO)])
    assert est[ConceptType.FPSO].annual_opex_mm is None
    assert key in est[ConceptType.FPSO].note


def test_explicit_zero_fixed_opex_is_evaluated(fdas, monkeypatch):
    manager = fdas.AssumptionsManager()
    manager.assumptions.loc[
        manager.assumptions.DEV_SYSTEM == "subsea15", "FIXED_OPEX_MM_PER_YEAR"
    ] = 0
    monkeypatch.setattr(fdas, "AssumptionsManager", lambda: manager)
    est = estimate_field_cost_portfolio(full_concept(), [_scored(ConceptType.FPSO)])
    assert est[ConceptType.FPSO].annual_opex_mm == 0.0


@pytest.mark.parametrize("known_opex", [0.0, 10.0])
def test_portfolio_ranks_unknown_opex_after_known_cost(monkeypatch, known_opex):
    from worldenergydata.field_development import cost_estimator

    unknown = PerConceptCostEstimate(ConceptType.SUBSEA_TIEBACK, capex_mm=1.0)
    known = PerConceptCostEstimate(
        ConceptType.FPSO, capex_mm=100.0, annual_opex_mm=known_opex
    )
    estimates = {est.concept_type: est for est in (unknown, known)}
    monkeypatch.setattr(
        cost_estimator,
        "estimate_per_concept_costs",
        lambda concept, scored: estimates[scored.concept_type],
    )
    portfolio = estimate_field_cost_portfolio(
        full_concept(), [_scored(ct) for ct in estimates]
    )
    assert list(portfolio) == [ConceptType.FPSO, ConceptType.SUBSEA_TIEBACK]


@pytest.mark.parametrize("key", ["HOST_CAPEX_MM", "SURF_PER_WELL_MM"])
def test_zero_capex_component_blocks_economics(fdas, monkeypatch, key):
    manager = fdas.AssumptionsManager()
    manager.assumptions.loc[manager.assumptions.DEV_SYSTEM == "subsea15", key] = 0
    monkeypatch.setattr(fdas, "AssumptionsManager", lambda: manager)
    result = estimate_economics(full_concept())
    assert result.capex_mm is None and result.npv_mm is None
    assert key in result.note
