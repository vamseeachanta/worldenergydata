"""Tests for OSHA fatalities acquirer module."""

import pandas as pd
import pytest

from worldenergydata.hse.acquirers.osha_fatalities_acquirer import (
    DOWNLOAD_TIMEOUT,
    OIL_GAS_KEYWORDS,
    OIL_GAS_NAICS_PREFIXES,
    SEVERE_INJURY_URL,
    OSHAFatalitiesAcquirer,
    build_parser,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_naics_prefixes(self):
        assert "211" in OIL_GAS_NAICS_PREFIXES
        assert "213111" in OIL_GAS_NAICS_PREFIXES

    def test_keywords(self):
        assert "oil" in OIL_GAS_KEYWORDS
        assert "drilling" in OIL_GAS_KEYWORDS
        assert "pipeline" in OIL_GAS_KEYWORDS

    def test_timeout(self):
        assert DOWNLOAD_TIMEOUT == 120

    def test_url(self):
        assert "osha.gov" in SEVERE_INJURY_URL


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestOSHAFatalitiesAcquirerInit:
    def test_defaults(self):
        acq = OSHAFatalitiesAcquirer()
        assert acq.severe_injury_url == SEVERE_INJURY_URL
        assert acq.timeout == DOWNLOAD_TIMEOUT

    def test_custom(self):
        acq = OSHAFatalitiesAcquirer(
            severe_injury_url="http://example.com/test.csv",
            timeout=30,
        )
        assert acq.severe_injury_url == "http://example.com/test.csv"
        assert acq.timeout == 30


# ---------------------------------------------------------------------------
# _find_column
# ---------------------------------------------------------------------------


class TestFindColumn:
    def test_first_match(self):
        df = pd.DataFrame({"naics": [1], "other": [2]})
        result = OSHAFatalitiesAcquirer._find_column(df, ["naics", "naics_code"])
        assert result == "naics"

    def test_second_match(self):
        df = pd.DataFrame({"naics_code": [1], "other": [2]})
        result = OSHAFatalitiesAcquirer._find_column(df, ["naics", "naics_code"])
        assert result == "naics_code"

    def test_no_match(self):
        df = pd.DataFrame({"other": [1]})
        result = OSHAFatalitiesAcquirer._find_column(df, ["naics", "naics_code"])
        assert result is None


# ---------------------------------------------------------------------------
# build_parser
# ---------------------------------------------------------------------------


class TestBuildParser:
    def test_required_args(self):
        parser = build_parser()
        args = parser.parse_args(["--output-dir", "/tmp/test"])
        assert args.output_dir == "/tmp/test"
        assert args.force is False
        assert args.inspection_csv is None
        assert args.filter_naics is False
        assert args.timeout == DOWNLOAD_TIMEOUT

    def test_all_args(self):
        parser = build_parser()
        args = parser.parse_args(
            [
                "--output-dir",
                "/tmp/test",
                "--force",
                "--inspection-csv",
                "/tmp/inspections.csv",
                "--filter-naics",
                "--timeout",
                "60",
            ]
        )
        assert args.force is True
        assert args.inspection_csv == "/tmp/inspections.csv"
        assert args.filter_naics is True
        assert args.timeout == 60


# ---------------------------------------------------------------------------
# download_all (file-exists skip path)
# ---------------------------------------------------------------------------


class TestDownloadAll:
    def test_skips_existing(self, tmp_path):
        # Create an existing file so download is skipped
        severe = tmp_path / "osha_severe_injury.csv"
        severe.write_text("header\ndata\n")
        acq = OSHAFatalitiesAcquirer()
        result = acq.download_all(str(tmp_path), force=False)
        assert "severe_injury" in result
        assert result["severe_injury"] == severe


# ---------------------------------------------------------------------------
# extract_fatality_inspections (with local CSV)
# ---------------------------------------------------------------------------


class TestExtractFatalityInspections:
    def test_basic(self, tmp_path):
        # Create a CSV with inspection data
        csv_content = "INSP_TYPE,NAME\nA,Acme Oil\nB,Safe Co\nA,Drill Inc\n"
        in_path = tmp_path / "inspections.csv"
        in_path.write_text(csv_content)
        out_path = tmp_path / "fatalities.csv"

        acq = OSHAFatalitiesAcquirer()
        count = acq.extract_fatality_inspections(str(in_path), str(out_path))
        assert count == 2
        assert out_path.exists()

    def test_no_type_column(self, tmp_path):
        csv_content = "OTHER_COL,NAME\nX,Test\n"
        in_path = tmp_path / "inspections.csv"
        in_path.write_text(csv_content)
        out_path = tmp_path / "fatalities.csv"

        acq = OSHAFatalitiesAcquirer()
        count = acq.extract_fatality_inspections(str(in_path), str(out_path))
        assert count == 0


# ---------------------------------------------------------------------------
# filter_oil_and_gas (with local CSV)
# ---------------------------------------------------------------------------


class TestFilterOilAndGas:
    def test_by_naics(self, tmp_path):
        csv_content = "NAICS,EMPLOYER\n211100,Acme Oil\n541000,Consulting Co\n"
        in_path = tmp_path / "data.csv"
        in_path.write_text(csv_content)
        out_path = tmp_path / "filtered.csv"

        acq = OSHAFatalitiesAcquirer()
        count = acq.filter_oil_and_gas(str(in_path), str(out_path))
        assert count == 1

    def test_by_keyword(self, tmp_path):
        csv_content = "OTHER,EMPLOYER\nX,Acme Oil Services\nY,Software Inc\n"
        in_path = tmp_path / "data.csv"
        in_path.write_text(csv_content)
        out_path = tmp_path / "filtered.csv"

        acq = OSHAFatalitiesAcquirer()
        count = acq.filter_oil_and_gas(str(in_path), str(out_path))
        assert count == 1

    def test_no_matches(self, tmp_path):
        csv_content = "OTHER,COMPANY\nX,Tech Corp\nY,Food Inc\n"
        in_path = tmp_path / "data.csv"
        in_path.write_text(csv_content)
        out_path = tmp_path / "filtered.csv"

        acq = OSHAFatalitiesAcquirer()
        count = acq.filter_oil_and_gas(str(in_path), str(out_path))
        assert count == 0
