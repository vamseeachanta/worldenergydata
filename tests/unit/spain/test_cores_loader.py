"""Spain CORES production loader tests (#763a)."""

import pandas as pd
import pytest

from worldenergydata.spain.production.cores_loader import (
    GWH_TO_MCF,
    TONNES_TO_BBL,
    CoresFixtureProductionLoader,
    CoresParseError,
    CoresProductionLoader,
    parse_cores_frame,
)


def test_parse_oil_frame_drops_total_rows_and_converts_tonnes_to_bbl():
    raw = pd.DataFrame(
        [
            {
                "Year": 2024,
                "Month": "January",
                "Ayoluengo": 10.0,
                "Casablanca": 1.5,
                "Grand total": 11.5,
            },
            {
                "Year": 2024,
                "Month": "February",
                "Ayoluengo": 12.0,
                "Casablanca": None,
                "Grand total": 12.0,
            },
            {
                "Year": 2024,
                "Month": "Total",
                "Ayoluengo": 22.0,
                "Casablanca": 1.5,
                "Grand total": 23.5,
            },
            {
                "Year": None,
                "Month": None,
                "Ayoluengo": 999.0,
                "Casablanca": 999.0,
                "Grand total": 999.0,
            },
        ]
    )

    out = parse_cores_frame(raw, product="oil")

    assert list(out.columns) == ["field_name", "year", "month", "oil_bbl"]
    assert set(out["field_name"]) == {"Ayoluengo", "Casablanca"}
    assert set(out["month"]) == {1, 2}
    ayoluengo = out[out["field_name"] == "Ayoluengo"].sort_values("month")
    assert list(ayoluengo["oil_bbl"]) == pytest.approx(
        [10.0 * TONNES_TO_BBL, 12.0 * TONNES_TO_BBL]
    )
    casablanca = out[out["field_name"] == "Casablanca"]
    assert len(casablanca) == 1
    assert casablanca.iloc[0]["oil_bbl"] == pytest.approx(1.5 * TONNES_TO_BBL)


def test_parse_gas_frame_accepts_spanish_months_and_converts_gwh_to_mcf():
    raw = pd.DataFrame(
        [
            {
                "Año": 2024,
                "Mes": "enero",
                "Gaviota": 3.0,
                "Viura": 1.25,
                "Total general": 4.25,
            },
            {
                "Año": 2024,
                "Mes": "Total",
                "Gaviota": 3.0,
                "Viura": 1.25,
                "Total general": 4.25,
            },
        ]
    )

    out = parse_cores_frame(raw, product="gas")

    assert list(out.columns) == ["field_name", "year", "month", "gas_mcf"]
    assert set(out["field_name"]) == {"Gaviota", "Viura"}
    assert set(out["month"]) == {1}
    assert out.loc[out["field_name"] == "Gaviota", "gas_mcf"].iloc[0] == (
        pytest.approx(3.0 * GWH_TO_MCF)
    )


def test_loader_reads_xlsx_with_cores_header_row(tmp_path):
    path = tmp_path / "cores_oil.xlsx"
    raw = pd.DataFrame(
        [
            {
                "Year": 2026,
                "Month": "June",
                "Ayoluengo": 2.0,
                "Grand total": 2.0,
            }
        ]
    )
    raw.to_excel(path, index=False, startrow=5)

    out = CoresProductionLoader(product="oil", path=path, header_row=5).load()

    assert out.to_dict("records") == [
        {
            "field_name": "Ayoluengo",
            "year": 2026,
            "month": 6,
            "oil_bbl": pytest.approx(2.0 * TONNES_TO_BBL),
        }
    ]


def test_fixture_loader_carries_direct_source_provenance():
    loader = CoresFixtureProductionLoader()

    metadata = loader.metadata()
    out = loader.load_field_production("Ayoluengo")

    assert metadata["source_url"].endswith("/crude-oil-production.xlsx")
    assert metadata["statistics_page"] == "https://www.cores.es/en/estadisticas"
    assert metadata["source_updated_date"] == "2026-06-12"
    assert set(out["field_name"]) == {"Ayoluengo"}
    assert out["oil_bbl"].gt(0).any()


def test_parse_rejects_unknown_product():
    with pytest.raises(CoresParseError, match="product"):
        parse_cores_frame(
            pd.DataFrame({"Year": [2024], "Month": ["January"]}), product="water"
        )
