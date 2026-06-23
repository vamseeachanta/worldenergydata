"""ANP CSV downloader with semester/year parameters and local cache."""

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
    "https://cdp.anp.gov.br/ords/r/cdp_apex/"
    "consulta-dados-publicos-cdp/consulta-producao-por-poco"
)


class ANPClient:
    """Download and cache ANP well-production CSVs by semester/year."""

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

    def _cache_key(self, year: int, semester: int) -> str:
        return f"anp_production_{year}_s{semester}.csv"

    def is_cached(self, year: int, semester: int) -> bool:
        return (self.cache_dir / self._cache_key(year, semester)).exists()

    def load_cached(
        self,
        year: int,
        semester: int,
        encoding: str = "latin-1",
    ) -> pd.DataFrame:
        path = self.cache_dir / self._cache_key(year, semester)
        return pd.read_csv(path, sep=";", encoding=encoding)

    def download(
        self,
        year: int,
        semester: int,
        force_refresh: bool = False,
        encoding: str = "latin-1",
    ) -> pd.DataFrame:
        """Download ANP CSV for a given year/semester, using cache when available."""
        if not force_refresh and self.is_cached(year, semester):
            logger.info("Using cached data for %d-S%d", year, semester)
            return self.load_cached(year, semester, encoding=encoding)

        if requests is None:
            raise RuntimeError("requests library required for downloads")

        url = self._build_url(year, semester)
        logger.info("Downloading ANP data from %s", url)

        response = requests.get(url, timeout=60)
        response.raise_for_status()

        cache_path = self.cache_dir / self._cache_key(year, semester)
        cache_path.write_bytes(response.content)

        return pd.read_csv(io.BytesIO(response.content), sep=";", encoding=encoding)

    def _build_url(self, year: int, semester: int) -> str:
        return f"{self.base_url}?year={year}&semester={semester}"
