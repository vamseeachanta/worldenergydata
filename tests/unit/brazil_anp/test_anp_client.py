"""Tests for official ANP production-by-well direct-source client."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from worldenergydata.brazil_anp.production.anp_client import ANPClient


def _official_anp_csv(
    *,
    field: str,
    well: str,
    period: str = "2023/01",
    oil: str = "1.000,5000",
    gas_total: str = "5,5000",
) -> str:
    """Small structurally faithful ANP CSV: two useful header rows + blank row."""
    return (
        "Estado;Bacia;Nome Poço;;Campo;Operador;Número do Contrato;Período;"
        "Óleo (bbl/dia);Condensado (bbl/dia);Petróleo (bbl/dia);"
        "Gás Natural (Mm³/dia);;;Volume Gás Royalties (Mm³/dia);"
        "Água (bbl/dia)\n"
        ";;ANP;Operador;;;;;;;;Associado;Não Associado;Gás Total;;\n"
        ";;;;;;;;;;;;;;;\n"
        f"Rio de Janeiro;Santos;{well};{well};{field};Petrobras;"
        f"480000000000000;{period};{oil};10,0000;1.010,5000;"
        f"2,0000;3,0000;{gas_total};4,0000;20,2500\n"
    )


def _zip_bytes(entries: dict[str, str]) -> bytes:
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        for name, text in entries.items():
            archive.writestr(name, text.encode("utf-8-sig"))
    return payload.getvalue()


def _partition_zip(*, duplicate: bool = False) -> bytes:
    mar = _official_anp_csv(field="TUPI", well="7-TUPI-1")
    presal = _official_anp_csv(
        field="TUPI" if duplicate else "BUZIOS",
        well="7-TUPI-1" if duplicate else "7-BUZ-1",
    )
    terra = _official_anp_csv(field="MOSSORO", well="7-MOS-1")
    return _zip_bytes(
        {
            "2023_01_producao_Mar.csv": mar,
            "2023_01_producao_Presal.csv": presal,
            "2023_01_producao_Terra.csv": terra,
        }
    )


class TestANPClientInit:
    def test_default_cache_dir(self, tmp_path):
        client = ANPClient(cache_dir=str(tmp_path))
        assert client.cache_dir == Path(tmp_path)

    def test_creates_cache_dir(self, tmp_path):
        cache = tmp_path / "anp_cache"
        ANPClient(cache_dir=str(cache))
        assert cache.exists()

    def test_default_base_url_is_official_gov_br_source(self, tmp_path):
        client = ANPClient(cache_dir=str(tmp_path))
        assert "www.gov.br/anp" in client.base_url
        assert "cdp_apex" not in client.base_url
        assert "consulta-producao-por-poco" not in client.base_url


class TestANPClientMonthCache:
    def test_cache_key_includes_year_and_month(self, tmp_path):
        client = ANPClient(cache_dir=str(tmp_path))
        key = client._cache_key(year=2023, month=1)
        assert key == "anp_production_2023_01.zip"

    def test_cache_key_different_for_different_months(self, tmp_path):
        client = ANPClient(cache_dir=str(tmp_path))
        assert client._cache_key(year=2023, month=1) != client._cache_key(
            year=2023,
            month=2,
        )

    def test_is_cached_returns_false_when_missing(self, tmp_path):
        client = ANPClient(cache_dir=str(tmp_path))
        assert client.is_cached(year=2023, month=1) is False

    def test_is_cached_returns_true_when_zip_present(self, tmp_path):
        client = ANPClient(cache_dir=str(tmp_path))
        (tmp_path / client._cache_key(year=2023, month=1)).write_bytes(
            _partition_zip()
        )
        assert client.is_cached(year=2023, month=1) is True

    def test_load_cached_monthly_zip(self, tmp_path):
        client = ANPClient(cache_dir=str(tmp_path))
        (tmp_path / client._cache_key(year=2023, month=1)).write_bytes(
            _partition_zip()
        )

        df = client.load_cached(year=2023, month=1)

        assert isinstance(df, pd.DataFrame)
        assert set(df["location_source"]) == {"mar", "presal", "terra"}
        assert "Nome Poço ANP" in df.columns
        assert "Gás Natural (Mm³/dia) Gás Total" in df.columns


class TestANPClientDownloadMonth:
    @patch("worldenergydata.brazil_anp.production.anp_client.requests")
    def test_download_month_uses_official_gov_br_zip_url(self, mock_requests, tmp_path):
        client = ANPClient(cache_dir=str(tmp_path))
        mock_response = MagicMock()
        mock_response.content = _partition_zip()
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        df = client.download_month(year=2023, month=1)

        called_url = mock_requests.get.call_args.args[0]
        assert "www.gov.br/anp" in called_url
        assert "/2023/producao-01.zip" in called_url
        assert "cdp_apex" not in called_url
        assert len(df) == 3
        assert (tmp_path / "anp_production_2023_01.zip").exists()

    @patch("worldenergydata.brazil_anp.production.anp_client.requests")
    def test_download_month_uses_cache_when_available(
        self,
        mock_requests,
        tmp_path,
    ):
        client = ANPClient(cache_dir=str(tmp_path))
        (tmp_path / client._cache_key(year=2023, month=1)).write_bytes(
            _partition_zip()
        )

        df = client.download_month(year=2023, month=1)

        mock_requests.get.assert_not_called()
        assert len(df) == 3

    @patch("worldenergydata.brazil_anp.production.anp_client.requests")
    def test_force_refresh_replaces_cache(self, mock_requests, tmp_path):
        client = ANPClient(cache_dir=str(tmp_path))
        (tmp_path / client._cache_key(year=2023, month=1)).write_bytes(
            _partition_zip()
        )
        mock_response = MagicMock()
        mock_response.content = _partition_zip()
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        client.download_month(year=2023, month=1, force_refresh=True)

        mock_requests.get.assert_called_once()

    @patch("worldenergydata.brazil_anp.production.anp_client.requests")
    def test_presal_overlap_with_mar_is_deduplicated_to_presal_source(
        self,
        mock_requests,
        tmp_path,
    ):
        client = ANPClient(cache_dir=str(tmp_path))
        mock_response = MagicMock()
        mock_response.content = _partition_zip(duplicate=True)
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        df = client.download_month(year=2023, month=1, force_refresh=True)

        tupi = df[df["Campo"] == "TUPI"]
        assert len(tupi) == 1
        assert tupi.iloc[0]["location_source"] == "presal"
        assert len(df) == 2
