"""Offline regression contracts for #1282; no browser or portal is started.

Numbers use CLDR 48.2 Latin grouping symbols and the root #,##0.### pattern:
https://github.com/unicode-org/cldr/blob/release-48-2/common/main/root.xml
The decimal-comma fallback and nonzero leading group retain PR #1399's policy.
Accents use Python 3.11 unicodedata.normalize (NFKD) and combining:
https://docs.python.org/3.11/library/unicodedata.html
"""

from pathlib import PureWindowsPath
from unittest.mock import patch

import pandas as pd
import pytest

from worldenergydata.mexico_cnh.data.loaders.excel_loader import CNHExcelLoader
from worldenergydata.mexico_cnh.data.loaders.pdf_parser import CNHPDFParser
from worldenergydata.mexico_cnh.scrapers.sih_scraper import SIHScraper


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1,234", 1234),
        ("1,234,567", 1234567),
        ("1234.5", 1234.5),
        ("1,234.5", 1234.5),
        ("-1,234", -1234),
        (" +1,234 ", 1234),
        ("0,125", 0.125),
        ("12,5", 12.5),
    ],
)
def test_pdf_numeric_groups(text, expected):
    """Hand calculation: 1,234 = 1000 + 200 + 30 + 4;
    1,234,567 = 1000000 + 234000 + 567; .5 adds 5/10; minus negates.
    0,125 = 125/1000 and 12,5 = 12 + 5/10 under the retained fallback.
    """
    result = CNHPDFParser()._convert_numeric_columns(pd.DataFrame({"oil": [text]}))
    assert result.loc[0, "oil"] == expected


def test_pdf_grouping_with_missing_and_invalid_cells():
    """1234 = 1000 + 234, 2345 = 2000 + 345, 3456 = 3000 + 456.

    The three valid rows exceed half of five rows under the existing majority
    heuristic (pdf_parser.py); this test does not establish that heuristic's merit.
    """
    frame = pd.DataFrame({"oil": ["1,234", "2,345", "3,456", None, "1,23,456"]})
    result = CNHPDFParser()._convert_numeric_columns(frame)
    assert result["oil"].iloc[:3].tolist() == [1234, 2345, 3456]
    assert result["oil"].iloc[3:].isna().all()


def test_pdf_identifier_text_unchanged():
    result = CNHPDFParser()._convert_numeric_columns(pd.DataFrame({"clave": ["1,234"]}))
    assert result.loc[0, "clave"] == "1,234"


@pytest.mark.parametrize(
    "header,expected",
    [
        ("Producción Aceite", "oil_production"),
        ("Produccio\u0301n Gas", "gas_production"),
        ("Año", "year"),
        ("Clasificación", "classification"),
        ("Número Pozo", "well_number"),
        ("Profundidad-Totál", "total_depth"),
    ],
)
def test_accented_header_maps(header, expected):
    """Remove combining marks after NFKD; existing COLUMN_MAPPING gives names."""
    result = CNHExcelLoader().normalize_columns(pd.DataFrame({header: ["text"]}))
    assert result.columns.tolist() == [expected]
    assert result.iloc[0, 0] == "text"


def test_unmapped_required_header_raises():
    """A required source header has no target; report its actual spelling."""
    header = "Producción Desconocida"
    with pytest.raises(ValueError, match=header):
        CNHExcelLoader().normalize_columns(
            pd.DataFrame({header: ["text"]}), required_columns=[header]
        )


def test_missing_required_target_raises():
    with pytest.raises(ValueError, match="oil_production"):
        CNHExcelLoader().normalize_columns(
            pd.DataFrame({"Fecha": ["text"]}), required_columns=["oil_production"]
        )


def test_required_source_header_maps():
    result = CNHExcelLoader().normalize_columns(
        pd.DataFrame({"Producción Aceite": ["text"]}),
        required_columns=["Producción Aceite"],
    )
    assert result.columns.tolist() == ["oil_production"]


