"""NSTA CSV downloader with local cache and year/field parameters.

Data source: NSTA Open Data / data.gov.uk
  https://opendata-nstauthority.hub.arcgis.com/datasets/NSTAUTHORITY::nsta-field-production-pprs-wgs84

Field production CSVs are freely downloadable with no authentication.
CSV format: FieldName, Year, Month, OilProduction (Thousand Tonnes),
            GasProduction (MMscf), WaterProduction (Thousand Tonnes)
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
    "https://opendata-nstauthority.hub.arcgis.com/api/download/v1/"
    "items/ba8b7b78d3a74edc88293011981ce2d7/csv?layers=0"
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
    ) -> pd.DataFrame:
        """Download NSTA CSV for a given year/dataset, using cache when available."""
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

        response = requests.get(url, timeout=60)
        response.raise_for_status()

        cache_path = self.cache_dir / self._cache_key(year, dataset)
        cache_path.write_bytes(response.content)

        return pd.read_csv(io.BytesIO(response.content), encoding=encoding)

    def _build_url(self, year: int, dataset: str) -> str:
        return self.base_url.format(year=year, dataset=dataset)
