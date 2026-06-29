"""Texas RRC lifecycle source catalog loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

SOURCE_CATALOG_ROOT = Path("/mnt/ace/worldenergydata/data/modules/texas_rrc")
SOURCE_CATALOG_PATH = Path(__file__).parent / "data" / "source_catalog.yml"

REQUIRED_SOURCE_FIELDS = {
    "source_url",
    "format",
    "refresh_cadence",
    "raw_path",
    "normalized_path",
    "curated_path",
    "availability_status",
    "source_of_record",
    "caveats",
}

VALID_AVAILABILITY_STATUSES = {"available", "partial", "validation_only"}


def load_source_catalog(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load and validate the Texas RRC source catalog."""
    catalog_path = path or SOURCE_CATALOG_PATH
    with catalog_path.open("r", encoding="utf-8") as stream:
        payload = yaml.safe_load(stream) or {}

    catalog = payload.get("sources", {})
    if not isinstance(catalog, dict):
        raise ValueError("Texas RRC source catalog must contain a 'sources' mapping")

    validate_source_catalog(catalog)
    return catalog


def validate_source_catalog(catalog: dict[str, dict[str, Any]]) -> None:
    """Validate source catalog shape and storage-path policy."""
    for source_id, entry in catalog.items():
        if not isinstance(entry, dict):
            raise ValueError(f"Catalog entry '{source_id}' must be a mapping")

        missing = REQUIRED_SOURCE_FIELDS.difference(entry)
        if missing:
            fields = ", ".join(sorted(missing))
            raise ValueError(f"Catalog entry '{source_id}' is missing: {fields}")

        status = entry["availability_status"]
        if status not in VALID_AVAILABILITY_STATUSES:
            raise ValueError(
                f"Catalog entry '{source_id}' has invalid availability_status: "
                f"{status!r}"
            )

        if not isinstance(entry["source_of_record"], bool):
            raise ValueError(
                f"Catalog entry '{source_id}' field 'source_of_record' must be boolean"
            )
        if status == "validation_only" and entry["source_of_record"]:
            raise ValueError(
                f"Catalog entry '{source_id}' cannot be source_of_record when "
                "availability_status is validation_only"
            )

        for field in ("raw_path", "normalized_path", "curated_path"):
            _validate_catalog_path(source_id, field, Path(entry[field]))


def _validate_catalog_path(source_id: str, field: str, path: Path) -> None:
    if not path.is_absolute():
        raise ValueError(f"Catalog entry '{source_id}' field '{field}' is not absolute")
    if not path.is_relative_to(SOURCE_CATALOG_ROOT):
        raise ValueError(
            f"Catalog entry '{source_id}' field '{field}' must stay under "
            f"{SOURCE_CATALOG_ROOT}"
        )
