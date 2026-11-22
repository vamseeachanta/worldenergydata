"""Spain CORES production loader tests (#763a)."""

import pandas as pd
import pytest

from worldenergydata.spain.production.cores_density import (
    CoresCrudeDensityFactor,
    CoresOilConversionAudit,
    build_oil_conversion_audit,
)
from worldenergydata.spain.production.cores_loader import (
    GWH_TO_MCF,
    TONNES_TO_BBL,
    CoresFixtureProductionLoader,
    CoresParseError,
    CoresProductionLoader,
    extract_cores_field_names,
    parse_cores_frame,
)


def _density_factor(field_name="Ayoluengo", aliases=("ayoluengo",), factor=6.95):
    return CoresCrudeDensityFactor(
        field_name=field_name,
        aliases=aliases,
        api_gravity_deg=None,
        api_gravity_min_deg=None,
        api_gravity_max_deg=None,
        bbl_per_tonne=factor,
        measurement_basis="representative produced stream",
        source_title="Example operator assay",
        source_url="https://example.test/spain-crude-assay",
        source_class="operator_record",
        evidence_note="Accepted field-specific conversion factor.",
        confidence="high",
        accepted_for_conversion=True,
    )


def _single_field_audit(factor=None):
    factor = factor or _density_factor()
    return CoresOilConversionAudit(
        used_factors=(factor,),
        defaulted_fields=(),
        missing_fields=(),
        _accepted_entries=(("Ayoluengo", factor),),
        _defaulted_field_keys=(),
    )


def _audit_for_fields(*field_names):
    factors = {}
    for field_name in field_names:
        factors[field_name] = _density_factor(
            field_name=field_name,
            aliases=(field_name,),
            factor=TONNES_TO_BBL,
        )
    return build_oil_conversion_audit(field_names, factors)


@pytest.mark.parametrize("total_column", ["Total", "TOTAL", " total ", "ToTaL"])
@pytest.mark.parametrize("product", ["oil", "gas"])
def test_plain_total_column_is_excluded_from_production(total_column, product):
    """Issue 1293, SF2 in the Spain agent pack (2026), defines Total as summary.

    Synthetic input: Field A = 3 and Field B = 5, hence Total = 3 + 5 = 8.
    The independent expected field list is [Field A, Field B]; the summary
    contributes no field. Oil uses an explicit synthetic factor, 7 bbl/tonne,
    so the hand-calculated outputs are 3 * 7 = 21 and 5 * 7 = 35 bbl.
    These inputs test column selection, not physical density qualification.
    """
    raw = pd.DataFrame(
        [
            {
                "Year": 2024,
                "Month": "January",
                "Field A": 3,
                "Field B": 5,
                total_column: 8,
            }
        ]
    )
    factors = {
        name: _density_factor(field_name=name, aliases=(name,), factor=7.0)
        for name in ("Field A", "Field B")
    }
    audit = build_oil_conversion_audit(list(factors), factors)

    out = parse_cores_frame(raw, product=product, oil_conversion_audit=audit)

    assert out["field_name"].tolist() == ["Field A", "Field B"]
    assert extract_cores_field_names(raw) == ["Field A", "Field B"]
    if product == "oil":
        assert out["oil_bbl"].tolist() == [21.0, 35.0]


@pytest.mark.parametrize("operation", [extract_cores_field_names, parse_cores_frame])
def test_only_total_columns_cannot_supply_a_field(operation):
    """Issue 1293 SF2: a summary-only table has no field; 3 + 5 = 8 is synthetic."""
    raw = pd.DataFrame(
        [
            {
                "Year": 2024,
                "Month": "January",
                "Total": 8,
                "Grand total": 8,
                "Total general": 8,
            }
        ]
    )
    kwargs = {"product": "gas"} if operation is parse_cores_frame else {}

    with pytest.raises(CoresParseError, match="no field columns found"):
        operation(raw, **kwargs)


def test_total_word_within_field_name_is_preserved():
    """Issue 1293 SF2 excludes whole summary headers; a longer name is a field.

    The synthetic zero input is a true zero, not a missing observation.
    The hand calculation is 0 times any existing conversion factor = 0.
    """
    raw = pd.DataFrame(
        [{"Year": 2024, "Month": "January", "Total Basin": 0, "Total": 0}]
    )

    out = parse_cores_frame(raw, product="gas")

    assert out["field_name"].tolist() == ["Total Basin"]
    assert out["gas_mcf"].tolist() == [0.0]
    assert extract_cores_field_names(raw) == ["Total Basin"]


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

    out = parse_cores_frame(
        raw,
        product="oil",
        oil_conversion_audit=_audit_for_fields("Ayoluengo", "Casablanca"),
    )

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


