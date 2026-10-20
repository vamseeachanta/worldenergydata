"""Read the public NSTA fields and wells themes without a production-feed join.

Responses are returned as normalized metadata with snapshot digests. Callers
retaining observations shall retain source snapshots alongside those digests.
No implicit on-disk cache is used, so a partial cache cannot appear complete.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from worldenergydata.ukcs.field_metadata import (
    FIELDS_URL,
    WELLS_URL,
    enrich_ukcs_field_metadata,
)


class NSTAResponseError(ValueError):
    """The upstream payload cannot establish a complete metadata result."""


class NSTAFieldMetadataClient:
    """Fetch one named field; optionally enrich absent depth from matching wells."""

    def __init__(self, *, session=None, page_size: int = 2000, timeout: float = 60):
        # Transport controls, not engineering constants. Both public layer
        # schemas report maxRecordCount=2000 (inspected 2026-10-20).
        if (
            isinstance(page_size, bool)
            or not isinstance(page_size, int)
            or page_size <= 0
        ):
            raise ValueError("page_size must be a positive integer")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and positive")
        if session is None:
            import requests

            session = requests.Session()
        self.session = session
        self.page_size = page_size
        self.timeout = timeout

    def load_field_metadata(
        self, field_name: str, *, include_wells: bool = True
    ) -> dict:
        """Return source-backed metadata, coverage and UTC retrieval time.

        Name matching is exact after trimming and case normalization, never a
        substring or geographic proximity join. SQL literals are escaped and
        supplied through request parameters, not interpolated into URLs.
        """
        if not isinstance(field_name, str) or not field_name.strip():
            raise ValueError("field_name must be a nonempty string")
        name = field_name.strip()
        fields = self._query(FIELDS_URL, "FIELDNAME", name)
        meta = enrich_ukcs_field_metadata(name, fields=fields)
        if include_wells and meta["water_depth_m"] is None:
            wells = self._query(WELLS_URL, "TARGETFLD", name)
            meta = enrich_ukcs_field_metadata(name, fields=fields, wells=wells)
        meta["retrieved_at"] = datetime.now(timezone.utc).isoformat()
        return meta

    def _query(self, url: str, field_column: str, field_name: str) -> list[dict]:
        literal = field_name.upper().replace("'", "''")
        rows: list[dict] = []
        seen_ids: set = set()
        while True:
            response = self.session.get(
                url + "/query",
                params={
                    "where": f"UPPER({field_column}) = '{literal}'",
                    "outFields": "*",
                    "returnGeometry": "false",
                    "orderByFields": "OBJECTID ASC",
                    "resultOffset": len(rows),
                    "resultRecordCount": self.page_size,
                    "f": "json",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            page = _validated_page(payload, seen_ids)
            rows.extend(page)
            if not payload.get("exceededTransferLimit", False):
                return rows


def _validated_page(payload: dict, seen_ids: set) -> list[dict]:
    if not isinstance(payload, dict) or "error" in payload:
        raise NSTAResponseError("NSTA query returned an error payload")
    features = payload.get("features")
    if not isinstance(features, list):
        raise NSTAResponseError("NSTA query omitted its feature list")
    if not features and payload.get("exceededTransferLimit"):
        raise NSTAResponseError("NSTA query returned an empty incomplete page")
    rows = []
    for feature in features:
        row = feature.get("attributes") if isinstance(feature, dict) else None
        if not isinstance(row, dict) or not isinstance(row.get("OBJECTID"), int):
            raise NSTAResponseError(
                "NSTA query returned invalid attributes or OBJECTID"
            )
        if row["OBJECTID"] in seen_ids:
            raise NSTAResponseError(
                "NSTA query repeated an OBJECTID; pagination is incomplete"
            )
        seen_ids.add(row["OBJECTID"])
        rows.append(row)
    return rows
