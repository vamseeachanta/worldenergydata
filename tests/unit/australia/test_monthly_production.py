"""Invented monthly gas volumes; no Australian source observations are used.

EIA Glossary, entries Mcf and MMcf, defines thousand and million cubic feet:
https://www.eia.gov/tools/glossary/index.php?id=M
The same reference conditions are required for both supplied monthly volumes.
"""

import sys

import pytest

from worldenergydata.australia.monthly_production import total_monthly_gas_mcf


def test_two_month_gas_total_in_mcf():
    # Hand sum: (1.25 + 2.50) million ft^3 * 1000 = 3750 thousand ft^3.
    rows = [
        {"period": "2024-01", "gas_mmscf": 1.25},
        {"period": "2024-02", "gas_mmscf": 2.50},
    ]
    assert total_monthly_gas_mcf(rows) == 3750.0
    assert rows[0]["gas_mmscf"] == 1.25
    assert total_monthly_gas_mcf(iter(reversed(rows))) == 3750.0


def test_reported_zero_is_a_total():
    assert total_monthly_gas_mcf([{"period": "2024-02", "gas_mmscf": 0}]) == 0


def test_empty_input_is_not_reported_zero():
    with pytest.raises(ValueError, match="no monthly"):
        total_monthly_gas_mcf([])


@pytest.mark.parametrize("value", [None, True, "1.25", -1, float("nan"), float("inf")])
def test_invalid_or_missing_volumes_fail(value):
    with pytest.raises((TypeError, ValueError), match="gas_mmscf"):
        total_monthly_gas_mcf([{"period": "2024-01", "gas_mmscf": value}])


@pytest.mark.parametrize("period", ["0000-01", "2024-00", "2024-13", "2024-1", None])
def test_invalid_month_fails(period):
    with pytest.raises(ValueError, match="period"):
        total_monthly_gas_mcf([{"period": period, "gas_mmscf": 1}])


def test_duplicate_month_cannot_double_count_a_revision():
    row = {"period": "2024-01", "gas_mmscf": 1}
    with pytest.raises(ValueError, match="duplicate"):
        total_monthly_gas_mcf([row, row])


def test_unit_column_is_required_instead_of_assumed():
    with pytest.raises(TypeError, match="gas_mmscf"):
        total_monthly_gas_mcf([{"period": "2024-01", "gas_mcf": 1000}])


@pytest.mark.parametrize("value", [sys.float_info.max, sys.float_info.max / 1500])
def test_conversion_or_total_overflow_fails(value):
    with pytest.raises(ValueError, match="finite"):
        total_monthly_gas_mcf(
            [{"period": f"2024-{month:02}", "gas_mmscf": value} for month in (1, 2)]
        )
