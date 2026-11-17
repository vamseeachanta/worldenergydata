"""Pure reader for local fields-theme JSON; no live schema or consent claim."""

from __future__ import annotations

import hashlib
import json
import math
from decimal import Decimal

_COLUMNS = {
    "operator": "CURR_OPER",
    "field_status": "STATUS",
    "startup_raw": "PROD_DATE",
    "discovery_raw": "DISC_DATE",
}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("nonfinite JSON number")


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("nonfinite JSON number")
    if Decimal(value) != Decimal(str(number)):
        raise ValueError("unsupported JSON decimal precision")
    return number


def read_field_metadata(
    raw: bytes, field_name: str, *, source_url: str, retrieved_at: str
) -> dict:
    """Match FIELDNAME by trim/casefold and retain the supplied bytes' digest.

    Optional attributes accept only strings or null. Dates stay uninterpreted;
    coverage means present text, never engineering eligibility. Source URL and
    retrieval time are caller assertions. OBJECTID must be an integer.
    JSON decimals must round-trip through finite floats without changing their
    decimal value; unsupported precision (including underflow) is rejected.
    """
    if not isinstance(raw, bytes):
        raise TypeError("snapshot must be bytes")
    for value in (field_name, source_url, retrieved_at):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("request and provenance must be nonblank text")
    payload = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
        parse_float=_finite_float,
    )
    if not isinstance(payload, dict) or not isinstance(payload.get("features"), list):
        raise ValueError("snapshot requires a features list")
    matches = []
    for feature in payload["features"]:
        if not isinstance(feature, dict) or not isinstance(
            feature.get("attributes"), dict
        ):
            raise ValueError("feature requires attributes")
        attrs = feature["attributes"]
        name = attrs.get("FIELDNAME")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("FIELDNAME must be nonblank text")
        if type(attrs.get("OBJECTID")) is not int:
            raise ValueError("OBJECTID must be an integer")
        for column in _COLUMNS.values():
            value = attrs.get(column)
            if value is not None and not isinstance(value, str):
                raise ValueError("metadata must be text or null")
        if name.strip().casefold() == field_name.strip().casefold():
            matches.append(attrs)
    records = [
        {key: value for key, value in attrs.items() if key != "OBJECTID"}
        for attrs in matches
    ]
    if len({json.dumps(row, sort_keys=True) for row in records}) > 1:
        raise ValueError("conflicting field metadata")
    selected = records[0] if records else {}
    meta = {"field_name": field_name.strip(), "source": "NSTA"}
    for target, column in _COLUMNS.items():
        value = selected.get(column)
        meta[target] = value if value is not None and value.strip() else None
    meta["metadata_evidence"] = {
        "coverage": {key: meta[key] is not None for key in _COLUMNS},
        "attributes": selected,
        "source_ids": sorted({row["OBJECTID"] for row in matches}),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "source_url": source_url,
        "retrieved_at": retrieved_at,
        "match_status": "matched" if matches else "no_match",
        "fdp_consent": "NOT_EVALUATED",
        "recommendation_ready": False,
    }
    return meta