def test_parse_oil_frame_requires_conversion_audit():
    raw = pd.DataFrame(
        [
            {
                "Year": 2024,
                "Month": "January",
                "Ayoluengo": 10.0,
                "Grand total": 10.0,
            }
        ]
    )

    with pytest.raises(CoresParseError, match="oil_conversion_audit"):
        parse_cores_frame(raw, product="oil")


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


def test_parse_oil_frame_uses_conversion_audit_factor():
    raw = pd.DataFrame(
        [
            {
                "Year": 2024,
                "Month": "January",
                "Ayoluengo": 10.0,
                "Grand total": 10.0,
            }
        ]
    )

    out = parse_cores_frame(
        raw,
        product="oil",
        oil_conversion_audit=_single_field_audit(),
    )

    assert out.to_dict("records") == [
        {
            "field_name": "Ayoluengo",
            "year": 2024,
            "month": 1,
            "oil_bbl": pytest.approx(10.0 * 6.95),
        }
    ]


def test_parse_oil_frame_requires_explicit_default_opt_in():
    raw = pd.DataFrame(
        [
            {
                "Year": 2024,
                "Month": "January",
                "Ayoluengo": 10.0,
                "Casablanca": 2.0,
                "Grand total": 12.0,
            }
        ]
    )

    with pytest.raises(CoresParseError, match="Casablanca"):
        parse_cores_frame(
            raw,
            product="oil",
            oil_conversion_audit=_single_field_audit(),
        )


def test_parse_oil_frame_allows_legacy_default_when_explicit():
    raw = pd.DataFrame(
        [
            {
                "Year": 2024,
                "Month": "January",
                "Ayoluengo": 10.0,
                "Casablanca": 2.0,
                "Grand total": 12.0,
            }
        ]
    )
    audit = build_oil_conversion_audit(
        ["Ayoluengo", "Casablanca"],
        {"ayoluengo": _density_factor()},
        allow_default_density=True,
    )

    out = parse_cores_frame(raw, product="oil", oil_conversion_audit=audit)

    values = {row["field_name"]: row["oil_bbl"] for row in out.to_dict("records")}
    assert values["Ayoluengo"] == pytest.approx(10.0 * 6.95)
    assert values["Casablanca"] == pytest.approx(2.0 * TONNES_TO_BBL)


def test_parse_gas_frame_ignores_oil_conversion_audit():
    raw = pd.DataFrame(
        [
            {
                "Year": 2024,
                "Month": "January",
                "Gaviota": 3.0,
                "Grand total": 3.0,
            }
        ]
    )

    out = parse_cores_frame(
        raw,
        product="gas",
        oil_conversion_audit=_single_field_audit(),
    )

    assert out.to_dict("records") == [
        {
            "field_name": "Gaviota",
            "year": 2024,
            "month": 1,
            "gas_mcf": pytest.approx(3.0 * GWH_TO_MCF),
        }
    ]


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

    out = CoresProductionLoader(
        product="oil",
        path=path,
        header_row=5,
        oil_conversion_audit=_single_field_audit(_density_factor(factor=TONNES_TO_BBL)),
    ).load()

    assert out.to_dict("records") == [
        {
            "field_name": "Ayoluengo",
            "year": 2026,
            "month": 6,
            "oil_bbl": pytest.approx(2.0 * TONNES_TO_BBL),
        }
    ]


def test_loader_passes_conversion_audit_to_parser(tmp_path):
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

    out = CoresProductionLoader(
        product="oil",
        path=path,
        header_row=5,
        oil_conversion_audit=_single_field_audit(),
    ).load()

    assert out.to_dict("records") == [
        {
            "field_name": "Ayoluengo",
            "year": 2026,
            "month": 6,
            "oil_bbl": pytest.approx(2.0 * 6.95),
        }
    ]


def test_loader_can_select_real_cores_production_sheet(tmp_path):
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
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"note": ["landing sheet"]}).to_excel(
            writer,
            sheet_name="Start",
            index=False,
        )
        raw.to_excel(writer, sheet_name="Production", index=False, startrow=5)

    out = CoresProductionLoader(
        product="oil",
        path=path,
        header_row=5,
        sheet_name="Production",
        oil_conversion_audit=_single_field_audit(_density_factor(factor=TONNES_TO_BBL)),
    ).load()

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
