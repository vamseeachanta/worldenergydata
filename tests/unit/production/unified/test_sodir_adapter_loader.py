"""Norway SODIR adapter fixture-backed contract tests (#716)."""

import pandas as pd
import pytest

from worldenergydata.common.units import OilUnits
from worldenergydata.fdas.adapters.contract import to_fdas_production
from worldenergydata.production.unified.adapters.sodir_adapter import SodirAdapter
from worldenergydata.production.unified.query import STANDARD_COLUMNS, ProductionQuery


class FixtureMonthlyLoader:
    """Minimal MonthlyProductionLoader stand-in for adapter tests."""

    def __init__(self):
        self.calls = []

    def load_field_production(self, field_name):
        self.calls.append(("field", field_name))
        return _loader_frame(field_name)

    def load_all_production(self):
        self.calls.append(("all", None))
        return _loader_frame("JOHAN SVERDRUP")


def _loader_frame(field_name):
    return pd.DataFrame(
        [
            {
                "field_name": field_name,
                "year": 2024,
                "month": 1,
                "oil_sm3": 1000.0,
                "gas_sm3": 2_000_000.0,
                "ngl_sm3": 0.0,
                "condensate_sm3": 10.0,
                "water_injected_sm3": 999_999.0,
                "oil_bbl": 1000.0 * OilUnits.SM3_TO_BBL,
                "gas_mcf": 70_629.4,
            },
            {
                "field_name": field_name,
                "year": 2024,
                "month": 2,
                "oil_sm3": 1100.0,
                "gas_sm3": 2_100_000.0,
                "ngl_sm3": 0.0,
                "condensate_sm3": 20.0,
                "water_injected_sm3": 888_888.0,
                "oil_bbl": 1100.0 * OilUnits.SM3_TO_BBL,
                "gas_mcf": 74_160.87,
            },
        ]
    )


def test_fetch_transforms_loader_output_to_standard_columns():
    loader = FixtureMonthlyLoader()
    adapter = SodirAdapter(loader=loader)

    out = adapter.fetch(
        ProductionQuery(
            regions=["ncs"],
            fields=["JOHAN SVERDRUP"],
            start="2024-02",
            end="2024-02",
        )
    )

    assert loader.calls == [("field", "JOHAN SVERDRUP")]
    assert list(out.columns) == list(STANDARD_COLUMNS)
    assert len(out) == 1
    row = out.iloc[0]
    assert row["region"] == "ncs"
    assert row["field_name"] == "JOHAN SVERDRUP"
    assert row["year"] == 2024
    assert row["month"] == 2
    assert row["oil_bbl"] == pytest.approx(1100.0 * OilUnits.SM3_TO_BBL)
    assert row["gas_mcf"] == pytest.approx(74_160.87)
    assert row["condensate_bbl"] == pytest.approx(20.0 * OilUnits.SM3_TO_BBL)
    assert pd.isna(row["water_bbl"])
    assert row["source"] == "sodir"
    assert "water_injected_sm3" not in out.columns


def test_fetch_output_is_accepted_by_fdas_production_contract():
    adapter = SodirAdapter(loader=FixtureMonthlyLoader())

    unified = adapter.fetch(ProductionQuery(regions=["ncs"], fields=["JOHAN SVERDRUP"]))
    fdas = to_fdas_production(unified)

    assert list(fdas["DEV_NAME"].unique()) == ["JOHAN SVERDRUP"]
    assert list(fdas["YEAR_MONTH"]) == ["2024-01", "2024-02"]
    assert fdas["MONTHLY_WATER_BBL"].isna().all()


def test_fetch_all_uses_loader_all_path_when_no_field_filter():
    loader = FixtureMonthlyLoader()
    adapter = SodirAdapter(loader=loader)

    out = adapter.fetch(ProductionQuery(regions=["ncs"]))

    assert loader.calls == [("all", None)]
    assert len(out) == 2
    assert set(out["source"]) == {"sodir"}
