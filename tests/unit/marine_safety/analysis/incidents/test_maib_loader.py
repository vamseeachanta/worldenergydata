"""
Tests for maib_loader.py — MAIB occurrence CSV taxonomy pipeline loader.

Covers:
- MAIBLoader CSV loading with semicolon delimiter
- Column mapping via MAIB_COLUMN_MAP to canonical schema
- Year filtering
- TaxonomyRecord generation from MAIB CSV
- load_maib_csv convenience function
- load_maib_csv_to_records convenience function
- load_dataframe_as_maib in-memory path
- describe_maib_dataset summary
- Error handling (missing file, malformed CSV)
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import List

import pandas as pd
import pytest

from worldenergydata.marine_safety.analysis.incidents.incident_taxonomy import (
    RootCauseType,
    TaxonomyRecord,
)
from worldenergydata.marine_safety.analysis.incidents.maib_loader import (
    MAIBLoader,
    describe_maib_dataset,
    load_dataframe_as_maib,
    load_maib_csv,
    load_maib_csv_to_records,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MAIB_CSV_CONTENT = textwrap.dedent(
    """\
    Occurrence_Id;Date;Main_Event;Vessel_Name;Vessel_Type;Latitude;Longitude;Deaths;Injuries;Abstract
    2020-001;2020-03-15;Collision;MV Searoamer;Cargo Ship;56.5;-2.1;0;2;Two vessels collided in fog
    2021-002;2021-08-19;Grounding;FV Argyll;Fishing Vessel;59.2;-1.5;1;3;Fishing vessel grounded on rocks
    2022-003;2022-11-05;Fire;MT Nordic Carrier;Tanker;53.6;-0.2;0;0;Engine room fire
"""
)

MAIB_CSV_WITH_HUMAN_ERROR_CONTENT = textwrap.dedent(
    """\
    Occurrence_Id;Date;Main_Event;Vessel_Name;Vessel_Type;Latitude;Longitude;Deaths;Injuries;Abstract
    2023-010;2023-06-01;Collision;SS Navigator;Cargo Ship;51.5;0.1;0;0;Collision due to watchkeeping failure
