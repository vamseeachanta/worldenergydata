"""Metadata tests; synthetic prices are caller inputs, not empirical constants."""

import pandas as pd

from worldenergydata.fdas.core.economics_basis import reference_chain_basis


def test_missing_production_is_not_an_evaluated_zero():
    basis = reference_chain_basis(pd.DataFrame(), 70, royalty_basis="unspecified")
    assert basis["status"] == "NOT_EVALUATED"
    assert basis["production_sources"] == []
    assert basis["fiscal_validation"] == "NOT_EVALUATED"
    assert basis["discount_rate_annual"] is None


def test_supplied_sources_and_deck_are_reported_without_promotion():
    production = pd.DataFrame({"source": ["synthetic", None, "synthetic"]})
    gas = {"2024-01": 3}
    basis = reference_chain_basis(
        production, 70, royalty_basis="test_deck_royalty_only", gas_prices=gas
    )
    assert basis["production_sources"] == ["synthetic"]
    assert basis["royalty_basis"] == "test_deck_royalty_only"
    assert basis["oil_price_usd_bbl"] == 70
    assert basis["gas_prices_usd_mcf"] == gas
    assert basis["capex"] == "model_host_only_no_drilling_or_facilities_schedule"
    assert basis["opex"] == "variable_fdas_assumptions_fixed_excluded"
    gas.clear()
    assert basis["gas_prices_usd_mcf"] == {"2024-01": 3}
