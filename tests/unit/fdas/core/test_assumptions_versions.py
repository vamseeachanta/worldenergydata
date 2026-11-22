"""Version selection and synthetic royalty/net/NPV compatibility contracts."""

import pandas as pd
import pytest

from worldenergydata.fdas.analysis.cashflow import (
    CashflowEngine,
    MonthlyCashflowModel,
)
from worldenergydata.fdas.core.config import (
    DEFAULT_ASSUMPTIONS,
    AssumptionsManager,
    ConfigurationError,
)
from worldenergydata.fdas.fiscal import get_fiscal_terms

# Literal compatibility snapshot; monetary assumptions are USD or million USD
# as named. These are shipped illustrative assumptions, not measured inputs.
LEGACY = {
    "DEV_SYSTEM": ["dry", "subsea15", "subsea20", "default"],
    "HOST_CAPEX_MM": [0.0, 300.0, 450.0, 300.0],
    "SURF_PER_WELL_MM": [0.0, 8.0, 12.0, 8.0],
    "MODU_LOADED_DAYRATE_MM": [0.6, 0.8, 1.0, 0.8],
    "DRY_TREE_RIG_RATE_MM": [0.5, 0.5, 0.5, 0.5],
    "ROYALTY_RATE": [0.125, 0.188, 0.188, 0.188],
    "VARIABLE_OPEX_$/BBL": [8.0, 12.0, 15.0, 12.0],
    "FIXED_OPEX_MM_PER_YEAR": [10.0, 25.0, 40.0, 25.0],
    "DISCOUNT_RATE_ANNUAL": [0.10, 0.10, 0.10, 0.10],
    "WTI_BASE_$/BBL": [75.0, 75.0, 75.0, 75.0],
}
SYSTEMS = ["dry", "subsea15", "subsea20", "default", "unmapped"]
VERSIONS = [None, "legacy-v1", "source-note-v2"]


def manager_for(version):
    return (
        AssumptionsManager() if version is None else AssumptionsManager(version=version)
    )


@pytest.mark.parametrize("version", VERSIONS)
@pytest.mark.parametrize("system", SYSTEMS)
def test_complete_table_and_lookup(version, system):
    manager = manager_for(version)
    expected = pd.DataFrame(LEGACY)
    if version == "source-note-v2":
        expected["ROYALTY_RATE"] = [0.125, 0.1875, 0.1875, 0.1875]
    pd.testing.assert_frame_equal(manager.assumptions, expected)
    assert manager.assumptions_version == (version or "legacy-v1")
    assert DEFAULT_ASSUMPTIONS == LEGACY
    row = expected.iloc[SYSTEMS.index(system) if system != "unmapped" else 3]
    for parameter in expected.columns.drop("DEV_SYSTEM"):
        assert manager.get(system, parameter) == row[parameter]


@pytest.mark.parametrize("version", VERSIONS)
def test_selected_tables_are_independent(version):
    first, second = manager_for(version), manager_for(version)
    first.assumptions.loc[1, "ROYALTY_RATE"] = 0.5
    first.assumptions.loc[1, "HOST_CAPEX_MM"] = 1.0
    assert second.get("subsea15", "ROYALTY_RATE") == (
        0.1875 if version == "source-note-v2" else 0.188
    )
    assert second.get("subsea15", "HOST_CAPEX_MM") == 300.0
    assert DEFAULT_ASSUMPTIONS == LEGACY


@pytest.mark.parametrize("factory", ["dataframe", "dictionary", "excel"])
def test_custom_inputs_preserve_values_and_metadata(factory, tmp_path):
    data = {"DEV_SYSTEM": ["dry", "default"], "ROYALTY_RATE": [0.42, 0.43]}
    frame = pd.DataFrame(data)
    if factory == "dataframe":
        manager = AssumptionsManager(frame)
        frame.loc[0, "ROYALTY_RATE"] = 0.9
    elif factory == "dictionary":
        manager = AssumptionsManager.from_dict(data)
    else:
        path = tmp_path / "assumptions.xlsx"
        frame.to_excel(path, sheet_name="assumptions", index=False)
        manager = AssumptionsManager.from_excel(path)
    assert manager.assumptions_version == "custom"
    pd.testing.assert_frame_equal(manager.assumptions, pd.DataFrame(data))
    assert manager.get("dry", "ROYALTY_RATE") == 0.42
    assert manager.get("unmapped", "ROYALTY_RATE") == 0.43


@pytest.mark.parametrize("version", ["legacy-v1", "source-note-v2"])
def test_custom_table_rejects_builtin_selector(version):
    with pytest.raises(ConfigurationError, match="custom"):
        AssumptionsManager(pd.DataFrame(LEGACY), version=version)


@pytest.mark.parametrize("version", ["", "custom", "unknown-v3"])
def test_unknown_version_fails_closed(version):
    with pytest.raises(ConfigurationError, match="version"):
        AssumptionsManager(version=version)


@pytest.mark.parametrize("version", VERSIONS)
@pytest.mark.parametrize("system", SYSTEMS)
def test_deckless_royalty_net_and_npv(version, system):
    """Two synthetic months: USD 1000000 gross each, every cost set to zero.

    Historical Sale 249 percentages give 12.5/100 and 18.75/100 (guide sources).
    Expected royalty/net per month: dry 125000/875000; deep legacy
    188000/812000; deep source-note 187500/812500. Two-month zero-rate NPVs
    are 1750000, 1624000 and 1625000 USD respectively. OpenStax (2022),
    section 16.2, supplies PV summation; core.financial.calculate_npv supplies
    month-zero timing and effective monthly compounding, hence the exponent.
    """
    engine = CashflowEngine(manager_for(version), system, fiscal_terms=None)
    royalty, net, zero_npv = (
        (125_000.0, 875_000.0, 1_750_000.0)
        if system == "dry"
        else (
            (187_500.0, 812_500.0, 1_625_000.0)
            if version == "source-note-v2"
            else (188_000.0, 812_000.0, 1_624_000.0)
        )
    )
    revenue = {"2025-01": 1_000_000.0, "2025-02": 1_000_000.0}
    payments = engine.calculate_royalty(revenue)
    assert payments == {month: royalty for month in revenue}
    rows = [
        MonthlyCashflowModel(
            year_month=month,
            oil_revenue_usd=gross,
            royalty_usd=payments[month],
            variable_opex_usd=0.0,
            fixed_opex_usd=0.0,
            drilling_capex_usd=0.0,
            facilities_capex_usd=0.0,
            host_capex_usd=0.0,
        )
        for month, gross in revenue.items()
    ]
    assert [row.calculate_net_cashflow() for row in rows] == [net, net]
    assert engine.calculate_npv(rows, 0.0) == zero_npv
    assert engine.calculate_npv(rows, 0.10) == pytest.approx(
        net + net / 1.10 ** (1 / 12)
    )


@pytest.mark.parametrize("version", ["legacy-v1", "source-note-v2"])
@pytest.mark.parametrize("system", SYSTEMS)
def test_flat_deck_and_explicit_zero_keep_precedence(version, system):
    engine = CashflowEngine(manager_for(version), system, get_fiscal_terms("us_gom"))
    revenue = {"2025-01": 1_000_000.0}
    expected = 125_000.0 if system == "dry" else 187_500.0
    assert engine.calculate_royalty(revenue) == {"2025-01": expected}
    assert engine.calculate_royalty(revenue, royalty_rate=0.0) == {"2025-01": 0.0}
