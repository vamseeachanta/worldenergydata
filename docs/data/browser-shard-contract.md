# Browser shard transport

`browser_shard_transport/1.0.0` packs already-normalized records in memory.
It validates transport shape, without establishing domain-schema validity,
identity assignment, provenance, redistribution rights or publication readiness.

## API

Load `scripts/hf_export/browser_shards.py` by file path and call
`pack_records(table, records, *, id_key, schema, max_rows, max_bytes)`.
Tables are `fields`, `wells`, `countries` and `parametric_economics`.
The schema must equal `browser_shard_transport/1.0.0`; unknown versions fail.
Both bounds are explicit positive integers; Boolean bounds fail.
Each record is a JSON object with a unique, nonblank string at `id_key`.
Other values may be JSON objects, arrays, strings, finite numbers, Booleans or
null. Object keys must be strings at every depth. Unsupported values fail.
Strings and keys containing either angle bracket fail conservatively, including
comparison text: callers must supply plain text without markup delimiters.
Consumers must still escape values when rendering them.

## Deterministic bytes and bounds

Records sort lexicographically by ID, preserving case and Unicode code points.
Object keys sort recursively. Arrays within records retain their order.
JSON uses UTF-8, unescaped Unicode, compact comma/colon separators and exactly
one trailing newline. Non-finite numbers fail rather than becoming null.
No timestamp, path or environment value is added to the records.

Complete records pack greedily within both bounds. Byte limits include the
array brackets, commas and newline; they measure encoded bytes, not characters.
An oversized individual record fails the entire call without truncation.
Empty input returns no shards and zero records and bytes, even with a byte
bound smaller than an empty JSON array. Input objects are never mutated.
The API performs no network or filesystem operations and returns only after
all records have passed validation.

## Return value

The result contains `table`, `schema`, `record_count`, `byte_count` and `shards`.
Each shard contains `data` (bytes), `path`, `sha256`, `byte_count`,
`record_count`, `media_type` (`application/json`) and `schema`.
Paths are generated as `browser/<table>/<zero-based-index:06>.json`;
the index width is a minimum, so larger collections do not wrap.
Totals cover all shards; byte totals exclude metadata. The digest covers the
exact returned bytes, including the newline. Metadata is not a full manifest.

Callers own source admission, stable identities, joins, domain schemas,
licensing, clean source revisions, manifests, uploads and exact-revision
readback. Existing analytical formats and economics suppression are unchanged.
The earlier results-bundle regeneration mismatch remains unexplained (#1045).
