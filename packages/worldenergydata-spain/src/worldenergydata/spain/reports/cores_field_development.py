"""Spain CORES field-development report builder (#810)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pandas as pd

from worldenergydata.production.unified.adapters.spain_cores_adapter import (
    SpainCoresAdapter,
)
from worldenergydata.production.unified.query import ProductionQuery
from worldenergydata.spain.reference_chain import run_spain_reference_chain
from worldenergydata.spain.reports.cores_density_audit import (
    CoresDensityAuditError,
    load_oil_conversion_audit,
    oil_conversion_limitations,
)
from worldenergydata.spain.reports.cores_html import render_spain_cores_html

FIELD_METADATA = {
    "Ayoluengo": {
        "environment": "onshore",
        "field_name": "Ayoluengo",
        "source": "CORES",
    }
}


class CoresReportError(RuntimeError):
    """Raised when the normalized CORES scheduler cache is not report-ready."""


@dataclass(frozen=True)
class CoresReportSource:
    """Validated normalized scheduler output used by the report."""

    all_production: pd.DataFrame
    oil_production: pd.DataFrame
    gas_production: pd.DataFrame
    metadata: dict[str, Any]
    manifest: dict[str, Any]
    workbook_metadata: dict[str, Any]
    oil_conversion_audit: dict[str, Any] | None = None


class NormalizedCoresReportLoader:
    """Production adapter over normalized CORES CSVs, with no live XLSX reads."""

    def __init__(self, source: CoresReportSource):
        self._source = source

    def load_all_production(self) -> pd.DataFrame:
        return self._source.all_production.copy()

    def load_field_production(self, field_name: str) -> pd.DataFrame:
        frame = self.load_all_production()
        mask = frame["field_name"].astype(str).str.lower() == field_name.lower()
        return frame[mask].copy()

    def fetch(self, query: ProductionQuery) -> pd.DataFrame:
        frame = self.load_all_production()
        if query.fields:
            fields = {field.lower() for field in query.fields}
            frame = frame[frame["field_name"].astype(str).str.lower().isin(fields)]
        frame = _filter_period(frame, query.start, query.end)
        return _to_unified(frame)


def load_cores_report_source(cache_root: str | Path) -> CoresReportSource:
    root = Path(cache_root)
    all_production = _read_csv(root / "normalized" / "cores_all_production.csv")
    oil_production = _read_csv(root / "normalized" / "cores_oil_production.csv")
    gas_production = _read_csv(root / "normalized" / "cores_gas_production.csv")
    metadata = _read_json(root / "_metadata.json")
    manifest = _read_json(root / "manifest.json")
    workbook_metadata = _read_json(root / "metadata" / "cores_refresh_metadata.json")
    try:
        oil_conversion_audit = load_oil_conversion_audit(
            root,
            metadata,
            oil_production,
        )
    except CoresDensityAuditError as exc:
        raise CoresReportError(str(exc)) from exc
    _validate_metadata(metadata, manifest, workbook_metadata, len(all_production))
    return CoresReportSource(
        all_production=all_production,
        oil_production=oil_production,
        gas_production=gas_production,
        metadata=metadata,
        manifest=manifest,
        workbook_metadata=workbook_metadata,
        oil_conversion_audit=oil_conversion_audit,
    )


def build_report(
    cache_root: str | Path,
    *,
    output_html: str | Path | None = None,
    output_json: str | Path | None = None,
    oil_price_usd_bbl: float = 75.0,
) -> dict[str, Any]:
    source = load_cores_report_source(cache_root)
    loader = NormalizedCoresReportLoader(source)
    fields = _field_summaries(source.all_production)
    economics = _economics_summary(loader, fields, oil_price_usd_bbl)
    summary = _summary(source, fields, economics)
    if output_json is not None:
        _write_json(Path(output_json), summary)
    if output_html is not None:
        _write_text(Path(output_html), render_spain_cores_html(summary))
    return summary


def _summary(
    source: CoresReportSource,
    fields: list[dict[str, Any]],
    economics: dict[str, Any],
) -> dict[str, Any]:
    summary = {
        "source": {
            "format": source.metadata["format"],
            "last_refresh": source.metadata["last_refresh"],
            "record_count": source.metadata["record_count"],
            "source_url": source.metadata["source_url"],
        },
        "scheduler_manifest": source.manifest,
        "workbook_metadata": source.workbook_metadata,
        "fields": {
            "field_count": len(fields),
            "items": fields,
        },
        "economics": economics,
        "limitations": [
            "Only fields with explicit field metadata and oil production run economics.",
            "Gas-only revenue is deferred to issue #808.",
            *oil_conversion_limitations(source.oil_conversion_audit),
            "Ayoluengo uses offshore FDAS plumbing as a wiring check; mismatch is flagged.",
        ],
    }
    if source.oil_conversion_audit is not None:
        summary["oil_conversion_audit"] = source.oil_conversion_audit
    return summary


def _economics_summary(
    loader: NormalizedCoresReportLoader,
    fields: list[dict[str, Any]],
    oil_price_usd_bbl: float,
) -> dict[str, Any]:
    adapter = SpainCoresAdapter(loader=loader)
    evaluated = [
        item["field_name"]
        for item in fields
        if item["field_name"] in FIELD_METADATA and item["oil_bbl"] > 0
    ]
    results = {}
    for field_name in evaluated:
        result = run_spain_reference_chain(
            adapter=adapter,
            field_meta=FIELD_METADATA[field_name],
            field_name=field_name,
            oil_price_usd_bbl=oil_price_usd_bbl,
        )
        results[field_name] = _reference_chain_summary(result)
    return {
        "evaluated_fields": evaluated,
        "oil_price_usd_bbl": oil_price_usd_bbl,
        "results": results,
    }


def _reference_chain_summary(result: dict[str, Any]) -> dict[str, Any]:
    ranked = result.get("ranked_concepts", [])
    return {
        "concept_screening_label": result["concept_screening_label"],
        "dev_system": result["dev_system"],
        "economics_label": result["economics_label"],
        "pre_tax_metrics": _rounded_metrics(result["pre_tax_metrics"]),
        "ranked_concepts": [_concept_item(item) for item in ranked[:5]],
    }


def _field_summaries(frame: pd.DataFrame) -> list[dict[str, Any]]:
    items = []
    for field_name, group in frame.groupby("field_name", sort=True):
        oil = float(_series(group, "oil_bbl").sum())
        gas = float(_series(group, "gas_mcf").sum())
        items.append(
            {
                "field_name": str(field_name),
                "first_period": _period(group, "min"),
                "last_period": _period(group, "max"),
                "gas_mcf": round(gas, 3),
                "oil_bbl": round(oil, 3),
                "row_count": int(len(group)),
                "limitations": _field_limitations(str(field_name), oil, gas),
                "monthly": _monthly_series(group),
            }
        )
    return items


def _field_limitations(field_name: str, oil_bbl: float, gas_mcf: float) -> list[str]:
    limitations = []
    if gas_mcf > 0 and oil_bbl <= 0:
        limitations.append("gas_revenue_deferred_to_issue_808")
    if field_name not in FIELD_METADATA:
        limitations.append("field_environment_metadata_not_curated")
    return limitations


def _monthly_series(group: pd.DataFrame) -> list[dict[str, Any]]:
    frame = group.copy()
    frame["_period"] = _period_series(frame)
    frame = frame.sort_values(["year", "month"])
    rows = []
    for _, row in frame.iterrows():
        rows.append(
            {
                "period": row["_period"],
                "oil_bbl": _rounded_number(row.get("oil_bbl")),
                "gas_mcf": _rounded_number(row.get("gas_mcf")),
            }
        )
    return rows


def _validate_metadata(
    metadata: dict[str, Any],
    manifest: dict[str, Any],
    workbook_metadata: dict[str, Any],
    row_count: int,
) -> None:
    if metadata.get("format") != "csv":
        raise CoresReportError("_metadata.json must declare format=csv")
    if int(metadata.get("record_count", -1)) != row_count:
        raise CoresReportError("_metadata.json record_count does not match CSV rows")
    if int(manifest.get("records_updated", -1)) != row_count:
        raise CoresReportError("manifest.json records_updated does not match CSV rows")
    if manifest.get("status") != "success":
        raise CoresReportError("manifest.json status must be success")
    if manifest.get("job_name") != "spain_cores_refresh":
        raise CoresReportError("manifest.json job_name must be spain_cores_refresh")
    for key in ("source_url", "last_refresh"):
        if not metadata.get(key):
            raise CoresReportError(f"_metadata.json missing {key}")
    _validate_workbooks(workbook_metadata)


def _validate_workbooks(workbook_metadata: dict[str, Any]) -> None:
    workbooks = workbook_metadata.get("workbooks", {})
    for product in ("oil", "gas"):
        data = workbooks.get(product)
        if not isinstance(data, dict):
            raise CoresReportError("cores_refresh_metadata.json missing workbook data")
        for key in (
            "source_url",
            "sha256",
            "byte_count",
            "last_modified",
            "status_code",
        ):
            if data.get(key) in (None, ""):
                raise CoresReportError(f"cores_refresh_metadata.json missing {key}")
        status = int(data["status_code"])
        if status >= 400:
            raise CoresReportError(f"{product} workbook status_code={status}")


def _to_unified(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["region"] = "spain"
    out["source"] = "CORES"
    for column in ("oil_bbl", "gas_mcf", "water_bbl", "condensate_bbl"):
        if column not in out:
            out[column] = 0.0
        out[column] = pd.to_numeric(out[column], errors="coerce").fillna(0.0)
    columns = [
        "region",
        "field_name",
        "year",
        "month",
        "oil_bbl",
        "gas_mcf",
        "water_bbl",
        "condensate_bbl",
        "source",
    ]
    return (
        out[columns].sort_values(["field_name", "year", "month"]).reset_index(drop=True)
    )


def _filter_period(
    frame: pd.DataFrame,
    start: str | None,
    end: str | None,
) -> pd.DataFrame:
    if start is None and end is None:
        return frame
    period = _period_series(frame)
    mask = pd.Series(True, index=frame.index)
    if start is not None:
        mask &= period >= start
    if end is not None:
        mask &= period <= end
    return frame[mask]


def _period(group: pd.DataFrame, method: str) -> str:
    series = _period_series(group)
    value = series.min() if method == "min" else series.max()
    return str(value)


def _period_series(frame: pd.DataFrame) -> pd.Series:
    year = pd.to_numeric(frame["year"], errors="raise").astype(int)
    month = pd.to_numeric(frame["month"], errors="raise").astype(int)
    return pd.Series(
        [f"{y:04d}-{m:02d}" for y, m in zip(year, month)], index=frame.index
    )


def _series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce").fillna(0.0)


def _concept_item(item: Any) -> dict[str, Any]:
    return {
        "concept_type": _name(getattr(item, "concept_type", "")),
        "total_score": round(float(getattr(item, "total_score", 0.0)), 4),
        "warnings": list(getattr(item, "warnings", [])),
    }


def _name(value: Any) -> str:
    return getattr(value, "value", str(value))


def _rounded_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    rounded = {}
    for key, value in metrics.items():
        rounded[key] = round(value, 3) if isinstance(value, float) else value
    return rounded


def _rounded_number(value: Any) -> float:
    if value is None or pd.isna(value):
        return 0.0
    return round(float(value), 3)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise CoresReportError(f"missing {path.name}")
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise CoresReportError(f"missing {path.name}")
    return pd.read_csv(path)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
