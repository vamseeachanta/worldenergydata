"""Financial convention and missing-input regressions; pack equations E2–E4."""

import pytest

from worldenergydata.field_development import FieldConcept, build_fdp_html
from worldenergydata.field_development.integrations import estimate_economics


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
    # E3: 60,000*365/1e6 * (70*(1-.188)-12) - 25 = 956.996 MM/yr.
    # E4: -348 + 956.996*(1-1.1**-15)/.1 = 6930.987663... MM.
    assert result.capex_mm == 348.0
    assert result.npv_mm == pytest.approx(6931.0, abs=0.05)
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
    assert result.npv_mm == pytest.approx(14006.9, abs=0.05)


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


@pytest.mark.parametrize("key", ["HOST_CAPEX_MM", "SURF_PER_WELL_MM"])
def test_zero_capex_component_blocks_economics(fdas, monkeypatch, key):
    manager = fdas.AssumptionsManager()
    manager.assumptions.loc[manager.assumptions.DEV_SYSTEM == "subsea15", key] = 0
    monkeypatch.setattr(fdas, "AssumptionsManager", lambda: manager)
    result = estimate_economics(full_concept())
    assert result.capex_mm is None and result.npv_mm is None
    assert key in result.note
