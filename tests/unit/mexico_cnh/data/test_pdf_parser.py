"""PDF numeric regressions; synthetic inputs, independent decimal arithmetic.

Format reference: Unicode UTS #35, LDML Part 3: Numbers, v48.2,
Number Symbols (group) and Number Format Patterns (Special Pattern Characters):
https://www.unicode.org/reports/tr35/tr35-numbers.html#Number_Symbols
Comma grouping takes precedence for the thousands examples in issue #1282.
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
        ("0", 0),
    ],
)
def test_numeric_formats(text, expected):
    """Hand calculations, using base-ten place values:

    1,234 = 1000 + 200 + 30 + 4; 12,345 = 12000 + 300 + 40 + 5;
    1,234,567 = 1000000 + 234000 + 567. Appending .5 adds 5/10;
    minus negates the sum, plus and surrounding spaces leave it unchanged.
    Ungrouped 1234.5 has the same place values. Legacy decimal-comma 12,5
    is 12 + 5/10; zero has no nonzero place values.
    """
    result = CNHPDFParser()._convert_numeric_columns(pd.DataFrame({"oil": [text]}))
    assert result.loc[0, "oil"] == expected


def test_grouped_numbers_with_missing_and_invalid_cells():
    """1234 = 1000 + 234; 2345 = 2000 + 345; 3456 = 3000 + 456.

    Missing text and malformed repeated grouping have no numeric value.
    Three valid cells out of five exceed the existing majority rule.
    """
    frame = pd.DataFrame({"oil": ["1,234", "2,345", "3,456", None, "1,23,456"]})
    result = CNHPDFParser()._convert_numeric_columns(frame)
    assert result["oil"].iloc[:3].tolist() == [1234, 2345, 3456]
    assert result["oil"].iloc[3:].isna().all()


def test_identifier_and_numeric_columns_are_preserved():
    """An identifier is text; numeric 1234 = 1000 + 234 stays numeric."""
    frame = pd.DataFrame({"id": ["1,234"], "oil": [1234], "name": ["1,234"]})
    result = CNHPDFParser()._convert_numeric_columns(frame.copy())
    pd.testing.assert_frame_equal(result, frame)


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
