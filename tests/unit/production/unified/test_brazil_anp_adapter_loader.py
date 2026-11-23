"""Brazil ANP adapter fixture-backed contract tests (#718)."""

import pandas as pd
import pytest

from worldenergydata.fdas.adapters.contract import to_fdas_production
from worldenergydata.production.unified.adapters.brazil_anp_adapter import (
    BrazilAnpAdapter,
)
from worldenergydata.production.unified.query import STANDARD_COLUMNS, ProductionQuery


class FixtureAnpLoader:
    """Duck-typed ANP field-month loader."""

    def __init__(self):
        self.calls = []

    def load_field_production(self, field_name):
        self.calls.append(("field", field_name))
        frame = _field_month_frame()
        return frame[frame["field"].str.lower() == field_name.lower()].copy()

    def load_all_production(self):
        self.calls.append(("all", None))
        return _field_month_frame()


def _field_month_frame():
    return pd.DataFrame(
        [
            {
                "field": "TUPI",
                "date": pd.Timestamp("2024-01-01"),
                "year": 2024,
                "month": 1,
                "oil_bbl": 1000.0,
                "gas_mcf": 200.0,
                "water_bbl": 30.0,
                "condensate_bbl": 10.0,
            },
            {
                "field": "TUPI",
                "date": pd.Timestamp("2024-02-01"),
                "year": 2024,
                "month": 2,
                "oil_bbl": 1100.0,
                "gas_mcf": 210.0,
                "water_bbl": 35.0,
                "condensate_bbl": 11.0,
            },
            {
                "field": "BUZIOS",
                "date": pd.Timestamp("2024-01-01"),
                "year": 2024,
                "month": 1,
                "oil_bbl": 900.0,
                "gas_mcf": 180.0,
                "water_bbl": 25.0,
                "condensate_bbl": 8.0,
            },
        ]
    )


def test_fetch_transforms_anp_loader_output_to_standard_columns():
    loader = FixtureAnpLoader()
    adapter = BrazilAnpAdapter(loader=loader)

    out = adapter.fetch(
        ProductionQuery(
            regions=["brazil"],
            fields=["TUPI"],
            start="2024-02",
            end="2024-02",
        )
    )

    assert loader.calls == [("field", "TUPI")]
    assert list(out.columns) == list(STANDARD_COLUMNS)
    assert len(out) == 1
    row = out.iloc[0]
    assert row["region"] == "brazil"
    assert row["field_name"] == "TUPI"
    assert row["year"] == 2024
    assert row["month"] == 2
    assert row["oil_bbl"] == pytest.approx(1100.0)
    assert row["gas_mcf"] == pytest.approx(210.0)
    assert row["water_bbl"] == pytest.approx(35.0)
    assert row["condensate_bbl"] == pytest.approx(11.0)
    assert row["source"] == "anp_producao_poco"
    assert "field" not in out.columns


def test_fetch_output_is_accepted_by_fdas_production_contract():
    adapter = BrazilAnpAdapter(loader=FixtureAnpLoader())

    unified = adapter.fetch(ProductionQuery(regions=["brazil"], fields=["TUPI"]))
    fdas = to_fdas_production(unified)

    assert list(fdas["DEV_NAME"].unique()) == ["TUPI"]
    assert list(fdas["YEAR_MONTH"]) == ["2024-01", "2024-02"]
    assert fdas["MONTHLY_WATER_BBL"].notna().all()


def test_fetch_all_uses_loader_all_path_when_no_field_filter():
    loader = FixtureAnpLoader()
    adapter = BrazilAnpAdapter(loader=loader)

    out = adapter.fetch(ProductionQuery(regions=["brazil"]))

    assert loader.calls == [("all", None)]
    assert set(out["field_name"]) == {"TUPI", "BUZIOS"}
    assert set(out["source"]) == {"anp_producao_poco"}


def test_default_synthetic_surface_still_lists_benchmark_fields():
    adapter = BrazilAnpAdapter()

    assert "Lula" in adapter.available_fields()
    out = adapter.fetch(ProductionQuery(regions=["brazil"], fields=["Lula"]))

    assert len(out) > 0
    assert set(out["source"]) == {"brazil_anp_mock"}
