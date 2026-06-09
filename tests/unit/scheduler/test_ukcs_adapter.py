"""Tests for the UKCS scheduler adapter."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from worldenergydata.scheduler.jobs.ukcs_refresh import UkcsRefreshJob


def _raw_ukcs_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "FieldName": "Forties",
                "Year": 2026,
                "Month": 1,
                "OilProduction (Thousand Tonnes)": 450.3,
                "GasProduction (MMscf)": 12.5,
                "WaterProduction (Thousand Tonnes)": 310.2,
            }
        ]
    )


def _two_row_raw_ukcs_df() -> pd.DataFrame:
    first = _raw_ukcs_df().iloc[0].to_dict()
    second = {
        **first,
        "FieldName": "Buzzard",
        "OilProduction (Thousand Tonnes)": 780.1,
    }
    return pd.DataFrame([first, second])


def test_ukcs_downloads_configured_year_and_writes_outputs(tmp_path: Path):
    client = MagicMock()
    client.download.return_value = _raw_ukcs_df()

    with patch(
        "worldenergydata.scheduler.jobs.ukcs_refresh.NSTAClient",
        return_value=client,
    ):
        result = UkcsRefreshJob().run(
            {
                "output_dir": str(tmp_path),
                "year": 2026,
                "dataset": "monthly",
                "force_refresh": True,
            }
        )

    assert result.status == "success"
    assert result.records_updated == 1
    client.download.assert_called_once_with(
        year=2026,
        dataset="monthly",
        force_refresh=True,
    )
    assert (tmp_path / "raw" / "nsta_production_2026_monthly.parquet").exists()
    normalized_path = tmp_path / "ukcs_production_2026_monthly.parquet"
    assert normalized_path.exists()
    normalized = pd.read_parquet(normalized_path)
    assert normalized.loc[0, "field"] == "FORTIES"
    assert normalized.loc[0, "oil_bbl"] > 0


def test_ukcs_max_records_bounds_written_outputs(tmp_path: Path):
    client = MagicMock()
    client.download.return_value = _two_row_raw_ukcs_df()

    with patch(
        "worldenergydata.scheduler.jobs.ukcs_refresh.NSTAClient",
        return_value=client,
    ):
        result = UkcsRefreshJob().run(
            {
                "output_dir": str(tmp_path),
                "year": 2026,
                "max_records": 1,
            }
        )

    assert result.status == "success"
    assert result.records_updated == 1
    normalized = pd.read_parquet(tmp_path / "ukcs_production_2026_monthly.parquet")
    assert normalized["field"].tolist() == ["FORTIES"]


def test_ukcs_missing_output_dir_skips_without_network():
    with patch("worldenergydata.scheduler.jobs.ukcs_refresh.NSTAClient") as client:
        result = UkcsRefreshJob().run({"year": 2026})

    assert result.status == "skipped"
    assert result.records_updated == 0
    client.assert_not_called()


def test_ukcs_client_failure_returns_failure(tmp_path: Path):
    client = MagicMock()
    client.download.side_effect = RuntimeError("NSTA offline")

    with patch(
        "worldenergydata.scheduler.jobs.ukcs_refresh.NSTAClient",
        return_value=client,
    ):
        result = UkcsRefreshJob().run({"output_dir": str(tmp_path), "year": 2026})

    assert result.status == "failure"
    assert result.records_updated == 0
    assert "NSTA offline" in (result.error_msg or "")


def test_ukcs_passes_configured_download_url_to_client(tmp_path: Path):
    client = MagicMock()
    client.download.return_value = _raw_ukcs_df()
    download_url = "https://example.test/nsta/{year}/{dataset}.csv"

    with patch(
        "worldenergydata.scheduler.jobs.ukcs_refresh.NSTAClient",
        return_value=client,
    ) as client_cls:
        UkcsRefreshJob().run(
            {
                "output_dir": str(tmp_path),
                "year": 2026,
                "download_url": download_url,
            }
        )

    client_cls.assert_called_once_with(
        cache_dir=str(tmp_path / "raw"),
        base_url=download_url,
    )
