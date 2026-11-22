"""PDF numeric regressions; synthetic inputs, independent decimal arithmetic.

Parser policy for issue #1282: three-digit comma groups with a nonzero first
group take precedence over the decimal-comma fallback, regardless of locale.
These tests establish parsing behavior, not a live CNH report's unit basis.
"""

import pandas as pd
import pytest

from worldenergydata.mexico_cnh.data.loaders.pdf_parser import CNHPDFParser


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1,234", 1234),
        ("12,345", 12345),
        ("1,234,567", 1234567),
        ("1,234.5", 1234.5),
        ("-1,234.5", -1234.5),
        (" +1,234.5 ", 1234.5),
        ("1234.5", 1234.5),
        ("12,5", 12.5),
        ("0,125", 0.125),
        ("-0,500", -0.5),
        ("00,125", 0.125),
        ("012,345", 12.345),
        ("0", 0),
    ],
)
def test_numeric_formats(text, expected):
    """Hand calculations, using base-ten place values:

    1,234 = 1000 + 200 + 30 + 4; 12,345 = 12000 + 300 + 40 + 5;
    1,234,567 = 1000000 + 234000 + 567. Appending .5 adds 5/10;
    minus negates the sum, plus and surrounding spaces leave it unchanged.
    Ungrouped 1234.5 has the same place values. Legacy decimal-comma 12,5
    is 12 + 5/10; 0,125 and 00,125 are 125/1000; -0,500 is -5/10;
    012,345 is 12 + 345/1000; zero has no nonzero place values.
    """
    result = CNHPDFParser()._convert_numeric_columns(pd.DataFrame({"oil": [text]}))
    assert result.loc[0, "oil"] == expected


def test_grouped_numbers_with_missing_and_invalid_cells():
    """1234 = 1000 + 234; 2345 = 2000 + 345; 3456 = 3000 + 456.

    Missing text and grouping outside this parser's policy have no numeric value.
    Three valid cells out of five exceed the existing majority rule.
    """
    frame = pd.DataFrame({"oil": ["1,234", "2,345", "3,456", None, "1,23,456"]})
    result = CNHPDFParser()._convert_numeric_columns(frame)
    assert result["oil"].iloc[:3].tolist() == [1234, 2345, 3456]
    assert result["oil"].iloc[3:].isna().all()


@pytest.mark.parametrize(
    "header",
    [
        "id",
        "ID",
        "Record ID",
        "Clave",
        "Clave del pozo",
        "Nombre",
        "Name",
        "ID_POZO",
        "clave_pozo",
        "record_id",
        "Identificador",
        "Identificador del pozo",
        "Identificación",
        "IdPozo",
        "ClavePozo",
        "NombreCampo",
        "PozoID",
        "IDs",
        "Claves",
    ],
)
def test_identifier_and_numeric_columns_are_preserved(header):
    """Identifiers retain leading zeros; existing numeric values stay numeric."""
    frame = pd.DataFrame(
        {
            header: ["1,234", "00123", "00456"],
            "oil": [1234, 2345, 3456],
            "name": ["1,234", "00123", "00456"],
        }
    )
    result = CNHPDFParser()._convert_numeric_columns(frame.copy())
    pd.testing.assert_frame_equal(result, frame)


@pytest.mark.parametrize(
    "header", ["Liquidos", "Hidrocarburos", "Unidad", "Produccion de liquidos"]
)
def test_headers_containing_identifier_substrings_remain_text(header):
    """Preserve the existing substring policy until header parsing is revised."""
    result = CNHPDFParser()._convert_numeric_columns(pd.DataFrame({header: ["1,234"]}))
    assert result.loc[0, header] == "1,234"


def test_production_extraction_converts_thousands(monkeypatch):
    """Table boundary: 1,234,567 = 1000000 + 234000 + 567."""
    parser = CNHPDFParser()
    monkeypatch.setattr(
        parser,
        "extract_tables",
        lambda *args, **kwargs: [pd.DataFrame({"oil": ["1,234,567"]})],
    )
    result = parser.extract_production_data("unused.pdf")
    assert result.loc[0, "oil"] == 1234567
