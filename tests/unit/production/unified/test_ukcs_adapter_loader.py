"""UKCS NSTA adapter fixture-backed contract tests (#717)."""

import pandas as pd
import pytest

from worldenergydata.fdas.adapters.contract import to_fdas_production
from worldenergydata.production.unified.adapters.ukcs_adapter import UkcsAdapter
from worldenergydata.production.unified.query import STANDARD_COLUMNS, ProductionQuery
from worldenergydata.ukcs.production.field_production import UKCSFieldProductionLoader


class FixtureNstaLoader:
    """Duck-typed NSTA loader returning normalized UKCS production rows."""

    def __init__(self):
        self.calls = []

    def load_field_production(self, field_name):
        self.calls.append(("field", field_name))
        normalized = _normalized_nsta_frame()
        return normalized[normalized["field"] == field_name.upper().strip()].copy()

    def load_all_production(self):
        self.calls.append(("all", None))
        return _normalized_nsta_frame()


def _normalized_nsta_frame():
    raw = pd.DataFrame(
        [
            {
                "FIELDNAME": "FORTIES",
                "PERIODYR": 1975,
                "PERIODMNTH": 9,
                "OILPRODMAS": 1000.0,
                "AGASPROKSM": 25.0,
                "DGASPROKSM": 5.0,
                "WATPRODVOL": 100.0,
            },
            {
                "FIELDNAME": "FORTIES",
                "PERIODYR": 1975,
                "PERIODMNTH": 10,
                "OILPRODMAS": 1100.0,
                "AGASPROKSM": 28.0,
                "DGASPROKSM": 6.0,
                "WATPRODVOL": 120.0,
            },
            {
                "FIELDNAME": "BUZZARD",
                "PERIODYR": 2007,
                "PERIODMNTH": 1,
                "OILPRODMAS": 900.0,
                "AGASPROKSM": 18.0,
                "DGASPROKSM": 4.0,
                "WATPRODVOL": 80.0,
            },
        ]
    )
    return UKCSFieldProductionLoader().load(raw)


def test_fetch_transforms_nsta_loader_output_to_standard_columns():
    loader = FixtureNstaLoader()
    adapter = UkcsAdapter(loader=loader)

    out = adapter.fetch(
        ProductionQuery(
            regions=["ukcs"],
            fields=["Forties"],
            start="1975-10",
            end="1975-10",
        )
    )

    assert loader.calls == [("field", "Forties")]
    assert list(out.columns) == list(STANDARD_COLUMNS)
    assert len(out) == 1
    row = out.iloc[0]
    expected = _normalized_nsta_frame().iloc[1]
    assert row["region"] == "ukcs"
    assert row["field_name"] == "Forties"
    assert row["year"] == 1975
    assert row["month"] == 10
    assert row["oil_bbl"] == pytest.approx(expected["oil_bbl"])
    assert row["gas_mcf"] == pytest.approx(expected["gas_mcf"])
    assert row["water_bbl"] == pytest.approx(expected["water_bbl"])
    assert pd.isna(row["condensate_bbl"])
    assert row["source"] == "nsta"
    assert "field" not in out.columns


def test_fetch_output_is_accepted_by_fdas_production_contract():
    adapter = UkcsAdapter(loader=FixtureNstaLoader())

    unified = adapter.fetch(ProductionQuery(regions=["ukcs"], fields=["Forties"]))
    fdas = to_fdas_production(unified)

    assert list(fdas["DEV_NAME"].unique()) == ["Forties"]
    assert list(fdas["YEAR_MONTH"]) == ["1975-09", "1975-10"]
    assert fdas["MONTHLY_WATER_BBL"].notna().all()


def test_fetch_all_uses_loader_all_path_when_no_field_filter():
    loader = FixtureNstaLoader()
    adapter = UkcsAdapter(loader=loader)

    out = adapter.fetch(ProductionQuery(regions=["ukcs"]))

    assert loader.calls == [("all", None)]
    assert set(out["field_name"]) == {"Forties", "Buzzard"}
    assert set(out["source"]) == {"nsta"}
    assert out["condensate_bbl"].isna().all()


def test_default_synthetic_surface_still_lists_benchmark_fields():
    adapter = UkcsAdapter()

    assert adapter.available_fields() == [
        "Forties",
        "Buzzard",
        "Mariner",
        "Clair Ridge",
    ]
    out = adapter.fetch(ProductionQuery(regions=["ukcs"], fields=["Forties"]))

    assert len(out) > 0
    assert set(out["source"]) == {"ukcs_mock"}


@pytest.mark.parametrize("condensate", [62.898, 0.0, None])
def test_loader_condensate_reaches_standard_columns_and_fdas(condensate):
    """Hand calculation: synthetic 10 m3 * 6.2898 = 62.898 bbl.

    NIST SP 811 Appendix B.8 petroleum-barrel entry supports the shared
    rounded volume factor. Explicit zero and unknown remain distinct.
    FDAS has no condensate column; oil remains unmodified by condensate.
    """

    class ComponentLoader:
        def load_all_production(self):
            return pd.DataFrame(
                {
                    "field": ["EXAMPLE"],
                    "year": [2024],
                    "month": [1],
                    "oil_bbl": [0.0],
                    "gas_mcf": [float("nan")],
                    "water_bbl": [float("nan")],
                    "condensate_bbl": [condensate],
                    "ngl_bbl": [float("nan")],
                }
            )

    out = UkcsAdapter(loader=ComponentLoader()).fetch(ProductionQuery(regions=["ukcs"]))
    assert list(out) == list(STANDARD_COLUMNS)
    if condensate is None:
        assert pd.isna(out.loc[0, "condensate_bbl"])
    else:
        assert out.loc[0, "condensate_bbl"] == condensate
    fdas = to_fdas_production(out)
    assert fdas.loc[0, "MONTHLY_OIL_BBL"] == 0
    assert pd.isna(fdas.loc[0, "MONTHLY_GAS_MCF"])
    assert pd.isna(fdas.loc[0, "MONTHLY_WATER_BBL"])


def test_raw_condensate_survives_loader_to_fdas_bridge():
    """Hand calculation: 10 m3 * 6.2898 = 62.898 bbl (NIST SP 811 B.8).

    Only the source volume supports condensate; absent oil/gas/water stay
    unknown in both unified and FDAS frames. A non-default index is retained
    correctly through normalization.
    """

    class RawLoader:
        def load_all_production(self):
            raw = pd.DataFrame(
                {
                    "FIELDNAME": ["EXAMPLE"],
                    "PERIODYR": [2024],
                    "PERIODMNTH": [1],
                    "GCONDVOL": [10],
                },
                index=[7],
            )
            return UKCSFieldProductionLoader().load(raw)

    out = UkcsAdapter(loader=RawLoader()).fetch(ProductionQuery(regions=["ukcs"]))
    assert out.loc[0, "condensate_bbl"] == pytest.approx(62.898)
    assert list(out) == list(STANDARD_COLUMNS)
    fdas = to_fdas_production(out)
    assert (
        fdas[["MONTHLY_OIL_BBL", "MONTHLY_GAS_MCF", "MONTHLY_WATER_BBL"]]
        .isna()
        .all()
        .all()
    )
