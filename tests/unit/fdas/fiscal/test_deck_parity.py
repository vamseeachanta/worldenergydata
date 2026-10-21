"""Suite 5 — Gulf deck correction and component regressions (#1233).

Original us_gom.yml revision 1 source_ref states 12.5% and 18.75%; hence the
deck fractions are 0.125 and 0.1875. core/config.py DEFAULT_ASSUMPTIONS retains
0.188 for historical deep-water runs. Only royalty and net cashflow change;
all other component vectors must remain identical.
"""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from worldenergydata.fdas.analysis.cashflow import CashflowEngine
from worldenergydata.fdas.core.config import AssumptionsManager
from worldenergydata.fdas.core.financial import calculate_npv
from worldenergydata.fdas.fiscal import DEV_SYSTEMS, get_fiscal_terms

_COMPONENT_FIELDS = (
    "oil_production_bbl",
    "oil_revenue_usd",
    "royalty_usd",
    "variable_opex_usd",
    "fixed_opex_usd",
    "drilling_capex_usd",
    "facilities_capex_usd",
    "host_capex_usd",
    "net_cashflow_usd",
)


def _fixture():
    prod = pd.DataFrame(
        {
            "YEAR_MONTH": ["2025-01", "2025-02", "2025-03", "2025-04"],
            "MONTHLY_OIL_BBL": [120000.0, 110000.0, 95000.0, 80000.0],
        }
    )
    wti = {"2025-01": 75.0, "2025-02": 78.5, "2025-03": 72.0, "2025-04": 80.0}
    timeline = {"drilling_monthly": {"2024-10": 30.0, "2024-11": 28.0}}
    first_oil = datetime(2025, 1, 1)
    return prod, timeline, wti, first_oil


def test_deckless_vs_us_gom_only_royalty_and_net_change():
    """Hand calculation: royalty = gross * source percentage / 100.

    Net cashflow increases by the royalty saving, with other costs unchanged.
    Source percentages and legacy fraction are cited in the module docstring.
    """
    us_gom = get_fiscal_terms("us_gom")
    prod, timeline, wti, first_oil = _fixture()

    for ds in DEV_SYSTEMS:
        legacy = CashflowEngine(AssumptionsManager(), dev_system=ds)
        decked = CashflowEngine(
            AssumptionsManager(), dev_system=ds, fiscal_terms=us_gom
        )

        cf_legacy = legacy.generate_monthly_cashflow(
            prod.copy(), timeline, wti, first_oil
        )
        cf_decked = decked.generate_monthly_cashflow(
            prod.copy(), timeline, wti, first_oil
        )

        assert len(cf_legacy) == len(cf_decked) > 0, ds
        for a, b in zip(cf_legacy, cf_decked):
            assert a.year_month == b.year_month, ds
            for field in _COMPONENT_FIELDS:
                if field not in {"royalty_usd", "net_cashflow_usd"}:
                    assert getattr(a, field) == getattr(b, field), (
                        ds,
                        field,
                        a.year_month,
                    )
            rate = 0.125 if ds == "dry" else 0.1875
            assert b.royalty_usd == a.oil_revenue_usd * rate
            assert b.net_cashflow_usd == pytest.approx(
                a.net_cashflow_usd + a.royalty_usd - b.royalty_usd
            )


