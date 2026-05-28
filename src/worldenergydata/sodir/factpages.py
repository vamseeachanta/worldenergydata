"""
SODIR Factpages tableview CSV client (demo-ready live path).

The legacy :class:`worldenergydata.sodir.api_client.SodirAPIClient` targets the
``factmaps.sodir.no`` DataService endpoint, which currently returns HTTP 400
``Invalid URL``.  SODIR publishes the same public Norwegian Continental Shelf
datasets as downloadable CSV "tableview" reports under ``factpages.sodir.no``,
and those endpoints are live and stable (verified 2026-05-28).

This module fetches those CSV reports into pandas DataFrames with an on-disk
snapshot cache, so analysis stays reproducible offline -- e.g. during a live
demo where the external network may be slow or blocked.  The live fetch is
preferred when ``refresh=True``; otherwise a cached snapshot is used when
present, and the snapshot is also the fallback if a live fetch fails.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Dict

import pandas as pd

try:
    import requests
except ImportError:  # pragma: no cover - exercised only without requests
    requests = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

FACTPAGES_BASE = "https://factpages.sodir.no/public"

# Curated tableview reports confirmed live against SODIR on 2026-05-28.
# Maps a friendly key -> the SODIR tableview report name.
REPORTS: Dict[str, str] = {
    "fields": "field",
    "field_production_yearly": "field_production_yearly",
    "wellbores_development": "wellbore_development_all",
    "discoveries": "discovery",
}

# Snapshots live under the standard module data directory so they are tracked
# and reproducible (matches the bsee data/modules/<module> convention).
DEFAULT_CACHE_DIR = Path("data/modules/sodir")


def tableview_url(report: str) -> str:
    """Build the SODIR factpages CSV export URL for a tableview report."""
    return (
        f"{FACTPAGES_BASE}?/Factpages/external/tableview/{report}"
        "&rs:Command=Render&rc:Toolbar=false&rc:Parameters=f"
        "&IpAddress=not_used&CultureCode=en&rs:Format=CSV"
    )


def _parse_csv(text: str) -> pd.DataFrame:
    """Parse a SODIR CSV body, rejecting HTML error pages.

    SODIR answers an unknown/failed report with an HTTP 500 HTML page rather
    than a CSV body; guard against silently parsing that as data.
    """
    head = text.lstrip()[:64].lower()
    if head.startswith("<html") or head.startswith("<!doctype"):
        raise ValueError("SODIR returned an HTML error page, not CSV data")
    # encoding handled by caller; SODIR prefixes a UTF-8 BOM on the header.
    return pd.read_csv(io.StringIO(text))


def fetch_report(
    report_key: str,
    *,
    cache_dir: Path | str = DEFAULT_CACHE_DIR,
    refresh: bool = False,
    timeout: int = 30,
) -> pd.DataFrame:
    """Fetch a SODIR tableview report as a DataFrame.

    Args:
        report_key: A key from :data:`REPORTS` (e.g. ``"fields"``).
        cache_dir: Directory holding ``<report_key>.csv`` snapshots.
        refresh: When True, fetch live and overwrite the snapshot.  When False
            (default), a present snapshot is used without any network call.
        timeout: Per-request timeout in seconds for the live fetch.

    Returns:
        The report as a pandas DataFrame.

    Raises:
        KeyError: If ``report_key`` is unknown.
        RuntimeError: If no cached snapshot exists and the live fetch fails
            (or ``requests`` is unavailable).
    """
    if report_key not in REPORTS:
        raise KeyError(
            f"Unknown SODIR report '{report_key}'. Known: {sorted(REPORTS)}"
        )

    cache_dir = Path(cache_dir)
    cache_path = cache_dir / f"{report_key}.csv"

    # Offline / default path: use the snapshot when we are not refreshing.
    if not refresh and cache_path.exists():
        logger.info("Loading SODIR '%s' from snapshot %s", report_key, cache_path)
        return pd.read_csv(cache_path, encoding="utf-8-sig")

    # Live path.
    url = tableview_url(REPORTS[report_key])
    if requests is not None:
        try:
            logger.info("Fetching SODIR '%s' live from %s", report_key, url)
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            resp.encoding = "utf-8-sig"
            df = _parse_csv(resp.text)
            cache_dir.mkdir(parents=True, exist_ok=True)
            df.to_csv(cache_path, index=False)
            logger.info(
                "Fetched %d rows for SODIR '%s'; snapshot -> %s",
                len(df),
                report_key,
                cache_path,
            )
            return df
        except Exception as exc:  # noqa: BLE001 - fall back to snapshot below
            logger.warning("Live SODIR fetch for '%s' failed: %s", report_key, exc)

    if cache_path.exists():
        logger.info("Falling back to SODIR '%s' snapshot %s", report_key, cache_path)
        return pd.read_csv(cache_path, encoding="utf-8-sig")

    raise RuntimeError(
        f"Could not load SODIR '{report_key}': live fetch failed and no "
        f"snapshot exists at {cache_path}."
    )


def fetch_fields(**kwargs) -> pd.DataFrame:
    """NCS field overview: name, operator, area, hydrocarbon type, status."""
    return fetch_report("fields", **kwargs)


def fetch_field_production_yearly(**kwargs) -> pd.DataFrame:
    """Per-field, per-year NCS production (oil/gas/NGL/condensate, MillSm3)."""
    return fetch_report("field_production_yearly", **kwargs)
