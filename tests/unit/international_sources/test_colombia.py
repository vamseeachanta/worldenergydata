"""Synthetic monthly rows using the ANH Socrata column descriptions.

Oil: https://www.datos.gov.co/api/views/fdvb-hsrf.json, produccion_bls.
Gas: https://www.datos.gov.co/api/views/5dux-bfvx.json, produccionkpc.
Both metadata records were read on 2026-10-20. No live volumes are fixtures.
"""

from decimal import Decimal

import pytest

from worldenergydata.international_sources.colombia import (
    describe_dataset,
    normalize_rows,
    rows_url,
)


def test_metadata_preserves_quarterly_refresh_and_source_vintage():
    metadata = {
        "id": "fdvb-hsrf",
        "columns": [{"fieldName": "produccion_bls"}],
        "license": {
            "name": "Creative Commons Attribution | Share Alike 4.0 International"
        },
        "rowsUpdatedAt": 0,
        "metadata": {
            "custom_fields": {
                "Información de Datos": {"Frecuencia de Actualización": "Trimestral"}
            }
        },
    }
    result = describe_dataset(metadata)
    assert result.dataset_id == "fdvb-hsrf"
    assert result.update_frequency == "Trimestral"
    # POSIX epoch definition; this synthetic timestamp exercises a true zero.
    assert result.source_modified == "1970-01-01T00:00:00+00:00"
    assert "Share Alike" in result.license
    assert result.production_status == "NOT_EVALUATED"


def test_native_rows_preserve_nulls_and_keep_contracts_separate():
    """Hand calculation: supplied monthly oil values 10.5 + 2.5 = 13 bbl.

    Rows represent two synthetic contracts, not two independent fields. The
    third value is unknown and must remain unknown; it cannot contribute zero.
    No conversion, daily-rate multiplication or field aggregation is performed.
    """
    rows = [
        {
            "vigencia": "2024",
            "mes": "2",
            "campo": "EXAMPLE",
            "contrato": contract,
            "operadora": "EXAMPLE OPERATOR",
            "produccion_bls": value,
        }
        for contract, value in [("A", "10.5"), ("B", "2.5"), ("C", None)]
    ]
    result = normalize_rows(rows, commodity="oil")
    assert [r.contract for r in result] == ["A", "B", "C"]
    assert sum(r.volume for r in result if r.volume is not None) == Decimal(13)
    assert result[-1].volume is None
    assert result[0].period == "2024-02"
    assert result[0].unit == "bbl"
    assert result[0].commodity == "oil"
    assert result[0].field_name == "EXAMPLE"


def test_gas_uses_its_own_column_without_inventing_oil_or_water():
    """Synthetic 2.5 thousand cubic feet is retained as 2.5 Mcf, no scaling."""
    result = normalize_rows(
        [{"vigencia": "2024", "mes": "1", "campo": "EXAMPLE", "produccionkpc": "2.5"}],
        commodity="gas",
    )
    assert result[0].volume == Decimal("2.5")
    assert result[0].unit == "Mcf"
    assert result[0].contract is None


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "1,234", "unknown"])
def test_ambiguous_or_invalid_volume_is_rejected(value):
    with pytest.raises(ValueError, match="volume"):
        normalize_rows(
            [
                {
                    "vigencia": "2024",
                    "mes": "1",
                    "campo": "EXAMPLE",
                    "produccion_bls": value,
                }
            ],
            commodity="oil",
        )


@pytest.mark.parametrize(
    "year,month", [("2024.5", "1"), ("2024", "0"), ("2024", "13"), (None, "1")]
)
def test_invalid_monthly_period_is_rejected(year, month):
    with pytest.raises(ValueError, match="period"):
        normalize_rows(
            [{"vigencia": year, "mes": month, "campo": "EXAMPLE"}], commodity="oil"
        )


