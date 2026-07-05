"""Live CORES workbook download and cache support for Spain production (#806)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Mapping, Optional

import pandas as pd

from worldenergydata.spain.production.cores_loader import (
    GWH_TO_MCF,
    TONNES_TO_BBL,
    CoresProductionLoader,
)
from worldenergydata.spain.production.cores_source import (
    DEFAULT_WORKBOOKS,
    STATISTICS_PAGE_URL,
    CoresHttpResponse,
    CoresSourceError,
    CoresWorkbook,
    CoresWorkbookSource,
    utc_now_iso,
)

__all__ = [
    "DEFAULT_WORKBOOKS",
    "STATISTICS_PAGE_URL",
    "CoresHttpResponse",
    "CoresLiveProductionLoader",
    "CoresSourceError",
    "CoresWorkbook",
    "CoresWorkbookSource",
    "FixtureRefreshResult",
    "refresh_ayoluengo_fixture",
]


@dataclass(frozen=True)
class FixtureRefreshResult:
    """Paths written by ``refresh_ayoluengo_fixture``."""

    sample_path: Path
    metadata_path: Path


class CoresLiveProductionLoader:
    """Loader facade over downloaded CORES oil and gas workbooks."""

    def __init__(
        self,
        *,
        cache_root: Path,
        source: Optional[CoresWorkbookSource] = None,
        header_row: int = 5,
        sheet_name: str = "Production",
    ):
        self.cache_root = Path(cache_root)
        self.source = source or CoresWorkbookSource(cache_root=self.cache_root)
        self.raw_dir = self.cache_root / "raw"
        self.normalized_dir = self.cache_root / "normalized"
        self.header_row = header_row
        self.sheet_name = sheet_name

    def refresh(self, *, force_refresh: bool = False) -> dict[str, Any]:
        self.source.download_all(force_refresh=force_refresh, validate_links=True)
        self.load_all_production()
        return self.metadata()

    def load_oil_production(self) -> pd.DataFrame:
        return self._load_product("oil")

    def load_gas_production(self) -> pd.DataFrame:
        return self._load_product("gas")

    def load_all_production(self) -> pd.DataFrame:
        keys = ["field_name", "year", "month"]
        oil = self.load_oil_production()
        gas = self.load_gas_production()
        merged = oil.merge(gas, how="outer", on=keys)
        return self._write_normalized("all", merged)

    def load_field_production(self, field_name: str) -> pd.DataFrame:
        frame = self.load_all_production()
        mask = frame["field_name"].astype(str).str.lower() == field_name.lower()
        return frame[mask].copy()

    def metadata(self) -> dict[str, Any]:
        return self.source.metadata()

    def _load_product(self, product: str) -> pd.DataFrame:
        workbook = DEFAULT_WORKBOOKS[product]
        path = self.raw_dir / workbook.filename
        if not path.exists():
            path = self.source.download(product)
        frame = CoresProductionLoader(
            product=product,
            path=path,
            header_row=self.header_row,
            sheet_name=self.sheet_name,
        ).load()
        return self._write_normalized(product, frame)

    def _write_normalized(self, name: str, frame: pd.DataFrame) -> pd.DataFrame:
        self.normalized_dir.mkdir(parents=True, exist_ok=True)
        out = _sort_production(frame)
        out.to_csv(self.normalized_dir / f"cores_{name}_production.csv", index=False)
        return out


def refresh_ayoluengo_fixture(
    *,
    oil_frame: pd.DataFrame,
    metadata: Mapping[str, Any],
    output_dir: Optional[Path] = None,
    refreshed_at_utc: Optional[str] = None,
    sample_rows: int = 6,
) -> FixtureRefreshResult:
    """Refresh the small committed Ayoluengo fixture from live oil output."""

    output = Path(output_dir) if output_dir is not None else _package_cores_data_dir()
    sample = _ayoluengo_sample(oil_frame, sample_rows)
    output.mkdir(parents=True, exist_ok=True)
    sample_path = output / "ayoluengo_oil_sample.csv"
    metadata_path = output / "_metadata.json"
    sample.to_csv(sample_path, index=False)
    metadata_path.write_text(
        json.dumps(
            _fixture_metadata(metadata, len(sample), refreshed_at_utc),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return FixtureRefreshResult(sample_path=sample_path, metadata_path=metadata_path)


def _ayoluengo_sample(oil_frame: pd.DataFrame, sample_rows: int) -> pd.DataFrame:
    mask = oil_frame["field_name"].astype(str).str.lower() == "ayoluengo"
    sample = _sort_production(oil_frame[mask].copy()).head(sample_rows)
    if sample.empty:
        raise CoresSourceError("live oil frame contains no Ayoluengo rows")
    if "gas_mcf" not in sample.columns:
        sample["gas_mcf"] = 0.0
    return sample[["field_name", "year", "month", "oil_bbl", "gas_mcf"]]


def _fixture_metadata(
    source_metadata: Mapping[str, Any],
    sample_row_count: int,
    refreshed_at_utc: Optional[str],
) -> dict[str, Any]:
    workbooks = dict(source_metadata.get("workbooks", {}))
    oil = dict(workbooks.get("oil", {}))
    refreshed = refreshed_at_utc or utc_now_iso()
    return {
        "source_name": DEFAULT_WORKBOOKS["oil"].dataset_name,
        "source_url": oil.get("source_url", DEFAULT_WORKBOOKS["oil"].source_url),
        "statistics_page": source_metadata.get("statistics_page", STATISTICS_PAGE_URL),
        "source_updated_date": _source_updated_date(oil),
        "sample_extracted_date": refreshed[:10],
        "sample_field": "Ayoluengo",
        "sample_row_count": sample_row_count,
        "source_unit": DEFAULT_WORKBOOKS["oil"].source_unit,
        "normalized_unit": "bbl",
        "conversion": f"oil_bbl = tonnes * {TONNES_TO_BBL}",
        "conversion_factors": {
            "gas_gwh_to_mcf": GWH_TO_MCF,
            "oil_tonnes_to_bbl": TONNES_TO_BBL,
        },
        "license_note": (
            "CORES attribution required; cite source URL and latest-update date."
        ),
        "workbooks": workbooks,
    }


def _source_updated_date(oil_metadata: Mapping[str, Any]) -> Optional[str]:
    last_modified = oil_metadata.get("last_modified")
    if not last_modified:
        return oil_metadata.get("source_updated_date")
    try:
        return parsedate_to_datetime(last_modified).date().isoformat()
    except (TypeError, ValueError):
        return oil_metadata.get("source_updated_date")


def _sort_production(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sort_values(["field_name", "year", "month"]).reset_index(drop=True)


def _package_cores_data_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "cores"
