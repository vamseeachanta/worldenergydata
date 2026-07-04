"""Spain CORES adapter fixture-backed contract tests (#763b)."""

import pandas as pd
import pytest

from worldenergydata.fdas.adapters.contract import to_fdas_production
from worldenergydata.production.unified.adapters.spain_cores_adapter import (
    SpainCoresAdapter,
)
from worldenergydata.production.unified.query import STANDARD_COLUMNS, ProductionQuery
from worldenergydata.spain.production.cores_loader import GWH_TO_MCF, TONNES_TO_BBL
from worldenergydata.spain.production.cores_live import (
    DEFAULT_WORKBOOKS,
    CoresLiveProductionLoader,
)


class FixtureCoresLoader:
    """Duck-typed CORES loader returning normalized per-field monthly rows."""

    def __init__(self):
        self.calls = []

    def load_field_production(self, field_name):
        self.calls.append(("field", field_name))
        frame = _loader_frame()
        return frame[frame["field_name"] == field_name].copy()

    def load_all_production(self):
        self.calls.append(("all", None))
        return _loader_frame()


class SeparateProductCoresLoader:
    """Duck-typed CORES loader with separate oil and gas product frames."""

    def load_oil_production(self):
        return pd.DataFrame(
            [
                {
                    "field_name": "Ayoluengo",
                    "year": 2024,
                    "month": 1,
                    "oil_bbl": 73.3,
                },
                {
                    "field_name": "Ayoluengo",
                    "year": 2024,
                    "month": 2,
                    "oil_bbl": 87.96,
                },
            ]
        )

    def load_gas_production(self):
        return pd.DataFrame(
            [
                {
                    "field_name": "Ayoluengo",
                    "year": 2024,
                    "month": 1,
                    "gas_mcf": 3290.0,
                }
            ]
        )


def _loader_frame():
    return pd.DataFrame(
        [
            {
                "field_name": "Ayoluengo",
                "year": 2024,
                "month": 1,
                "oil_bbl": 73.3,
                "gas_mcf": 0.0,
            },
            {
                "field_name": "Ayoluengo",
                "year": 2024,
                "month": 2,
                "oil_bbl": 87.96,
                "gas_mcf": 0.0,
            },
            {
                "field_name": "Casablanca",
                "year": 2024,
                "month": 1,
                "oil_bbl": 10.995,
                "gas_mcf": 0.0,
            },
        ]
    )


def test_fetch_transforms_cores_loader_output_to_standard_columns():
    loader = FixtureCoresLoader()
    adapter = SpainCoresAdapter(loader=loader)

    out = adapter.fetch(
        ProductionQuery(
            regions=["spain"],
            fields=["Ayoluengo"],
            start="2024-02",
            end="2024-02",
        )
    )

    assert loader.calls == [("field", "Ayoluengo")]
    assert list(out.columns) == list(STANDARD_COLUMNS)
    assert len(out) == 1
    row = out.iloc[0]
    assert row["region"] == "spain"
    assert row["field_name"] == "Ayoluengo"
    assert row["year"] == 2024
    assert row["month"] == 2
    assert row["oil_bbl"] == pytest.approx(87.96)
    assert row["gas_mcf"] == pytest.approx(0.0)
    assert pd.isna(row["water_bbl"])
    assert pd.isna(row["condensate_bbl"])
    assert row["source"] == "cores"


def test_fetch_output_is_accepted_by_fdas_production_contract():
    adapter = SpainCoresAdapter(loader=FixtureCoresLoader())

    unified = adapter.fetch(ProductionQuery(regions=["spain"], fields=["Ayoluengo"]))
    fdas = to_fdas_production(unified)

    assert list(fdas["DEV_NAME"].unique()) == ["Ayoluengo"]
    assert list(fdas["YEAR_MONTH"]) == ["2024-01", "2024-02"]
    assert fdas["MONTHLY_WATER_BBL"].isna().all()


def test_fetch_all_uses_loader_all_path_when_no_field_filter():
    loader = FixtureCoresLoader()
    adapter = SpainCoresAdapter(loader=loader)

    out = adapter.fetch(ProductionQuery(regions=["spain"]))

    assert loader.calls == [("all", None)]
    assert set(out["field_name"]) == {"Ayoluengo", "Casablanca"}
    assert set(out["source"]) == {"cores"}
    assert out["water_bbl"].isna().all()
    assert out["condensate_bbl"].isna().all()


def test_fetch_merges_separate_oil_and_gas_loader_frames():
    adapter = SpainCoresAdapter(loader=SeparateProductCoresLoader())

    out = adapter.fetch(ProductionQuery(regions=["spain"], fields=["Ayoluengo"]))

    assert list(out[["year", "month"]].itertuples(index=False, name=None)) == [
        (2024, 1),
        (2024, 2),
    ]
    assert list(out["oil_bbl"]) == pytest.approx([73.3, 87.96])
    assert list(out["gas_mcf"]) == pytest.approx([3290.0, 0.0])
    assert set(out["source"]) == {"cores"}


def test_default_adapter_loads_committed_ayoluengo_fixture():
    adapter = SpainCoresAdapter()

    out = adapter.fetch(ProductionQuery(regions=["spain"], fields=["Ayoluengo"]))

    assert not out.empty
    assert set(out["field_name"]) == {"Ayoluengo"}
    assert set(out["source"]) == {"cores"}
    assert out["oil_bbl"].gt(0).any()


def test_adapter_accepts_live_cores_loader(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _write_cores_xlsx(
        raw_dir / DEFAULT_WORKBOOKS["oil"].filename,
        pd.DataFrame(
            [
                {
                    "Year": 2026,
                    "Month": "June",
                    "Ayoluengo": 2.0,
                    "Grand total": 2.0,
                }
            ]
        ),
    )
    _write_cores_xlsx(
        raw_dir / DEFAULT_WORKBOOKS["gas"].filename,
        pd.DataFrame(
            [
                {
                    "Year": 2026,
                    "Month": "June",
                    "Ayoluengo": 3.0,
                    "Grand total": 3.0,
                }
            ]
        ),
    )

    adapter = SpainCoresAdapter(loader=CoresLiveProductionLoader(cache_root=tmp_path))
    out = adapter.fetch(
        ProductionQuery(regions=["spain"], fields=["Ayoluengo"], start="2026-06")
    )

    assert list(out.columns) == list(STANDARD_COLUMNS)
    assert len(out) == 1
    assert out.iloc[0]["oil_bbl"] == pytest.approx(2.0 * TONNES_TO_BBL)
    assert out.iloc[0]["gas_mcf"] == pytest.approx(3.0 * GWH_TO_MCF)
    assert out.iloc[0]["source"] == "cores"


def _write_cores_xlsx(path, frame):
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"note": ["landing sheet"]}).to_excel(
            writer,
            sheet_name="Start",
            index=False,
        )
        frame.to_excel(writer, sheet_name="Production", index=False, startrow=5)
