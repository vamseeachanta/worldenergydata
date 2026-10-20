"""Colombia ANH metadata and native monthly observations, without imputation.

Schema and units: ANH Socrata metadata, read 2026-10-20:
https://www.datos.gov.co/api/views/fdvb-hsrf.json (produccion_bls description)
https://www.datos.gov.co/api/views/5dux-bfvx.json (produccionkpc description).
No fiscal assumptions, unit conversion, daily-rate conversion or aggregation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from urllib.parse import urlencode

from .argentina import Discovery

# Dataset identifiers and volume units are declared in the cited ANH metadata.
DATASETS = {
    "oil": ("fdvb-hsrf", "produccion_bls", "bbl"),
    "gas": ("5dux-bfvx", "produccionkpc", "Mcf"),
}


@dataclass(frozen=True)
class Observation:
    """A source row, retaining contract/operator and an explicit unknown value."""

    dataset_id: str
    field_name: str
    period: str
    commodity: str
    volume: Decimal | None
    unit: str
    contract: str | None
    operator: str | None


def _dataset(commodity: str) -> tuple[str, str, str]:
    if commodity not in DATASETS:
        raise ValueError("commodity must be oil or gas")
    return DATASETS[commodity]


def metadata_url(commodity: str) -> str:
    """The source's credential-free dataset-level metadata endpoint."""
    dataset_id, _, _ = _dataset(commodity)
    return f"https://www.datos.gov.co/api/views/{dataset_id}.json"


def rows_url(commodity: str, *, limit: int, offset: int) -> str:
    """Build one bounded page; the caller chooses count and offset, no auto-loop.

    Paging was exercised against the cited ANH row endpoints on 2026-10-20.
    Stable row ordering reduces ambiguity within a snapshot; source updates
    between requests still invalidate any completeness claim.
    """
    dataset_id, _, _ = _dataset(commodity)
    if type(limit) is not int or limit <= 0 or type(offset) is not int or offset < 0:
        raise ValueError("limit must be a positive integer; offset must be nonnegative")
    query = urlencode({"$limit": limit, "$offset": offset, "$order": ":id"})
    return f"https://www.datos.gov.co/resource/{dataset_id}.json?{query}"


def describe_dataset(metadata: dict) -> Discovery:
    """Preserve source vintage, reuse terms and refresh frequency verbatim."""
    dataset_id = metadata.get("id")
    if dataset_id not in {item[0] for item in DATASETS.values()}:
        raise ValueError("unrecognized ANH dataset id")
    updated = metadata.get("rowsUpdatedAt")
    vintage = None
    if updated is not None:
        if type(updated) is not int:
            raise ValueError("rowsUpdatedAt must be a POSIX integer timestamp")
        vintage = datetime.fromtimestamp(updated, tz=timezone.utc).isoformat()
    custom = metadata.get("metadata", {}).get("custom_fields", {})
    frequency = custom.get("Información de Datos", {}).get(
        "Frecuencia de Actualización"
    )
    return Discovery(
        dataset_id=dataset_id,
        license=(metadata.get("license") or {}).get("name") or None,
        update_frequency=frequency or None,
        source_modified=vintage,
        resources=(),
    )


def _period(row: dict) -> str:
    year, month = str(row.get("vigencia")), str(row.get("mes"))
    if not re.fullmatch(r"[0-9]+", year) or not re.fullmatch(r"[0-9]+", month):
        raise ValueError("monthly period requires integer year and month")
    try:
        period = date(int(year), int(month), 1)
        return f"{period.year:04d}-{period.month:02d}"
    except ValueError as exc:
        raise ValueError("invalid monthly period") from exc


def _volume(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    # The cited ANH row endpoints also serve comma groups with a decimal point.
    # Local ingestion policy rejects group-only text and signed adjustments
    # pending qualification; it does not guess another locale's separators.
    text = str(value).strip()
    plain = re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", text)
    grouped = re.fullmatch(r"[0-9]{1,3}(?:,[0-9]{3})+\.[0-9]+", text)
    if not plain and not grouped:
        raise ValueError("volume must be unambiguous nonnegative decimal text or null")
    return Decimal(text.replace(",", ""))


def normalize_rows(rows: list[dict], *, commodity: str) -> tuple[Observation, ...]:
    """Retain native monthly volumes; never infer water or join commodities.

    Empty strings and null volumes remain unknown. Schema drift, missing field
    keys and ambiguous numbers fail closed rather than become zero production.
    """
    dataset_id, volume_column, unit = _dataset(commodity)
    if not isinstance(rows, list):
        raise TypeError("SODA response must be an array of rows")
    observations = []
    for row in rows:
        if not isinstance(row, dict):
            raise TypeError("SODA row must be an object")
        period = _period(row)
        name = row.get("campo")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("field name is required")
        if volume_column not in row:
            raise ValueError("volume column is missing")
        observations.append(
            Observation(
                dataset_id,
                name,
                period,
                commodity,
                _volume(row[volume_column]),
                unit,
                row.get("contrato") or None,
                row.get("operadora") or None,
            )
        )
    return tuple(observations)
