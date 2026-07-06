"""Live CORES workbook download and cache support for Spain production (#806)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, cast

import pandas as pd

from worldenergydata.spain.production.cores_loader import (
    GWH_TO_MCF,
    TONNES_TO_BBL,
    CoresProductionLoader,
)
from worldenergydata.spain.production.cores_density import (
    CoresCrudeDensityFactor,
    CoresOilConversionAudit,
    DEFAULT_OIL_BBL_PER_TONNE,
    build_oil_conversion_audit,
    load_crude_density_factors,
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
        oil_density_registry_path: Optional[Path] = None,
        allow_default_density: bool = False,
    ):
        self.cache_root = Path(cache_root)
        self.source = source or CoresWorkbookSource(cache_root=self.cache_root)
        self.raw_dir = self.cache_root / "raw"
        self.normalized_dir = self.cache_root / "normalized"
        self.header_row = header_row
        self.sheet_name = sheet_name
        self.oil_density_registry_path = (
            Path(oil_density_registry_path)
            if oil_density_registry_path is not None
            else _default_density_registry_path()
        )
        if not isinstance(allow_default_density, bool):
            raise ValueError("allow_default_density must be boolean")
        self.allow_default_density = allow_default_density
        self.oil_conversion_audit: CoresOilConversionAudit | None = None

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
        return cast(dict[str, Any], self.source.metadata())

    def _load_product(self, product: str) -> pd.DataFrame:
        workbook = DEFAULT_WORKBOOKS[product]
        path = self.raw_dir / workbook.filename
        if not path.exists():
            path = self.source.download(product)
        raw = self._read_workbook(path)
        audit = self._oil_conversion_audit(raw) if product == "oil" else None
        if product == "oil":
            self.oil_conversion_audit = audit
        frame = CoresProductionLoader(
            product=product,
            raw_frame=raw,
            header_row=self.header_row,
            sheet_name=self.sheet_name,
            oil_conversion_audit=audit,
        ).load()
        if audit is not None:
            self._write_oil_density_sidecar(audit)
        return self._write_normalized(product, frame)

    def _read_workbook(self, path: Path) -> pd.DataFrame:
        return pd.read_excel(
            path,
            sheet_name=self.sheet_name,
            header=self.header_row,
        )

    def _oil_conversion_audit(
        self,
        raw: pd.DataFrame,
    ) -> CoresOilConversionAudit:
        legacy_frame = CoresProductionLoader(product="oil", raw_frame=raw).load()
        field_names = sorted(legacy_frame["field_name"].dropna().astype(str).unique())
        factors = load_crude_density_factors(self.oil_density_registry_path)
        return build_oil_conversion_audit(
            field_names,
            factors,
            allow_default_density=self.allow_default_density,
        )

    def _write_oil_density_sidecar(self, audit: CoresOilConversionAudit) -> None:
        self.normalized_dir.mkdir(parents=True, exist_ok=True)
        path = self.normalized_dir / "cores_oil_density_factors.json"
        path.write_text(
            json.dumps(
                self._oil_density_sidecar_payload(audit),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def _oil_density_sidecar_payload(self, audit: CoresOilConversionAudit) -> dict:
        metadata = self._density_registry_metadata()
        return {
            "schema_version": 1,
            "generated_at": utc_now_iso(),
            "registry_version": metadata.get("registry_version"),
            "registry_date": metadata.get("registry_date"),
            "conversion_basis": "cited_field_density_factors",
            "coverage_status": _coverage_status(audit),
            "oil_field_count": len(audit.used_factors) + len(audit.defaulted_fields),
            "used_fields": _unique_factor_names(audit.used_factors),
            "defaulted_fields": list(audit.defaulted_fields),
            "missing_fields": list(audit.missing_fields),
            "default_bbl_per_tonne": _default_bbl_per_tonne(audit),
            "factors": [asdict(factor) for factor in audit.used_factors],
        }

    def _density_registry_metadata(self) -> dict[str, Any]:
        if self.oil_density_registry_path is None:
            return {}
        with self.oil_density_registry_path.open(encoding="utf-8") as fh:
            return cast(dict[str, Any], json.load(fh))

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
    oil_conversion_audit: CoresOilConversionAudit | None = None,
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
            _fixture_metadata(
                metadata,
                len(sample),
                refreshed_at_utc,
                oil_conversion_audit,
            ),
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
    oil_conversion_audit: CoresOilConversionAudit | None = None,
) -> dict[str, Any]:
    workbooks = dict(source_metadata.get("workbooks", {}))
    oil = dict(workbooks.get("oil", {}))
    refreshed = refreshed_at_utc or utc_now_iso()
    metadata = {
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
    if oil_conversion_audit is not None:
        metadata.update(_fixture_density_metadata(oil_conversion_audit))
    return metadata


def _fixture_density_metadata(audit: CoresOilConversionAudit) -> dict[str, Any]:
    conversion_factors = {
        "gas_gwh_to_mcf": GWH_TO_MCF,
        "oil_tonnes_to_bbl_by_field": _factor_map(audit.used_factors),
    }
    default_bbl_per_tonne = _default_bbl_per_tonne(audit)
    if default_bbl_per_tonne is not None:
        conversion_factors["oil_tonnes_to_bbl_default"] = default_bbl_per_tonne
    return {
        "conversion": "oil_bbl = tonnes * cited_field_density_factors",
        "conversion_factors": conversion_factors,
        "oil_conversion_audit": {
            "coverage_status": _coverage_status(audit),
            "used_fields": _unique_factor_names(audit.used_factors),
            "defaulted_fields": list(audit.defaulted_fields),
            "missing_fields": list(audit.missing_fields),
            "default_bbl_per_tonne": default_bbl_per_tonne,
            "factors": [asdict(factor) for factor in audit.used_factors],
        },
    }


def _factor_map(factors: Iterable[CoresCrudeDensityFactor]) -> dict[str, float]:
    values: dict[str, float] = {}
    for factor in factors:
        if factor.bbl_per_tonne is not None:
            values[factor.field_name] = factor.bbl_per_tonne
    return values


def _source_updated_date(oil_metadata: Mapping[str, Any]) -> Optional[str]:
    last_modified = oil_metadata.get("last_modified")
    if not last_modified:
        return _optional_str(oil_metadata.get("source_updated_date"))
    try:
        return parsedate_to_datetime(str(last_modified)).date().isoformat()
    except (TypeError, ValueError):
        return _optional_str(oil_metadata.get("source_updated_date"))


def _sort_production(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sort_values(["field_name", "year", "month"]).reset_index(drop=True)


def _package_cores_data_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "cores"


def _default_density_registry_path() -> Path:
    return _package_cores_data_dir() / "crude_density_factors.json"


def _coverage_status(audit: CoresOilConversionAudit) -> str:
    if audit.missing_fields:
        return "missing"
    if audit.defaulted_fields:
        return "defaulted"
    return "complete"


def _default_bbl_per_tonne(audit: CoresOilConversionAudit) -> float | None:
    if audit.defaulted_fields:
        return DEFAULT_OIL_BBL_PER_TONNE
    return None


def _unique_factor_names(factors: Iterable[CoresCrudeDensityFactor]) -> list[str]:
    names: dict[str, None] = {}
    for factor in factors:
        names[factor.field_name] = None
    return list(names)


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)