def test_query_is_explicitly_bounded_and_deterministic():
    assert rows_url("oil", limit=2, offset=4) == (
        "https://www.datos.gov.co/resource/fdvb-hsrf.json?"
        "%24limit=2&%24offset=4&%24order=%3Aid"
    )
    with pytest.raises(ValueError):
        rows_url("oil", limit=0, offset=0)
    with pytest.raises(ValueError):
        rows_url("oil", limit=True, offset=0)
    with pytest.raises(ValueError):
        rows_url("water", limit=1, offset=0)


def test_observed_grouped_decimal_format_is_parsed_without_scaling():
    """Hand calculation: 1,234.50 means 1*1000 + 234 + 50/100 = 1234.50.

    Grouped decimal format was observed in both cited ANH row endpoints on
    2026-10-20. The fixture value is synthetic. Group-only text stays ambiguous.
    """
    result = normalize_rows(
        [
            {
                "vigencia": "2024",
                "mes": "1",
                "campo": "EXAMPLE",
                "produccion_bls": "1,234.50",
            }
        ],
        commodity="oil",
    )
    assert result[0].volume == Decimal("1234.50")


@pytest.mark.parametrize("value", ["12,34.50", "1234,567.00", "1.234,50", True])
def test_malformed_grouping_and_boolean_volumes_are_rejected(value):
    with pytest.raises(ValueError, match="volume"):
        normalize_rows(
            [
                {
                    "vigencia": "2024",
                    "mes": "1",
                    "campo": "EXAMPLE",
                    "produccion_bls": value,
                }
            ],
            commodity="oil",
        )


@pytest.mark.parametrize(
    "commodity,column,unit",
    [("oil", "produccion_bls", "bbl"), ("gas", "produccionkpc", "Mcf")],
)
@pytest.mark.parametrize("representation", ["omitted", "null", "empty"])
def test_source_nulls_preserve_unknown_volumes(commodity, column, unit, representation):
    """Socrata JSON omits null-valued fields; zero remains a known value.

    Contract: https://dev.socrata.com/docs/formats/json.html.
    Synthetic known values are retained as 0 and 2.5, without conversion.
    """
    row = {"vigencia": "2024", "mes": "1", "campo": "EXAMPLE", "contrato": "A"}
    if representation != "omitted":
        row[column] = None if representation == "null" else ""
    rows = [
        row,
        {**row, "contrato": "B", column: "0"},
        {**row, "contrato": "C", column: "2.5"},
    ]

    result = normalize_rows(rows, commodity=commodity)

    assert [item.volume for item in result] == [None, Decimal("0"), Decimal("2.5")]
    assert [item.contract for item in result] == ["A", "B", "C"]
    assert all(item.unit == unit for item in result)
    assert all(item.period == "2024-01" for item in result)


@pytest.mark.parametrize(
    "dataset_id,column",
    [("fdvb-hsrf", "produccion_bls"), ("5dux-bfvx", "produccionkpc")],
)
def test_metadata_declares_the_required_volume_column(dataset_id, column):
    result = describe_dataset({"id": dataset_id, "columns": [{"fieldName": column}]})
    assert result.dataset_id == dataset_id
    assert result.source_modified is None
    assert result.production_status == "NOT_EVALUATED"


@pytest.mark.parametrize("dataset_id", ["fdvb-hsrf", "5dux-bfvx"])
@pytest.mark.parametrize(
    "schema",
    [
        {},
        {"columns": None},
        {"columns": {}},
        {"columns": []},
        {"columns": ["invalid"]},
        {"columns": [{"name": "produccion_bls"}]},
        {"columns": [{"fieldName": "renamed_volume"}]},
    ],
)
def test_missing_or_invalid_metadata_volume_column_is_schema_drift(dataset_id, schema):
    with pytest.raises(ValueError, match="column"):
        describe_dataset({"id": dataset_id, **schema})


@pytest.mark.parametrize(
    "dataset_id,other_column",
    [("fdvb-hsrf", "produccionkpc"), ("5dux-bfvx", "produccion_bls")],
)
def test_metadata_requires_the_volume_column_for_its_own_commodity(
    dataset_id, other_column
):
    with pytest.raises(ValueError, match="column"):
        describe_dataset({"id": dataset_id, "columns": [{"fieldName": other_column}]})
