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

        content = response.content
        # ANP frequently returns an HTML error/maintenance page with HTTP 200.
        # Detect it and refuse to poison the cache with a bad ".csv" file that
        # subsequent is_cached()/load_cached() calls would keep returning.
        leading = content[:512].lstrip().lower()
        content_type = response.headers.get("Content-Type", "").lower()
        if (
            leading.startswith(b"<!doctype html")
            or leading.startswith(b"<html")
            or ("html" in content_type and "csv" not in content_type)
        ):
            raise ValueError(
                f"ANP returned an HTML page (not CSV) for {year}-S{semester}; "
                "refusing to cache. URL may be down or the report is unavailable."
            )

        # Parse BEFORE caching so an unparseable body never lands in the cache.
        df = pd.read_csv(io.BytesIO(content), sep=";", encoding=encoding)

        cache_path = self.cache_dir / self._cache_key(year, semester)
        tmp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
        tmp_path.write_bytes(content)
        tmp_path.replace(cache_path)

        return df

    def _build_url(self, year: int, semester: int) -> str:
        return f"{self.base_url}?year={year}&semester={semester}"
