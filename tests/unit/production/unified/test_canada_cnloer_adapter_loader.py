"""Canada C-NLOER adapter DI-loader + fixture contract tests (#719)."""

import pandas as pd
import pytest

from worldenergydata.fdas.adapters.contract import to_fdas_production
from worldenergydata.production.unified.adapters.canada_adapter import CanadaAdapter
from worldenergydata.production.unified.query import STANDARD_COLUMNS, ProductionQuery


class FixtureCnloerLoader:
    """Duck-typed C-NLOER loader returning normalized per-field monthly rows."""

    def __init__(self):
        self.calls = []

    def _frame(self):
        return pd.DataFrame(
            [
                {
                    "field_name": "Hibernia",
                    "year": 2024,
                    "month": 1,
                    "oil_bbl": 3_800_000.0,
                    "gas_mcf": 1_500_000.0,
                    "water_bbl": 4_200_000.0,
                    "source": "cnloer",
                },
                {
                    "field_name": "Hibernia",
                    "year": 2024,
                    "month": 2,
                    "oil_bbl": 3_550_000.0,
                    "gas_mcf": 1_420_000.0,
                    "water_bbl": 4_300_000.0,
                    "source": "cnloer",
                },
                {
                    "field_name": "Terra Nova",
                    "year": 2024,
                    "month": 1,
                    "oil_bbl": 1_200_000.0,
                    "gas_mcf": 450_000.0,
                    "water_bbl": 2_100_000.0,
                    "source": "cnloer",
                },
            ]
        )

    def load_all_production(self):
        self.calls.append(("all", None))
        return self._frame()

    def load_field_production(self, field_name):
        self.calls.append(("field", field_name))
        frame = self._frame()
        return frame[frame["field_name"] == field_name].copy()


def test_fetch_transforms_loader_output_to_standard_columns():
    loader = FixtureCnloerLoader()
    adapter = CanadaAdapter(loader=loader)

    out = adapter.fetch(
        ProductionQuery(
            regions=["canada"], fields=["Hibernia"], start="2024-02", end="2024-02"
        )
    )

    assert loader.calls == [("field", "Hibernia")]
    assert list(out.columns) == list(STANDARD_COLUMNS)
    assert len(out) == 1
    row = out.iloc[0]
    assert row["region"] == "canada"
    assert row["field_name"] == "Hibernia"
    assert row["oil_bbl"] == pytest.approx(3_550_000.0)
    assert row["source"] == "cnloer"
    # C-NLOER has no condensate stream
    assert pd.isna(row["condensate_bbl"])
    # water IS published
    assert row["water_bbl"] == pytest.approx(4_300_000.0)


def test_fetch_output_is_accepted_by_fdas_production_contract():
    adapter = CanadaAdapter(loader=FixtureCnloerLoader())

    unified = adapter.fetch(ProductionQuery(regions=["canada"], fields=["Hibernia"]))
    fdas = to_fdas_production(unified)

    assert list(fdas["DEV_NAME"].unique()) == ["Hibernia"]
    assert list(fdas["YEAR_MONTH"]) == ["2024-01", "2024-02"]
    assert fdas["MONTHLY_WATER_BBL"].notna().all()


def test_fetch_all_uses_loader_all_path_when_no_field_filter():
    loader = FixtureCnloerLoader()
    adapter = CanadaAdapter(loader=loader)

    out = adapter.fetch(ProductionQuery(regions=["canada"]))

    assert loader.calls == [("all", None)]
    assert set(out["field_name"]) == {"Hibernia", "Terra Nova"}
    assert out["condensate_bbl"].isna().all()


def test_default_adapter_loads_committed_synthetic_fixture():
    adapter = CanadaAdapter()

    out = adapter.fetch(ProductionQuery(regions=["canada"], fields=["Hibernia"]))

    assert not out.empty
    assert set(out["field_name"]) == {"Hibernia"}
    assert (out["source"] == "cnloer_fixture_synthetic").all()
    assert out["oil_bbl"].gt(0).any()


def test_default_adapter_available_fields_and_date_range_non_empty():
    adapter = CanadaAdapter()
    fields = adapter.available_fields()
    assert {"Hibernia", "Terra Nova", "White Rose"}.issubset(set(fields))
    start, end = adapter.date_range()
    assert "-" in start and "-" in end
