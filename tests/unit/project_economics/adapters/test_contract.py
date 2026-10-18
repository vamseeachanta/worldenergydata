"""Suite A — project_economics production-contract normalizer (#715).

`to_project_economics_production` maps the unified STANDARD_COLUMNS frame → the project_economics monthly
schema the cashflow engine reads. Fail-closed on missing columns; typed-empty on
empty input; canonical `MONTHLY_OIL_BBL` (not `_VOLUME`).
"""

import pandas as pd
import pytest

from worldenergydata.project_economics.adapters.contract import (
    PROJECT_ECONOMICS_PRODUCTION_COLUMNS,
    ProjectEconomicsContractError,
    to_project_economics_production,
)


def _unified(rows=None):
    rows = rows or [
        # region, field_name, year, month, oil_bbl, gas_mcf, water_bbl, condensate_bbl, source
        ("ncs", "Troll", 2025, 1, 100000.0, 50000.0, 2000.0, 10.0, "sodir"),
        ("ncs", "Troll", 2025, 2, 95000.0, 48000.0, 2100.0, 9.0, "sodir"),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "region",
            "field_name",
            "year",
            "month",
            "oil_bbl",
            "gas_mcf",
            "water_bbl",
            "condensate_bbl",
            "source",
        ],
    )


def test_maps_to_exact_project_economics_columns():
    out = to_project_economics_production(_unified())
    assert list(out.columns) == list(PROJECT_ECONOMICS_PRODUCTION_COLUMNS)
    assert len(out) == 2


def test_year_month_is_zero_padded_string():
    out = to_project_economics_production(_unified([("ncs", "F", 2025, 3, 1.0, 2.0, 3.0, 0.0, "s")]))
    assert out["YEAR_MONTH"].iloc[0] == "2025-03"
    # parseable as a period
    assert pd.Period(out["YEAR_MONTH"].iloc[0], freq="M").month == 3


def test_canonical_bbl_naming_not_volume():
    out = to_project_economics_production(_unified())
    assert "MONTHLY_OIL_BBL" in out.columns
    assert "MONTHLY_OIL_VOLUME" not in out.columns
    assert out["MONTHLY_OIL_BBL"].iloc[0] == 100000.0
    assert out["MONTHLY_GAS_MCF"].iloc[0] == 50000.0
    assert out["MONTHLY_WATER_BBL"].iloc[0] == 2000.0


def test_dev_name_from_field_name_default():
    out = to_project_economics_production(_unified())
    assert out["DEV_NAME"].iloc[0] == "Troll"


def test_dev_name_col_override():
    df = _unified()
    df["dev_group"] = "Grieg-cluster"
    out = to_project_economics_production(df, dev_name_col="dev_group")
    assert (out["DEV_NAME"] == "Grieg-cluster").all()


def test_missing_columns_fail_closed():
    df = _unified().drop(columns=["oil_bbl"])
    with pytest.raises(ProjectEconomicsContractError, match="oil_bbl"):
        to_project_economics_production(df)


def test_missing_dev_name_col_fail_closed():
    with pytest.raises(ProjectEconomicsContractError, match="dev_group"):
        to_project_economics_production(_unified(), dev_name_col="dev_group")


def test_empty_input_returns_typed_empty():
    out = to_project_economics_production(_unified().iloc[0:0])
    assert list(out.columns) == list(PROJECT_ECONOMICS_PRODUCTION_COLUMNS)
    assert len(out) == 0
    assert out["MONTHLY_OIL_BBL"].dtype == "float64"


def test_none_input_returns_typed_empty():
    out = to_project_economics_production(None)
    assert len(out) == 0
    assert list(out.columns) == list(PROJECT_ECONOMICS_PRODUCTION_COLUMNS)


def test_bad_month_rejected():
    with pytest.raises(ProjectEconomicsContractError, match="month"):
        to_project_economics_production(_unified([("ncs", "F", 2025, 13, 1.0, 2.0, 3.0, 0.0, "s")]))


def test_non_numeric_year_rejected():
    with pytest.raises(ProjectEconomicsContractError):
        to_project_economics_production(_unified([("ncs", "F", "abcd", 1, 1.0, 2.0, 3.0, 0.0, "s")]))