@pytest.mark.parametrize(
    "method,header,expected",
    [
        ("parse_production_report", "Producción Aceite", "oil_production"),
        ("parse_well_report", "Profundidád Total", "total_depth"),
    ],
)
def test_specialized_parser_converts_accented_numeric_header(
    tmp_path, method, header, expected
):
    """Synthetic 3.5 = 3 + 5/10, so Excel numeric text becomes that number."""
    path = tmp_path / "synthetic.xlsx"
    pd.DataFrame({header: ["3.5"]}).to_excel(path, index=False)
    result = getattr(CNHExcelLoader(), method)(path)
    assert result.loc[0, expected] == 3.5


@pytest.mark.parametrize(
    "header,target",
    [
        ("BPD", "bpd"),
        ("Barriles Por Día", "barrels_per_day"),
        ("MMPCD", "mmcfd"),
        ("Miles Pies Cúbicos", "mcf"),
    ],
)
def test_production_parser_accepts_rate_only_workbook(tmp_path, header, target):
    """3.5 = 3 + 5/10; 12.5 = 12 + 5/10; 0.0254 = 254/10000."""
    path = tmp_path / "synthetic.xlsx"
    pd.DataFrame(
        {
            "Fecha": ["2026-01-03", "2026-01-01", "2026-01-02", "2026-01-04"],
            "Campo": ["Synthetic field"] * 4,
            header: ["0.0254", "3.5", "12.5", "invalid"],
        }
    ).to_excel(path, index=False)

    result = CNHExcelLoader().parse_production_report(path)

    assert pd.api.types.is_numeric_dtype(result[target])
    assert result[target].iloc[:3].tolist() == pytest.approx([3.5, 12.5, 0.0254])
    assert pd.isna(result[target].iloc[3])
    assert result["date"].dt.day.tolist() == [1, 2, 3, 4]


def test_missing_workbook_diagnostic_uses_forward_slashes():
    class MissingWindowsPath(PureWindowsPath):
        def exists(self):
            return False

    with (
        patch(
            "worldenergydata.mexico_cnh.data.loaders.excel_loader.Path",
            MissingWindowsPath,
        ),
        pytest.raises(FileNotFoundError) as error,
    ):
        CNHExcelLoader().load("relative/synthetic.xlsx")

    assert str(error.value) == "Excel file not found: relative/synthetic.xlsx"


@pytest.mark.parametrize("method", ["parse_production_report", "parse_well_report"])
def test_specialized_parser_reports_unmapped_required_column(tmp_path, method):
    header = "Medición Desconocida"
    path = tmp_path / "synthetic.xlsx"
    pd.DataFrame({header: ["3.5"]}).to_excel(path, index=False)
    with pytest.raises(ValueError, match=header):
        getattr(CNHExcelLoader(), method)(path, required_columns=[header])


def test_chrome_preferences_include_language_and_downloads(tmp_path):
    """Inspect actual Selenium options only; replacing prefs loses the language."""
    with patch(
        "worldenergydata.mexico_cnh.scrapers.sih_scraper.webdriver.Chrome"
    ) as start:
        scraper = SIHScraper(
            download_dir=tmp_path / "downloads", screenshot_dir=tmp_path / "screenshots"
        )
        options = scraper._create_chrome_options()
        prefs = options.experimental_options["prefs"]
        assert prefs["intl.accept_languages"] == "es-MX,es,en"
        assert prefs["download.default_directory"] == str(
            scraper.download_dir.absolute()
        )
        assert prefs["download.prompt_for_download"] is False
        assert prefs["plugins.always_open_pdf_externally"] is True
        start.assert_not_called()


@pytest.mark.parametrize("method", ["parse_production_report", "parse_well_report"])
def test_specialized_parser_rejects_unrecognized_schema(tmp_path, method):
    header = "Medición Desconocida"
    path = tmp_path / "synthetic.xlsx"
    pd.DataFrame({header: ["3.5"]}).to_excel(path, index=False)
    with pytest.raises(ValueError, match=header):
        getattr(CNHExcelLoader(), method)(path)


def test_accented_custom_mapping_keys():
    loader = CNHExcelLoader(column_mapping={"Producción Especial": "oil_production"})
    result = loader.normalize_columns(
        pd.DataFrame({"Produccio\u0301n Especial": ["text"]})
    )
    assert result.columns.tolist() == ["oil_production"]
