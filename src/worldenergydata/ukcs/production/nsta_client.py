"""NSTA production downloader with local cache and year/field parameters.

Data source: official UKCS Transition ArcGIS PPRS production points service
  https://services-eu1.arcgis.com/OZMfUznmLTnWccBc/arcgis/rest/services/UKCS_hydrocarbon_field_production_reports_PPRS_points_(WGS84)/FeatureServer/0

The NSTA Hub CSV download redirects to this FeatureServer export. The default
uses the pageable FeatureServer query endpoint and caches rows as CSV locally.
"""

import io
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = (
    "https://services-eu1.arcgis.com/OZMfUznmLTnWccBc/arcgis/rest/services/"
    "UKCS_hydrocarbon_field_production_reports_PPRS_points_(WGS84)/"
    "FeatureServer/0/query"
)


class NSTAClient:
    """Download and cache NSTA field-production CSVs by year and dataset type."""

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
    ):
        if cache_dir is None:
            cache_dir = str(Path(__file__).resolve().parents[1] / "data")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = base_url

    def _cache_key(self, year: int, dataset: str = "monthly") -> str:
        return f"nsta_production_{year}_{dataset}.csv"

    def is_cached(self, year: int, dataset: str = "monthly") -> bool:
        return (self.cache_dir / self._cache_key(year, dataset)).exists()

    def load_cached(
        self,
        year: int,
        dataset: str = "monthly",
        encoding: str = "utf-8",
    ) -> pd.DataFrame:
        path = self.cache_dir / self._cache_key(year, dataset)
        return pd.read_csv(path, encoding=encoding)

    def download(
        self,
        year: int,
        dataset: str = "monthly",
        force_refresh: bool = False,
        encoding: str = "utf-8",
        max_records: int | None = None,
    ) -> pd.DataFrame:
        """Download NSTA production data for a given year/dataset."""
        if not force_refresh and self.is_cached(year, dataset):
            logger.info("Using cached NSTA data for %d (%s)", year, dataset)
            return self.load_cached(year, dataset, encoding=encoding)

        if requests is None:
            raise RuntimeError(
                "requests library required for downloads — "
                "install with: pip install requests"
            )

        url = self._build_url(year, dataset)
        logger.info("Downloading NSTA data from %s", url)

        if _is_arcgis_query_url(url):
            return self._download_arcgis_query(
                url=url,
                year=year,
                dataset=dataset,
                max_records=max_records,
            )

        response = requests.get(url, timeout=60)
        response.raise_for_status()

        cache_path = self.cache_dir / self._cache_key(year, dataset)
        cache_path.write_bytes(response.content)

        return pd.read_csv(io.BytesIO(response.content), encoding=encoding)

    def _build_url(self, year: int, dataset: str) -> str:
        return self.base_url.format(year=year, dataset=dataset)

    def _download_arcgis_query(
        self,
        url: str,
        year: int,
        dataset: str,
        max_records: int | None,
    ) -> pd.DataFrame:
        rows = []
        offset = 0
        page_size = min(max_records or 2000, 2000)
        while True:
            remaining = None if max_records is None else max_records - len(rows)
            if remaining is not None and remaining <= 0:
                break
            record_count = page_size if remaining is None else min(page_size, remaining)
            response = requests.get(
                url,
                params={
                    "where": f"PERIODYR = '{year}'",
                    "outFields": "*",
                    "returnGeometry": "false",
                    "resultOffset": offset,
                    "resultRecordCount": record_count,
                    "f": "json",
                },
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
            page_rows = [
                feature["attributes"]
                for feature in payload.get("features", [])
                if isinstance(feature, dict)
                and isinstance(feature.get("attributes"), dict)
            ]
            rows.extend(page_rows)
            if not payload.get("exceededTransferLimit") or not page_rows:
                break
            offset += record_count
        df = pd.DataFrame(rows)
        cache_path = self.cache_dir / self._cache_key(year, dataset)
        df.to_csv(cache_path, index=False)
        return df


def _is_arcgis_query_url(url: str) -> bool:
    return "/query" in url and "arcgis/rest/services" in url
