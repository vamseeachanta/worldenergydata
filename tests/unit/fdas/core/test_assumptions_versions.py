"""Versioned royalty regressions with independent synthetic hand calculations.

Rate provenance: fiscal/decks/us_gom.yml, revision 1, source_ref (2026):
dry 12.5%, deep water 18.75%. NIST SP 811 (2008), section 7.10.2 defines
percent as 0.01. Legacy fractions are a compatibility pin to core/config.py
at revision f82ff2f, not a legal source. All other inputs below are synthetic.
"""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from worldenergydata.fdas.analysis.cashflow import CashflowEngine
from worldenergydata.fdas.core.config import (
    DEFAULT_ASSUMPTIONS,
    DEFAULT_ASSUMPTIONS_VERSION,
    LEGACY_ASSUMPTIONS,
    AssumptionsManager,
    ConfigurationError,
)
from worldenergydata.fdas.core.financial import calculate_npv
from worldenergydata.fdas.fiscal import get_fiscal_terms


@pytest.mark.parametrize(
    "system", ["dry", "subsea15", "subsea20", "default", "unmapped"]
)
@pytest.mark.parametrize("version", [None, "source-note-v2", "legacy-v1"])
def test_versioned_rates_and_cashflows(system, version):
    """Hand calculation for two identical synthetic months, each 1000 bbl at $100.

    Gross = $100000/month; variable OPEX = 1000*$10 = $10000/month.
    Dry royalty = 100000*12.5/100 = $12500; net = $77500.
    Corrected deep royalty = 100000*18.75/100 = $18750; net = $71250.
    Legacy deep royalty = 100000*0.188 = $18800; net = $71200.
    Capital inputs are zero; the engine currently emits zero fixed OPEX.
    At zero discount NPV = 2*net. At a synthetic annual 12% discount,
    NPV = net + net/1.12**(1/12), using first-row t=0 and monthly timing
    from core.financial.calculate_npv. Discounting equation: OpenStax,
    Principles of Finance (2022), section 16.2; monthly timing is FDAS policy.
    """
    manager = AssumptionsManager(version=version)
    assert manager.version == (version or DEFAULT_ASSUMPTIONS_VERSION)
    shallow = system == "dry"
    legacy = version == "legacy-v1"
    rate = 0.125 if shallow else (0.188 if legacy else 0.1875)
    royalty = 12500 if shallow else (18800 if legacy else 18750)
    net = 77500 if shallow else (71200 if legacy else 71250)
    assert manager.get(system, "ROYALTY_RATE") == rate

    # Override only synthetic costs; retain the selected version's royalty.
    manager.assumptions["HOST_CAPEX_MM"] = 0.0
    manager.assumptions["VARIABLE_OPEX_$/BBL"] = 10.0
    engine = CashflowEngine(manager, dev_system=system)
    production = pd.DataFrame(
        {"YEAR_MONTH": ["2025-01", "2025-02"], "MONTHLY_OIL_BBL": [1000, 1000]}
    )
    cashflows = engine.generate_monthly_cashflow(
        production, {}, {"2025-01": 100.0, "2025-02": 100.0}, datetime(2025, 1, 1)
    )
    assert [row.royalty_usd for row in cashflows] == [royalty, royalty]
    assert [row.net_cashflow_usd for row in cashflows] == [net, net]
    values = np.array([row.net_cashflow_usd for row in cashflows])
    assert calculate_npv(values, 0.0) == 2 * net
    assert calculate_npv(values, 0.12) == pytest.approx(net + net / 1.12 ** (1 / 12))


def test_default_identity_and_cost_compatibility():
    """Only royalties differ from the full table shipped at revision f82ff2f."""
    assert DEFAULT_ASSUMPTIONS_VERSION == "source-note-v2"
    for key, values in LEGACY_ASSUMPTIONS.items():
        if key != "ROYALTY_RATE":
            assert DEFAULT_ASSUMPTIONS[key] == values
            assert DEFAULT_ASSUMPTIONS[key] is not values
    assert LEGACY_ASSUMPTIONS["ROYALTY_RATE"] == [0.125, 0.188, 0.188, 0.188]
    first = AssumptionsManager(version="legacy-v1")
    first.assumptions.loc[0, "ROYALTY_RATE"] = 0.0
    assert AssumptionsManager(version="legacy-v1").get("dry", "ROYALTY_RATE") == 0.125


def test_corrected_deck_has_distinct_provenance():
    """Revision 2 corrects revision-1 source percentages, not legal effective dates."""
    terms = get_fiscal_terms("us_gom")
    assert terms.revision == "2"
    assert "12.5%" in terms.source_ref
    assert "18.75%" in terms.source_ref
    assert "legacy-v1" in terms.notes
    assert "NOT_EVALUATED" in terms.notes


@pytest.mark.parametrize("version", ["", "latest", "legacy", "SOURCE-NOTE-V2"])
def test_unknown_version_fails_closed(version):
    with pytest.raises(ConfigurationError, match="Unknown assumptions version"):
        AssumptionsManager(version=version)


def test_custom_inputs_are_not_relabelled_as_a_shipped_version():
    """Synthetic custom fraction 0.2 remains authoritative for custom tables."""
    data = {"DEV_SYSTEM": ["default"], "ROYALTY_RATE": [0.2]}
    manager = AssumptionsManager.from_dict(data)
    assert manager.version == "custom"
    assert manager.get("unmapped", "ROYALTY_RATE") == 0.2
    with pytest.raises(ConfigurationError, match="Cannot combine"):
        AssumptionsManager(pd.DataFrame(data), version="legacy-v1")


@pytest.mark.parametrize(
    "system", ["dry", "subsea15", "subsea20", "default", "unmapped"]
)
def test_deck_overrides_explicit_legacy_and_argument_overrides_deck(system):
    """At synthetic $100000 gross, a synthetic 0.2 override pays $20000."""
    engine = CashflowEngine(
        AssumptionsManager(version="legacy-v1"),
        dev_system=system,
        fiscal_terms=get_fiscal_terms("us_gom"),
    )
    revenue = {"2025-01": 100000}
    assert engine.calculate_royalty(revenue) == {
        "2025-01": 12500 if system == "dry" else 18750
    }
    assert engine.calculate_royalty(revenue, royalty_rate=0.2) == {"2025-01": 20000}
