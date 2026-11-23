"""Pack normalized records into deterministic, bounded, data-only JSON shards.

Transport validation only: callers retain source, identity and release admission.
See docs/data/browser-shard-contract.md for encoding and return values.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "_shard_strict_json", Path(__file__).with_name("explorer_visualization.py")
)
_PARSER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PARSER)

SCHEMA = "browser_shard_transport/1.0.0"
TABLES = ("fields", "wells", "countries", "parametric_economics")


def _data_only(value):
    """Accept JSON containers/scalars; conservatively reject angle brackets."""
    if isinstance(value, str):
        if "<" in value or ">" in value:
            raise ValueError("Markup delimiters are not data-only text")
    elif isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError("Object keys must be strings")
            _data_only(key)
            _data_only(child)
    elif isinstance(value, list):
        for child in value:
            _data_only(child)
    elif value is not None and type(value) not in (bool, int, float):
        raise ValueError("Only JSON values are supported")


def pack_records(table, records, *, id_key, schema, max_rows, max_bytes):
    """Return table totals and shards containing bytes plus integrity metadata.

    Bounds include array punctuation and the trailing newline. IDs are sorted
    lexicographically, without normalization. No input is mutated; no I/O occurs.
    """
    if table not in TABLES or schema != SCHEMA:
        raise ValueError("Unknown table or transport schema")
    if not isinstance(id_key, str) or not id_key.strip():
        raise ValueError("An explicit nonblank ID key is required")
    _data_only(id_key)
    for bound in (max_rows, max_bytes):
        if type(bound) is not int or bound <= 0:
            raise ValueError("Bounds must be positive non-Boolean integers")

    encoded = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Each record must be an object")
        identity = record.get(id_key)
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError("Each record requires a nonblank string ID")
        if identity in encoded:
            raise ValueError("Duplicate record ID")
        _data_only(record)
        raw = json.dumps(
            record,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(raw) + 3 > max_bytes:
            raise ValueError("Record exceeds byte bound")
        encoded[identity] = raw

    shards = []

    def append_shard(parts):
        raw = b"[" + b",".join(parts) + b"]\n"
        decoded = _PARSER.strict_json(raw)
        if len(decoded) != len(parts):
            raise ValueError("Encoded record count mismatch")
        shards.append(
            {
                "path": f"browser/{table}/{len(shards):06}.json",
                "sha256": hashlib.sha256(raw).hexdigest(),
                "byte_count": len(raw),
                "record_count": len(parts),
                "media_type": "application/json",
                "schema": schema,
                "data": raw,
            }
        )

    parts = []
    size = 3  # Two array brackets plus one newline, in UTF-8 bytes.
    for identity in sorted(encoded):
        raw = encoded[identity]
        addition = len(raw) + bool(parts)  # Comma between records.
        if parts and (len(parts) == max_rows or size + addition > max_bytes):
            append_shard(parts)
            parts = []
            size = 3
        size += len(raw) + bool(parts)
        parts.append(raw)
    if parts:
        append_shard(parts)
    return {
        "table": table,
        "schema": schema,
        "record_count": len(encoded),
        "byte_count": sum(shard["byte_count"] for shard in shards),
        "shards": shards,
    }
