"""Tests for the Brazil ANP monthly refresh job."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from worldenergydata.scheduler.jobs.brazil_anp_refresh import BrazilAnpRefreshJob


def _raw_anp_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Estado": "Rio de Janeiro",
                "Bacia": "Santos",
                "Nome Poço ANP": "7-TUPI-1",
                "Campo": "TUPI",
                "Operador": "Petrobras",
                "Ambiente": "Mar",
                "Período": "2026/01",
                "Óleo (bbl/dia)": "10,0",
                "Condensado (bbl/dia)": "1,0",
                "Gás Natural (Mm³/dia) Gás Total": "2,0",
                "Água (bbl/dia)": "3,0",
                "location_source": "presal",
            }
        ]
    )


def test_brazil_anp_downloads_configured_month_and_writes_outputs(tmp_path: Path):
    client = MagicMock()
    client.download_month.return_value = _raw_anp_df()

    with patch(
        "worldenergydata.scheduler.jobs.brazil_anp_refresh.ANPClient",
        return_value=client,
    ):
        result = BrazilAnpRefreshJob().run(
            {
                "output_dir": str(tmp_path),
                "year": 2026,
                "month": 1,
                "force_refresh": True,
            }
        )

    assert result.status == "success"
    assert result.records_updated == 1
    client.download_month.assert_called_once_with(
        year=2026,
        month=1,
        force_refresh=True,
    )
    client.download.assert_not_called()
    assert (tmp_path / "raw" / "anp_production_2026_01.parquet").exists()
    normalized_path = tmp_path / "anp_production_2026_01.parquet"
    assert normalized_path.exists()
    normalized = pd.read_parquet(normalized_path)
    assert normalized.loc[0, "field"] == "TUPI"
    assert normalized.loc[0, "oil_bbl"] > 0


def test_brazil_anp_defaults_to_latest_completed_month(tmp_path: Path):
    client = MagicMock()
    client.download_month.return_value = _raw_anp_df()

    with (
        patch(
            "worldenergydata.scheduler.jobs.brazil_anp_refresh.ANPClient",
            return_value=client,
        ),
        patch("worldenergydata.scheduler.jobs.brazil_anp_refresh.datetime") as dt,
    ):
        dt.now.return_value = pd.Timestamp("2026-08-15").to_pydatetime()
        result = BrazilAnpRefreshJob().run({"output_dir": str(tmp_path)})

    assert result.status == "success"
    client.download_month.assert_called_once_with(
        year=2026,
        month=6,
        force_refresh=False,
    )


def test_legacy_semester_config_uses_monthly_api_not_stale_cdp(tmp_path: Path):
    client = MagicMock()
    client.download_month.return_value = _raw_anp_df()

    with patch(
        "worldenergydata.scheduler.jobs.brazil_anp_refresh.ANPClient",
        return_value=client,
    ):
        result = BrazilAnpRefreshJob().run(
            {"output_dir": str(tmp_path), "year": 2026, "semester": 1}
        )

    assert result.status == "success"
    client.download_month.assert_called_once_with(
        year=2026,
        month=6,
        force_refresh=False,
    )
    client.download.assert_not_called()


def test_brazil_anp_client_failure_returns_failure(tmp_path: Path):
    client = MagicMock()
    client.download_month.side_effect = RuntimeError("ANP offline")

    with patch(
        "worldenergydata.scheduler.jobs.brazil_anp_refresh.ANPClient",
        return_value=client,
    ):
        result = BrazilAnpRefreshJob().run(
            {"output_dir": str(tmp_path), "year": 2026, "month": 1}
        )

    assert result.status == "failure"
    assert result.records_updated == 0
    assert "ANP offline" in (result.error_msg or "")


def test_brazil_anp_missing_output_dir_skips_without_network():
    with patch("worldenergydata.scheduler.jobs.brazil_anp_refresh.ANPClient") as client:
        result = BrazilAnpRefreshJob().run({"year": 2026, "month": 1})

    assert result.status == "skipped"
    client.assert_not_called()
