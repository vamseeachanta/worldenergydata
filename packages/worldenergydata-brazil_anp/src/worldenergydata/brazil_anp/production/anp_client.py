"""ANP production-by-well downloader using official monthly gov.br ZIP files."""

import io
import logging
from pathlib import Path
from typing import Optional
import zipfile

import pandas as pd

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = (
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/"
    "arquivos/arquivos-producao-de-petroleo-e-gas-natural-por-poco"
)


class ANPClient:
    """Download and cache ANP well-production ZIPs by year/month."""

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

    def _cache_key(self, year: int, month: int) -> str:
        return f"anp_production_{year}_{month:02d}.zip"

    def is_cached(self, year: int, month: int) -> bool:
        return (self.cache_dir / self._cache_key(year, month)).exists()

    def load_cached(
        self,
        year: int,
        month: int,
        encoding: str = "utf-8-sig",
    ) -> pd.DataFrame:
        path = self.cache_dir / self._cache_key(year, month)
        return self._read_zip(path.read_bytes(), encoding=encoding)

    def download_month(
        self,
        year: int,
        month: int,
        force_refresh: bool = False,
        encoding: str = "utf-8-sig",
    ) -> pd.DataFrame:
        """Download one official ANP production-by-well month."""
        if not force_refresh and self.is_cached(year, month):
            logger.info("Using cached ANP data for %04d-%02d", year, month)
            return self.load_cached(year, month, encoding=encoding)

        if requests is None:
            raise RuntimeError("requests library required for downloads")

        url = self._build_month_url(year, month)
        logger.info("Downloading ANP data from %s", url)

        response = requests.get(url, timeout=60)
        response.raise_for_status()

        cache_path = self.cache_dir / self._cache_key(year, month)
        cache_path.write_bytes(response.content)
        return self._read_zip(response.content, encoding=encoding)

    def download(
        self,
        year: int,
        semester: int,
        force_refresh: bool = False,
        encoding: str = "utf-8-sig",
    ) -> pd.DataFrame:
        """Compatibility wrapper that concatenates the months in a semester."""
        if semester not in (1, 2):
            raise ValueError("semester must be 1 or 2")

        start = 1 if semester == 1 else 7
        frames = [
            self.download_month(
                year=year,
                month=month,
                force_refresh=force_refresh,
                encoding=encoding,
            )
            for month in range(start, start + 6)
        ]
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    def _build_month_url(self, year: int, month: int) -> str:
        if not 1 <= int(month) <= 12:
            raise ValueError("month must be in 1..12")
        return f"{self.base_url}/{year}/producao-{month:02d}.zip"

    def _build_url(self, year: int, month: int) -> str:
        """Backward-compatible alias for the official monthly URL builder."""
        return self._build_month_url(year, month)

    def _read_zip(self, payload: bytes, encoding: str = "utf-8-sig") -> pd.DataFrame:
        frames = []
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            for name in sorted(archive.namelist()):
                if not name.lower().endswith(".csv"):
                    continue
                with archive.open(name) as fh:
                    frame = self._read_partition_csv(fh, encoding=encoding)
                frame["location_source"] = _location_source_from_name(name)
                frames.append(frame)

        if not frames:
            return pd.DataFrame()

        df = pd.concat(frames, ignore_index=True)
        return _deduplicate_expected_overlaps(df)

    @staticmethod
    def _read_partition_csv(handle, encoding: str = "utf-8-sig") -> pd.DataFrame:
        df = pd.read_csv(
            handle,
            sep=";",
            encoding=encoding,
            header=[0, 1],
            skiprows=[2],
            dtype=str,
        )
        df.columns = _flatten_anp_columns(df.columns)
        df = df.dropna(how="all")
        if "Período" in df.columns:
            periods = df["Período"].astype(str)
            df = df[periods.str.contains(r"\d{4}[/\-]\d{2}", na=False)]
        return df.reset_index(drop=True)


def _flatten_anp_columns(columns) -> list[str]:
    flattened = []
    current_top = ""
    for top, sub in columns:
        top_text = "" if str(top).startswith("Unnamed") else str(top).strip()
        sub_text = "" if str(sub).startswith("Unnamed") else str(sub).strip()
        if top_text:
            current_top = top_text
        base = top_text or current_top
        if sub_text and sub_text.lower() != base.lower():
            flattened.append(f"{base} {sub_text}".strip())
        else:
            flattened.append(base.strip())
    return flattened


def _location_source_from_name(name: str) -> str:
    normalized = name.lower()
    if "presal" in normalized or "pre-sal" in normalized:
        return "presal"
    if "terra" in normalized:
        return "terra"
    if "mar" in normalized:
        return "mar"
    return "unknown"


def _deduplicate_expected_overlaps(df: pd.DataFrame) -> pd.DataFrame:
    keys = ["Campo", "Nome Poço ANP", "Período"]
    if any(key not in df.columns for key in keys):
        return df
    duplicated = df.duplicated(keys, keep=False)
    if not duplicated.any():
        return df

    duplicate_groups = df.loc[duplicated].groupby(keys, dropna=False)
    unexpected = []
    for _, group in duplicate_groups:
        sources = set(group["location_source"].dropna().astype(str))
        if not sources <= {"mar", "presal"} or sources != {"mar", "presal"}:
            unexpected.append(group)

    if unexpected:
        sample = pd.concat(unexpected, ignore_index=True)
        sample = sample.loc[:, keys + ["location_source"]].head(5)
        raise ValueError(
            "unexpected duplicate ANP production keys across partitions: "
            f"{sample.to_dict(orient='records')}"
        )

    priority = df["location_source"].map({"presal": 0, "terra": 1, "mar": 2})
    deduped = (
        df.assign(_location_priority=priority.fillna(9))
        .sort_values(keys + ["_location_priority"])
        .drop_duplicates(keys, keep="first")
        .drop(columns=["_location_priority"])
        .sort_index()
        .reset_index(drop=True)
    )
    return deduped
