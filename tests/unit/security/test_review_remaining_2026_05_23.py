"""Targeted regression tests for the remaining deterministic findings from the
2026-05-23 worldenergydata review report.

Each test pins behaviour for a surgical fix:
- SODIR: terminal API errors keep their status code / type (no degrade to generic).
- NUPRC: transient 5xx/429 are retried; 4xx raises immediately; UA header set.
- ANP: an HTML error page returned with HTTP 200 is NOT cached as ".csv".
- Mexico CNH: language + download prefs survive in a single merged prefs dict.
- Baker Hughes: non-date column headers are coerced/dropped, not fatal.

These mock the narrowest seam so they do not hit the network.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


# ── SODIR ──────────────────────────────────────────────────────────────────
class TestSodirErrorClassPreserved:
    def _client(self):
        from worldenergydata.sodir.api_client import SodirAPIClient

        c = SodirAPIClient(
            base_url="https://test.api", rate_limit=0, max_retries=3, retry_delay=0
        )
        c.cache_enabled = False
        return c

    def test_4xx_raises_immediately_with_status(self):
        from worldenergydata.sodir.errors import SodirAPIError

        c = self._client()
        resp = MagicMock()
        resp.status_code = 400
        resp.text = "Bad Request"
        with patch.object(c, "_make_request", return_value=resp) as m:
            with pytest.raises(SodirAPIError) as exc:
                c.get("/test")
        # 4xx is terminal: no retry, status code preserved.
        assert exc.value.status_code == 400
        assert m.call_count == 1

    def test_exhausted_5xx_keeps_status_code(self):
        from worldenergydata.sodir.errors import SodirAPIError

        c = self._client()
        resp = MagicMock()
        resp.status_code = 500
        resp.text = "Internal Server Error"
        with patch.object(c, "_make_request", return_value=resp) as m:
            with pytest.raises(SodirAPIError) as exc:
                c.get("/test")
        # Was degraded to a generic SodirAPIError(status_code=None) before fix.
        assert exc.value.status_code == 500
        assert m.call_count == 4  # initial + 3 retries

    def test_exhausted_429_raises_rate_limit_type(self):
        from worldenergydata.sodir.errors import SodirRateLimitError

        c = self._client()
        resp = MagicMock()
        resp.status_code = 429
        resp.headers = {"Retry-After": "0"}
        resp.text = "Rate limited"
        with patch.object(c, "_make_request", return_value=resp):
            with pytest.raises(SodirRateLimitError):
                c.get("/test")


# ── NUPRC ──────────────────────────────────────────────────────────────────
class TestNuprcRetry:
    @patch("worldenergydata.west_africa.nigeria.nuprc_client.requests")
    def test_5xx_is_retried_then_succeeds(self, mock_requests):
        from worldenergydata.west_africa.nigeria.nuprc_client import NuprcClient

        bad = MagicMock(status_code=503)
        good = MagicMock(status_code=200, content=b"%PDF ok")
        mock_requests.get.side_effect = [bad, good]

        client = NuprcClient(cache_enabled=False, max_retries=2)
        data = client.download_pdf("https://example.com/r.pdf")
        assert data == b"%PDF ok"
        assert mock_requests.get.call_count == 2

    @patch("worldenergydata.west_africa.nigeria.nuprc_client.requests")
    def test_4xx_raises_without_retry(self, mock_requests):
        from worldenergydata.west_africa.nigeria.nuprc_client import (
            NuprcAPIError,
            NuprcClient,
        )

        mock_requests.get.return_value = MagicMock(status_code=404)
        client = NuprcClient(cache_enabled=False, max_retries=2)
        with pytest.raises(NuprcAPIError):
            client.download_pdf("https://example.com/missing.pdf")
        assert mock_requests.get.call_count == 1  # no retry on 4xx

    @patch("worldenergydata.west_africa.nigeria.nuprc_client.requests")
    def test_user_agent_header_sent(self, mock_requests):
        from worldenergydata.west_africa.nigeria.nuprc_client import NuprcClient

        mock_requests.get.return_value = MagicMock(status_code=200, content=b"%PDF")
        client = NuprcClient(cache_enabled=False)
        client.download_pdf("https://example.com/r.pdf")
        _, kwargs = mock_requests.get.call_args
        assert "User-Agent" in kwargs.get("headers", {})


# ── ANP ────────────────────────────────────────────────────────────────────
class TestAnpCachePoisoning:
    @patch("worldenergydata.brazil_anp.production.anp_client.requests")
    def test_html_error_page_is_not_cached(self, mock_requests, tmp_path):
        from worldenergydata.brazil_anp.production.anp_client import ANPClient

        resp = MagicMock(status_code=200)
        resp.content = b"<!DOCTYPE html><html><body>Service unavailable</body></html>"
        resp.headers = {"Content-Type": "text/html"}
        resp.raise_for_status = MagicMock()
        mock_requests.get.return_value = resp

        client = ANPClient(cache_dir=str(tmp_path))
        with pytest.raises(ValueError):
            client.download(year=2023, semester=1)
        # Bad body must NOT have been written to the cache.
        assert client.is_cached(year=2023, semester=1) is False


# ── Mexico CNH prefs merge ─────────────────────────────────────────────────
class TestSihPrefsMerge:
    def test_prefs_merged_into_single_call(self):
        import inspect

        from worldenergydata.mexico_cnh.scrapers import sih_scraper

        src = inspect.getsource(sih_scraper.SIHScraper._create_chrome_options)
        # Strip comment lines so commentary mentioning "prefs" is not counted.
        code = "\n".join(
            ln for ln in src.splitlines() if not ln.lstrip().startswith("#")
        )
        # Exactly one prefs experimental option call (merged), not two clobbering
        # calls — the second of two would silently drop intl.accept_languages.
        assert code.count('"prefs"') == 1
        assert "intl.accept_languages" in code
        assert "download.default_directory" in code


# ── Baker Hughes non-date headers ──────────────────────────────────────────
class TestBakerHughesNonDateHeaders:
    def test_total_column_does_not_abort_load(self, tmp_path):
        from worldenergydata.baker_hughes import loader

        df = pd.DataFrame(
            {
                "State": ["Texas", "Louisiana"],
                "2024-01-05": [100, 50],
                "2024-01-12": [102, 51],
                "Total": [202, 101],  # non-date header
            }
        )
        path = tmp_path / "summary.xlsx"
        df.to_excel(path, index=False, sheet_name="Summary")

        out = loader.load_summary(path, sheet_name="Summary")
        # 2 states x 2 real date columns = 4 rows; the "Total" column is dropped.
        assert len(out) == 4
        assert out["date"].notna().all()
