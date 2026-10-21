"""Royalty consistency with repository source notes, not current legal advice.

Sources are the shipped fiscal decks' source_ref notes, recorded 2026-07-03.
The BOEM link in us_gom.yml is unavailable; lease applicability is unqualified.
"""

import re
from decimal import Decimal

import pytest

from worldenergydata.fdas.analysis.cashflow import CashflowEngine
from worldenergydata.fdas.core.config import AssumptionsManager
from worldenergydata.fdas.fiscal import (
    DEV_SYSTEMS,
    available_countries,
    get_fiscal_terms,
)


@pytest.mark.parametrize("country", available_countries())
@pytest.mark.parametrize("dev_system", DEV_SYSTEMS)
def test_shipped_royalty_matches_its_source_note(country, dev_system):
    """Compare each shipped rate with its note independently of legacy config.

    us_gom.yml source_ref: 12.5% shallow-water and 18.75% deepwater.
    Hand conversion: 12.5 / 100 = 0.125; 18.75 / 100 = 0.1875.
    norway.yml source_ref: no production royalty, hence zero.
    uk.yml source_ref: royalty abolished, hence zero.
    Percent conversion uses Decimal to avoid rounding the source percentages.
    """
    terms = get_fiscal_terms(country)
    if country == "us_gom":
        match = re.search(
            r"([\d.]+)% shallow-water, ([\d.]+)% deepwater", terms.source_ref
        )
        assert match, "US Gulf source note must state both percentages"
        shallow, deep = match.groups()
        percent = shallow if dev_system == "dry" else deep
        expected = float(Decimal(percent) / Decimal(100))
    else:
        no_royalty_note = {
            "norway": "no production royalty on the NCS",
            "uk": "UKCS royalty abolished from 1 Jan 2003",
        }
        assert no_royalty_note[country] in terms.source_ref
        expected = 0.0  # The cited source note states absence of royalty.
    assert terms.royalty.rate_for(dev_system) == expected


@pytest.mark.parametrize("use_deck", [False, True])
@pytest.mark.parametrize("dev_system", DEV_SYSTEMS)
def test_us_gom_royalty_hand_calculation(use_deck, dev_system):
    """Synthetic USD revenues; expected values are independent hand arithmetic.

    Source: us_gom.yml source_ref, recorded 2026-07-03, BOEM royalty note.
    For USD 1,000,000: dry = 1,000,000 * 12.5/100 = 125,000;
    deepwater/default = 1,000,000 * 18.75/100 = 187,500.
    For zero revenue: 0 * either rate = 0.
    Formula: royalty = gross revenue * fractional rate (percentage definition).
    """
    engine = CashflowEngine(
        AssumptionsManager(),
        dev_system=dev_system,
        fiscal_terms=get_fiscal_terms("us_gom") if use_deck else None,
    )
    payment = 125_000.0 if dev_system == "dry" else 187_500.0
    assert engine.calculate_royalty(
        {"2025-01": 1_000_000.0, "2025-02": 0.0}
    ) == {"2025-01": payment, "2025-02": 0.0}


def test_missing_assumption_uses_source_note_rate():
    """BOEM note in us_gom.yml: synthetic USD 1,000,000 * 18.75/100 = 187,500."""
    assumptions = AssumptionsManager.from_dict({"DEV_SYSTEM": ["subsea15"]})
    engine = CashflowEngine(assumptions)
    assert engine.calculate_royalty({"2025-01": 1_000_000.0}) == {"2025-01": 187_500.0}


@pytest.mark.parametrize("use_deck", [False, True])
def test_explicit_and_custom_rates_remain_authoritative(use_deck):
    """Synthetic inputs: 1,000,000 * 0.2 = 200,000; an explicit zero gives zero.

    Rates here are caller inputs, not jurisdictional defaults or source claims.
    The deck's BOEM source note gives 18.75/100, so its hand result is 187,500.
    """
    assumptions = AssumptionsManager.from_dict(
        {"DEV_SYSTEM": ["subsea15"], "ROYALTY_RATE": [0.2]}
    )
    engine = CashflowEngine(
        assumptions, fiscal_terms=get_fiscal_terms("us_gom") if use_deck else None
    )
    revenue = {"2025-01": 1_000_000.0}
    expected = 187_500.0 if use_deck else 200_000.0
    assert engine.calculate_royalty(revenue) == {"2025-01": expected}
    assert engine.calculate_royalty(revenue, royalty_rate=0.0) == {"2025-01": 0.0}
