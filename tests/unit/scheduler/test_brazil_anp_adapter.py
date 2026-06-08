"""Tests for the Brazil ANP scheduler adapter."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from worldenergydata.scheduler.jobs.brazil_anp_refresh import BrazilAnpRefreshJob


def _raw_anp_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "campo": "LULA",
                "poco": "7LL55",
                "data": "2026-01-01",
                "oleo_sm3": 10.0,
                "condensado_sm3": 1.0,
                "gas_mm3": 2.0,
                "agua_sm3": 3.0,
            }
        ]
    )


def test_brazil_anp_downloads_configured_semester_and_writes_outputs(tmp_path: Path):
    client = MagicMock()
    client.download.return_value = _raw_anp_df()

    with patch(
        "worldenergydata.scheduler.jobs.brazil_anp_refresh.ANPClient",
        return_value=client,
    ):
        result = BrazilAnpRefreshJob().run(
            {
                "output_dir": str(tmp_path),
                "year": 2026,
                "semester": 1,
                "force_refresh": True,
            }
        )

    assert result.status == "success"
    assert result.records_updated == 1
    client.download.assert_called_once_with(
        year=2026,
        semester=1,
        force_refresh=True,
    )
    assert (tmp_path / "raw" / "anp_production_2026_s1.parquet").exists()
    normalized_path = tmp_path / "anp_production_2026_s1.parquet"
    assert normalized_path.exists()
    normalized = pd.read_parquet(normalized_path)
    assert normalized.loc[0, "field"] == "LULA"
    assert normalized.loc[0, "oil_bbl"] > 0


def test_brazil_anp_defaults_to_latest_completed_semester(tmp_path: Path):
    client = MagicMock()
    client.download.return_value = _raw_anp_df()

    with (
        patch(
            "worldenergydata.scheduler.jobs.brazil_anp_refresh.ANPClient",
            return_value=client,
        ),
        patch(
            "worldenergydata.scheduler.jobs.brazil_anp_refresh.datetime",
        ) as mock_datetime,
    ):
        mock_datetime.now.return_value = pd.Timestamp("2026-08-15").to_pydatetime()
        result = BrazilAnpRefreshJob().run({"output_dir": str(tmp_path)})

    assert result.status == "success"
    client.download.assert_called_once_with(
        year=2026,
        semester=1,
        force_refresh=False,
    )


def test_brazil_anp_client_failure_returns_failure(tmp_path: Path):
    client = MagicMock()
    client.download.side_effect = RuntimeError("ANP offline")

    with patch(
        "worldenergydata.scheduler.jobs.brazil_anp_refresh.ANPClient",
        return_value=client,
    ):
        result = BrazilAnpRefreshJob().run(
            {"output_dir": str(tmp_path), "year": 2026, "semester": 1}
        )

    assert result.status == "failure"
    assert result.records_updated == 0
    assert "ANP offline" in (result.error_msg or "")


def test_brazil_anp_missing_output_dir_skips_without_network():
    with patch("worldenergydata.scheduler.jobs.brazil_anp_refresh.ANPClient") as client:
        result = BrazilAnpRefreshJob().run({"year": 2026, "semester": 1})

    assert result.status == "skipped"
    client.assert_not_called()