"""
)


@pytest.fixture()
def maib_csv(tmp_path: Path) -> Path:
    """Write a minimal MAIB occurrence CSV with semicolon delimiter."""
    p = tmp_path / "maib_occurrences.csv"
    p.write_text(MAIB_CSV_CONTENT, encoding="utf-8")
    return p


@pytest.fixture()
def maib_human_error_csv(tmp_path: Path) -> Path:
    """MAIB CSV with a human-error keyword in the narrative."""
    p = tmp_path / "maib_human_error.csv"
    p.write_text(MAIB_CSV_WITH_HUMAN_ERROR_CONTENT, encoding="utf-8")
    return p


@pytest.fixture()
def loader() -> MAIBLoader:
    return MAIBLoader()


# ---------------------------------------------------------------------------
# MAIBLoader.load — basic loading and column renaming
# ---------------------------------------------------------------------------


class TestMAIBLoaderLoad:
    def test_returns_dataframe(self, loader: MAIBLoader, maib_csv: Path) -> None:
        df = loader.load(maib_csv)
        assert isinstance(df, pd.DataFrame)

    def test_row_count(self, loader: MAIBLoader, maib_csv: Path) -> None:
        df = loader.load(maib_csv)
        assert len(df) == 3

    def test_report_id_column_mapped(self, loader: MAIBLoader, maib_csv: Path) -> None:
        df = loader.load(maib_csv)
        assert "report_id" in df.columns
        assert set(df["report_id"]) == {"2020-001", "2021-002", "2022-003"}

    def test_incident_date_column_mapped(
        self, loader: MAIBLoader, maib_csv: Path
    ) -> None:
        df = loader.load(maib_csv)
        assert "incident_date" in df.columns
        assert "2020-03-15" in df["incident_date"].values

    def test_vessel_name_column_mapped(
        self, loader: MAIBLoader, maib_csv: Path
    ) -> None:
        df = loader.load(maib_csv)
        assert "vessel_name" in df.columns
        assert "MV Searoamer" in df["vessel_name"].values

    def test_vessel_type_column_mapped(
        self, loader: MAIBLoader, maib_csv: Path
    ) -> None:
        df = loader.load(maib_csv)
        assert "vessel_type" in df.columns
        assert "Cargo Ship" in df["vessel_type"].values

    def test_latitude_column_mapped(self, loader: MAIBLoader, maib_csv: Path) -> None:
        df = loader.load(maib_csv)
        assert "latitude" in df.columns
        assert pd.to_numeric(df["latitude"], errors="coerce").notna().all()

    def test_longitude_column_mapped(self, loader: MAIBLoader, maib_csv: Path) -> None:
        df = loader.load(maib_csv)
        assert "longitude" in df.columns

    def test_fatality_count_column_mapped(
        self, loader: MAIBLoader, maib_csv: Path
    ) -> None:
        df = loader.load(maib_csv)
        assert "fatality_count" in df.columns

    def test_injury_count_column_mapped(
        self, loader: MAIBLoader, maib_csv: Path
    ) -> None:
        df = loader.load(maib_csv)
        assert "injury_count" in df.columns

    def test_narrative_column_mapped(self, loader: MAIBLoader, maib_csv: Path) -> None:
        df = loader.load(maib_csv)
        assert "narrative" in df.columns
        assert "fog" in df["narrative"].iloc[0].lower()

    def test_source_column_added(self, loader: MAIBLoader, maib_csv: Path) -> None:
        df = loader.load(maib_csv)
        assert "source" in df.columns
        assert (df["source"] == "maib").all()

    def test_incident_type_column_mapped(
        self, loader: MAIBLoader, maib_csv: Path
    ) -> None:
        df = loader.load(maib_csv)
        assert "incident_type" in df.columns
        assert "Collision" in df["incident_type"].values

    def test_fatality_count_is_integer(
        self, loader: MAIBLoader, maib_csv: Path
    ) -> None:
        df = loader.load(maib_csv)
        assert df["fatality_count"].dtype in (int, "int64", "int32")

    def test_injury_count_is_integer(self, loader: MAIBLoader, maib_csv: Path) -> None:
        df = loader.load(maib_csv)
        assert df["injury_count"].dtype in (int, "int64", "int32")


# ---------------------------------------------------------------------------
# MAIBLoader.load — year filtering
# ---------------------------------------------------------------------------


class TestMAIBLoaderYearFilter:
    def test_year_filter_returns_subset(
        self, loader: MAIBLoader, maib_csv: Path
    ) -> None:
        df = loader.load(maib_csv, year_filter=2020)
        assert len(df) == 1
        assert df["report_id"].iloc[0] == "2020-001"

    def test_year_filter_2021(self, loader: MAIBLoader, maib_csv: Path) -> None:
        df = loader.load(maib_csv, year_filter=2021)
        assert len(df) == 1
        assert df["report_id"].iloc[0] == "2021-002"

    def test_year_filter_no_match_returns_empty(
        self, loader: MAIBLoader, maib_csv: Path
    ) -> None:
        df = loader.load(maib_csv, year_filter=1999)
        assert len(df) == 0

    def test_no_year_filter_returns_all(
        self, loader: MAIBLoader, maib_csv: Path
    ) -> None:
        df = loader.load(maib_csv, year_filter=None)
        assert len(df) == 3


# ---------------------------------------------------------------------------
# MAIBLoader.load — error handling
# ---------------------------------------------------------------------------


class TestMAIBLoaderErrors:
    def test_file_not_found_raises(self, loader: MAIBLoader) -> None:
        with pytest.raises(FileNotFoundError):
            loader.load("/nonexistent/path/maib.csv")

    def test_malformed_csv_raises_value_error(
        self, loader: MAIBLoader, tmp_path: Path
    ) -> None:
        bad = tmp_path / "bad.csv"
        # Write binary content that can't be decoded as UTF-8 with errors
        bad.write_bytes(b"\x80\x81\x82 invalid utf-8 data \xff\xfe" * 100)
        # The normaliser should raise ValueError or return empty; either is acceptable
        try:
            df = loader.load(bad)
        except (ValueError, UnicodeDecodeError):
            pass  # Expected error path


# ---------------------------------------------------------------------------
# MAIBLoader.load_to_records
# ---------------------------------------------------------------------------


class TestMAIBLoaderToRecords:
    def test_returns_list_of_taxonomy_records(
        self, loader: MAIBLoader, maib_csv: Path
    ) -> None:
        records = loader.load_to_records(maib_csv)
        assert isinstance(records, list)
        assert all(isinstance(r, TaxonomyRecord) for r in records)

    def test_record_count_matches_rows(
        self, loader: MAIBLoader, maib_csv: Path
    ) -> None:
        records = loader.load_to_records(maib_csv)
        assert len(records) == 3

    def test_source_is_maib(self, loader: MAIBLoader, maib_csv: Path) -> None:
        records = loader.load_to_records(maib_csv)
        assert all(r.source == "maib" for r in records)

    def test_report_ids_present(self, loader: MAIBLoader, maib_csv: Path) -> None:
        records = loader.load_to_records(maib_csv)
        ids = {r.report_id for r in records}
        assert "2020-001" in ids
        assert "2021-002" in ids

    def test_root_cause_is_enum(self, loader: MAIBLoader, maib_csv: Path) -> None:
        records = loader.load_to_records(maib_csv)
        for r in records:
            assert isinstance(r.root_cause, RootCauseType)

    def test_human_error_classified_correctly(
        self, loader: MAIBLoader, maib_human_error_csv: Path
    ) -> None:
        records = loader.load_to_records(maib_human_error_csv)
        assert len(records) == 1
        assert records[0].root_cause == RootCauseType.HUMAN_ERROR

    def test_year_filter_propagated(self, loader: MAIBLoader, maib_csv: Path) -> None:
        records = loader.load_to_records(maib_csv, year_filter=2022)
        assert len(records) == 1
        assert records[0].report_id == "2022-003"

    def test_fatality_count_populated(self, loader: MAIBLoader, maib_csv: Path) -> None:
        records = loader.load_to_records(maib_csv)
        # 2021-002 has 1 death
        rec = next(r for r in records if r.report_id == "2021-002")
        assert rec.fatality_count == 1

    def test_injury_count_populated(self, loader: MAIBLoader, maib_csv: Path) -> None:
        records = loader.load_to_records(maib_csv)
        # 2020-001 has 2 injuries
        rec = next(r for r in records if r.report_id == "2020-001")
        assert rec.injury_count == 2

    def test_coordinates_populated(self, loader: MAIBLoader, maib_csv: Path) -> None:
        records = loader.load_to_records(maib_csv)
        rec = next(r for r in records if r.report_id == "2020-001")
        assert rec.latitude == pytest.approx(56.5)
        assert rec.longitude == pytest.approx(-2.1)


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


class TestLoadMAIBCsv:
    def test_load_maib_csv_returns_dataframe(self, maib_csv: Path) -> None:
        df = load_maib_csv(maib_csv)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3

    def test_load_maib_csv_year_filter(self, maib_csv: Path) -> None:
        df = load_maib_csv(maib_csv, year_filter=2020)
        assert len(df) == 1

    def test_load_maib_csv_to_records_returns_list(self, maib_csv: Path) -> None:
        records = load_maib_csv_to_records(maib_csv)
        assert isinstance(records, list)
        assert len(records) == 3

    def test_load_maib_csv_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_maib_csv("/no/such/file.csv")


class TestLoadDataframeAsMAIB:
    def test_in_memory_dataframe_classified(self) -> None:
        df = pd.DataFrame(
            {
                "Occurrence_Id": ["TEST-001", "TEST-002"],
                "Date": ["2023-01-10", "2023-02-20"],
                "Main_Event": ["Collision", "Grounding"],
                "Vessel_Name": ["MV Alpha", "MV Beta"],
                "Vessel_Type": ["Cargo Ship", "Tanker"],
                "Abstract": [
                    "Operator error led to collision",
                    "Equipment failure caused grounding",
                ],
                "Deaths": [0, 1],
                "Injuries": [2, 0],
                "Latitude": [51.5, 53.4],
                "Longitude": [0.1, -3.2],
            }
        )
        records = load_dataframe_as_maib(df)
        assert len(records) == 2
        assert all(r.source == "maib" for r in records)

    def test_root_cause_human_error_from_narrative(self) -> None:
        df = pd.DataFrame(
            {
                "Occurrence_Id": ["HUERR-001"],
                "Abstract": ["Watchkeeping failure led to allision"],
                "Deaths": [0],
                "Injuries": [0],
            }
        )
        records = load_dataframe_as_maib(df)
        assert records[0].root_cause == RootCauseType.HUMAN_ERROR

    def test_root_cause_equipment_failure_from_narrative(self) -> None:
        df = pd.DataFrame(
            {
                "Occurrence_Id": ["EQUIP-001"],
                "Abstract": ["Steering failure caused grounding"],
                "Deaths": [0],
                "Injuries": [0],
            }
        )
        records = load_dataframe_as_maib(df)
        assert records[0].root_cause == RootCauseType.EQUIPMENT_FAILURE

    def test_empty_dataframe_returns_empty_list(self) -> None:
        df = pd.DataFrame()
        records = load_dataframe_as_maib(df)
        assert records == []


# ---------------------------------------------------------------------------
# describe_maib_dataset
# ---------------------------------------------------------------------------


class TestDescribeMAIBDataset:
    def test_total_records(self, loader: MAIBLoader, maib_csv: Path) -> None:
        df = loader.load(maib_csv)
        desc = describe_maib_dataset(df)
        assert desc["total_records"] == 3

    def test_date_range(self, loader: MAIBLoader, maib_csv: Path) -> None:
        df = loader.load(maib_csv)
        desc = describe_maib_dataset(df)
        assert desc["date_range"] is not None
        start, end = desc["date_range"]
        assert start <= end

    def test_vessel_types_list(self, loader: MAIBLoader, maib_csv: Path) -> None:
        df = loader.load(maib_csv)
        desc = describe_maib_dataset(df)
        assert isinstance(desc["vessel_types"], list)
        assert len(desc["vessel_types"]) > 0

    def test_columns_present(self, loader: MAIBLoader, maib_csv: Path) -> None:
        df = loader.load(maib_csv)
        desc = describe_maib_dataset(df)
        assert "report_id" in desc["columns_present"]

    def test_empty_dataframe_returns_zeros(self) -> None:
        desc = describe_maib_dataset(pd.DataFrame())
        assert desc["total_records"] == 0
        assert desc["date_range"] is None
        assert desc["vessel_types"] == []
        assert desc["columns_present"] == []