@pytest.mark.parametrize("discount_rate", [0.0, 0.10])
def test_deckless_vs_us_gom_npv_saving(discount_rate):
    """Independent hand calculation using the synthetic fixture:

    Gross revenue = 120000*75 + 110000*78.5 + 95000*72 + 80000*80
    = 30875000 USD. At zero discount NPV is the sum of cashflows, so the
    deep-water saving is 30875000 * (0.188 - 18.75/100) = 15437.5 USD.
    Dry-tree rates agree, giving zero saving. Rate sources: module docstring.

    Nonzero-discount case: OpenStax, Principles of Finance (2022), section
    16.2, discounts each cashflow to its present value. The synthetic annual
    rate is 0.10. Monthly savings are 4500, 4317.5, 3420, 3200 USD, obtained
    by multiplying each fixture revenue by (0.188 - 0.1875). Timing is defined
    by core/financial.py::calculate_npv: the first row is at time zero and
    monthly discounting uses (1 + annual_rate)**(t/12). The contract in
    analysis/cashflow.py::CashflowEngine.calculate_host_capex_timing spans
    24 months including first oil, leaving 23 pre-production rows. These are
    repository timing conventions, not textbook assumptions. Delta NPV is
    sum(saving_t / (1 + annual_rate)**(t/12)) for t = 23, 24, 25, 26.
    This also retains the original nonzero-discount regression input.
    """
    us_gom = get_fiscal_terms("us_gom")
    prod, timeline, wti, first_oil = _fixture()

    for ds in DEV_SYSTEMS:
        legacy = CashflowEngine(AssumptionsManager(), dev_system=ds)
        decked = CashflowEngine(
            AssumptionsManager(), dev_system=ds, fiscal_terms=us_gom
        )
        v_legacy = [
            c.net_cashflow_usd
            for c in legacy.generate_monthly_cashflow(
                prod.copy(), timeline, wti, first_oil
            )
        ]
        v_decked = [
            c.net_cashflow_usd
            for c in decked.generate_monthly_cashflow(
                prod.copy(), timeline, wti, first_oil
            )
        ]
        # Hand-calculated payments; code-defined timing contracts cited above.
        saving = (
            0.0
            if ds == "dry"
            else sum(
                amount / (1 + discount_rate) ** (month / 12)
                for month, amount in zip(range(23, 27), (4500, 4317.5, 3420, 3200))
            )
        )
        assert calculate_npv(np.array(v_decked), discount_rate) - calculate_npv(
            np.array(v_legacy), discount_rate
        ) == pytest.approx(saving), ds


@pytest.mark.parametrize("dev_system", (*DEV_SYSTEMS, "unmapped"))
def test_calculate_royalty_source_note_hand_calculation(dev_system):
    """Hand calculation on synthetic gross revenue of 1000000 USD:

    Original us_gom.yml revision 1 source_ref gives 12.5% shallow-water and
    18.75% deep-water. Payments = 1000000 * percentage / 100, hence
    125000 USD dry and 187500 USD deep-water (including the default fallback).
    """
    us_gom = get_fiscal_terms("us_gom")
    revenue = {"2025-01": 1_000_000.0}
    decked = CashflowEngine(
        AssumptionsManager(), dev_system=dev_system, fiscal_terms=us_gom
    )
    expected = 125000.0 if dev_system == "dry" else 187500.0
    assert decked.calculate_royalty(revenue) == {"2025-01": expected}


def test_explicit_rate_arg_overrides_deck():
    """An explicit royalty_rate arg wins over both deck and assumptions."""
    us_gom = get_fiscal_terms("us_gom")
    revenue = {"2025-01": 1_000_000.0}
    decked = CashflowEngine(
        AssumptionsManager(), dev_system="subsea15", fiscal_terms=us_gom
    )
    out = decked.calculate_royalty(revenue, royalty_rate=0.0)
    assert out["2025-01"] == 0.0


def test_runtime_reference_scale_parity():
    """Parity with existing Brazil code only; not a claim that bands are correct law."""
    import math

    from worldenergydata.brazil_anp.analysis.field_economics import (
        ROYALTY_SCALE,
        calculate_royalties_concession,
    )
    from worldenergydata.fdas.fiscal import validate_deck

    terms = validate_deck(
        {
            "schema_version": 1,
            "country": "synthetic-reference",
            "source_url": "https://example.org/synthetic",
            "source_ref": "Runtime reference parity only",
            "revision": "1",
            "effective_date": "2026-01-01",
            "royalty": {
                "model": "sliding_scale",
                "bands": [
                    {"max_rate_bpd": None if math.isinf(limit) else limit, "rate": rate}
                    for limit, rate in ROYALTY_SCALE
                ],
            },
        }
    )
    eng = CashflowEngine(AssumptionsManager(), fiscal_terms=terms)
    rates = [0]
    for limit, _ in ROYALTY_SCALE:
        if math.isfinite(limit):
            rates.extend([limit, limit + 1])
    for revenue in (0, 1_000_000):
        for rate in rates:
            result = eng.calculate_royalty(
                {"2025-01": revenue}, production_rate_bpd_monthly={"2025-01": rate}
            )
            assert result["2025-01"] == calculate_royalties_concession(revenue, rate)
