"""Contract-rate seam and sourced Brazil royalty-only screening.

Synthetic amounts below are independent hand-calculation inputs, not field
observations. Fraction bounds [0, 1] are the definition of a fractional rate.
The example rate is the statutory base in Lei 9.478/1997, art. 47, caput;
a field calculation requires its concession contract (Decreto 2.705/1998,
art. 12, paragraph 2). No illustrative daily-rate bands are fiscal evidence.
"""

from datetime import datetime

import pandas as pd
import pytest

from worldenergydata.fdas.analysis.cashflow import CashflowEngine
from worldenergydata.fdas.core.config import AssumptionsManager
from worldenergydata.fdas.fiscal import (
    DEV_SYSTEMS,
    FiscalTermsValidationError,
    get_fiscal_terms,
    validate_deck,
)


def contract_deck():
    """Synthetic deck with caller-supplied rate; no jurisdictional default."""
    return {
        "schema_version": 1,
        "country": "synthetic-contract",
        "source_url": "https://www.planalto.gov.br/ccivil_03/decreto/d2705.htm",
        "source_ref": "Decreto 2.705/1998, art. 12, paragraph 2",
        "revision": "1",
        "effective_date": "2026-10-19",
        "royalty": {"model": "contractual"},
    }


def engine():
    return CashflowEngine(
        AssumptionsManager(), fiscal_terms=validate_deck(contract_deck())
    )


def test_brazil_deck_has_no_assumed_contract_rate():
    terms = get_fiscal_terms("brazil")
    assert terms.royalty.model == "contractual"
    assert terms.royalty.rate_by_dev_system is None
    assert terms.royalty.bands == ()
    assert "NOT_EVALUATED" in terms.notes
    assert "special participation" in terms.notes
    for dev_system in DEV_SYSTEMS:
        with pytest.raises(ValueError, match="contract"):
            terms.royalty.rate_for(dev_system)


@pytest.mark.parametrize(
    "rate", [None, True, "0.1", -0.1, 1.1, float("nan"), float("inf")]
)
@pytest.mark.parametrize("revenue", [{}, {"2024-02": 1_000_000}])
def test_contract_rate_required_and_validated(rate, revenue):
    with pytest.raises(ValueError, match="contract"):
        engine().calculate_royalty(revenue, royalty_rate=rate)


@pytest.mark.parametrize("rate, expected", [(0, 0), (0.1, 100_000), (1, 1_000_000)])
def test_contract_royalty_hand_calculation(rate, expected):
    """Synthetic base 1,000,000 times supplied fractions 0, 0.1, 1.

    Results are 0, 100,000, 1,000,000; endpoints test generic fractions only.
    The 0.1 example corresponds to Lei 9.478/1997, art. 47, caput.
    """
    assert engine().calculate_royalty({"2024-02": 1_000_000}, rate) == {
        "2024-02": expected
    }


@pytest.mark.parametrize("field, value", [("bands", []), ("rate_by_dev_system", None)])
def test_contract_deck_rejects_embedded_rates(field, value):
    deck = contract_deck()
    deck["royalty"][field] = value
    with pytest.raises(FiscalTermsValidationError, match=field):
        validate_deck(deck)


def test_monthly_cashflow_passes_contract_rate():
    """Hand calculation: 29,000 bbl x 20 USD/bbl = 580,000 USD.

    Synthetic February 2024 inputs; at an explicitly supplied 0.1 fraction
    (Lei 9.478/1997, art. 47 base), royalty = 58,000 USD. Calendar length
    does not affect a contractual percentage; all other cashflow components
    remain legacy screening assumptions and are outside this assertion.
    """
    production = pd.DataFrame({"YEAR_MONTH": ["2024-02"], "MONTHLY_OIL_BBL": [29_000]})
    cashflows = engine().generate_monthly_cashflow(
        production,
        {"drilling_monthly": {}},
        {"2024-02": 20},
        datetime(2024, 2, 1),
        royalty_rate=0.1,
    )
    february = next(cf for cf in cashflows if cf.year_month == "2024-02")
    assert february.oil_revenue_usd == 580_000
    assert february.royalty_usd == 58_000


def test_monthly_cashflow_does_not_invent_contract_rate():
    production = pd.DataFrame({"YEAR_MONTH": ["2024-02"], "MONTHLY_OIL_BBL": [29_000]})
    with pytest.raises(ValueError, match="contract"):
        engine().generate_monthly_cashflow(
            production, {"drilling_monthly": {}}, {"2024-02": 20}, datetime(2024, 2, 1)
        )
