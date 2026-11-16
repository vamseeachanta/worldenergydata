"""Build an offline metadata inventory without querying or downloading datasets.

Caller-supplied descriptions and rights are retained as unverified metadata.
Catalogue availability does not establish redistribution permission.
"""

from collections.abc import Iterable, Mapping
from typing import TypedDict


class InventoryRecord(TypedDict):
    """Retained metadata; None represents an unknown size or unknown rights."""

    source_id: str
    name: str
    data_type: str
    size_bytes: int | None
    format: str
    relevance: str
    source_url: str
    rights: str | None


class InventorySummary(TypedDict):
    """Known bytes are a subtotal, excluding all unknown sizes."""

    dataset_count: int
    known_size_bytes: int
    unknown_size_count: int


class Inventory(TypedDict):
    """Rows ordered by exact source identifier, together with size accounting."""

    records: list[InventoryRecord]
    summary: InventorySummary


def _required_text(record: Mapping[str, object], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def build_inventory(records: Iterable[Mapping[str, object]]) -> Inventory:
    """Project supplied metadata into deterministic rows and a size summary.

    Required non-empty text fields are source_id, name, data_type, format,
    relevance and source_url. Identifiers are matched and sorted exactly,
    case-sensitively, without stripping or rewriting supplied text. source_url
    is retained without fetching it or verifying its provenance.

    size_bytes accepts non-negative integers only, excluding booleans. Missing
    or None sizes become None; a known empty dataset retains its zero size.
    rights accepts non-empty text or None; missing rights become None. Rights
    text is retained verbatim, without interpreting or verifying permissions.

    Other keys are omitted. Returned dictionaries are new objects and inputs
    are unchanged. The function performs no I/O. An empty iterable produces
    empty rows and zero counts. known_size_bytes sums only known sizes and
    must be read alongside unknown_size_count, rather than as a total size.

    Raises:
        ValueError: A record is not a mapping, a required text field is invalid,
            a source_id is duplicated, or size_bytes or rights is invalid.
    """
    rows: list[InventoryRecord] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("each record must be a mapping")
        source_id = _required_text(record, "source_id")
        if source_id in seen:
            raise ValueError("duplicate source_id")
        seen.add(source_id)

        size = record.get("size_bytes")
        if size is not None:
            # Byte counts cannot be negative; zero denotes a known empty size.
            if isinstance(size, bool) or not isinstance(size, int) or size < 0:
                raise ValueError("size_bytes must be a non-negative integer or None")

        rights = record.get("rights")
        if rights is not None:
            rights = _required_text(record, "rights")

        rows.append(
            {
                "source_id": source_id,
                "name": _required_text(record, "name"),
                "data_type": _required_text(record, "data_type"),
                "size_bytes": size,
                "format": _required_text(record, "format"),
                "relevance": _required_text(record, "relevance"),
                "source_url": _required_text(record, "source_url"),
                "rights": rights,
            }
        )

    rows.sort(key=lambda row: row["source_id"])
    return {
        "records": rows,
        "summary": {
            "dataset_count": len(rows),
            "known_size_bytes": sum(
                row["size_bytes"] for row in rows if row["size_bytes"] is not None
            ),
            "unknown_size_count": sum(row["size_bytes"] is None for row in rows),
        },
    }
