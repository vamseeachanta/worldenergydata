"""Bounded GET support for the regulator's observed ArcGIS service.

No OData service was established at the inspected FactPages API URLs.
Query attributes retain source units; adapters convert dates and production units.
"""

import hashlib
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SERVICE = "/services/DataService/Data/FeatureServer"
USER_AGENT = (
    "WorldEnergyData bounded SODIR reader "
    "https://github.com/vamseeachanta/worldenergydata"
)
DEFAULT_FIELDS = {
    "fields": ["OBJECTID", "fldName", "fldNpdidField"],
    "wellbores": ["OBJECTID", "wlbWellboreName", "wlbNpdidWellbore"],
    "production": [
        "OBJECTID",
        "prfInformationCarrier",
        "prfInformationCarrierKind",
        "prfYear",
        "prfMonth",
        "prfPrdOilNetMillSm3",
    ],
}
SCHEMAS = json.loads(Path(__file__).with_name("feature_schemas.json").read_text())


def parse_metadata(metadata: dict[str, Any]) -> dict[str, str]:
    """Extract ArcGIS property names and types without guessing missing fields."""
    if not isinstance(metadata, dict):
        raise TypeError("metadata must be an object")
    fields = metadata.get("fields")
    if not isinstance(fields, list) or not fields:
        raise ValueError("missing metadata fields")
    result = {}
    for field in fields:
        if not isinstance(field, dict):
            raise TypeError("invalid metadata field")
        name, kind = field.get("name"), field.get("type")
        if not isinstance(name, str) or not name.strip() or name in result:
            raise ValueError("invalid metadata field")
        if not isinstance(kind, str) or kind not in {
            "esriFieldTypeOID",
            "esriFieldTypeInteger",
            "esriFieldTypeSmallInteger",
            "esriFieldTypeDouble",
            "esriFieldTypeSingle",
            "esriFieldTypeString",
            "esriFieldTypeDate",
        }:
            raise ValueError("unsupported metadata type")
        result[name] = kind
    return result


def _entity_schema(client: Any, entity: str) -> dict[str, Any]:
    if client.base_url != "https://factmaps.sodir.no/api/rest":
        raise ValueError("unexpected service base")
    if not isinstance(entity, str) or entity not in SCHEMAS:
        raise ValueError("unknown entity")
    return SCHEMAS[entity]


def _validate_limits(client: Any, *limits: int) -> None:
    for value in (*limits, client.timeout):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError("limits and timeout must be positive")
    if not all(isinstance(value, int) for value in limits):
        raise ValueError("count limits must be integers")


def get_entity_metadata(client: Any, entity: str, *, max_bytes: int) -> dict[str, str]:
    """Read one bounded layer definition and check the committed schema.

    Source: Esri REST API, Layer (Feature Service), JSON response syntax,
    accessed 2026-10-19:
    https://developers.arcgis.com/rest/services-reference/enterprise/layer-feature-service/
    Layer IDs and required properties retain feature_schemas.json provenance.
    Additional supported properties are returned; missing properties, changed
    types or a different object ID field raise ValueError. The byte budget is
    a required caller resource limit, not an advertised service capacity.
    This explicit check does not run automatically before query_entity.
    """
    schema = _entity_schema(client, entity)
    _validate_limits(client, max_bytes)
    client.feature_observations = []
    url = client.base_url + SERVICE + f"/{schema['layer_id']}"
    payload, _, _ = _read_response(client, url, {"f": "json"}, max_bytes)
    properties = parse_metadata(payload)
    if payload.get("objectIdField") != schema["object_id_field"]:
        raise ValueError("metadata object ID field mismatch")
    if any(properties.get(key) != kind for key, kind in schema["properties"].items()):
        raise ValueError("metadata schema mismatch")
    return properties


def validate_record(entity: str, record: Any) -> None:
    """Validate returned attributes; nulls and projected fields are permitted.

    ArcGIS dates are numeric epoch milliseconds. No completeness or engineering
    readiness is inferred from this structural validation.
    """
    properties = SCHEMAS[entity]["properties"]
    if not isinstance(record, dict):
        raise ValueError("attributes must be an object")
    for key, value in record.items():
        if key not in properties:
            raise ValueError("unknown attribute")
        if value is None:
            continue
        kind = properties[key]
        if kind == "esriFieldTypeString":
            valid = isinstance(value, str)
        elif kind in {
            "esriFieldTypeOID",
            "esriFieldTypeInteger",
            "esriFieldTypeSmallInteger",
        }:
            valid = isinstance(value, int) and not isinstance(value, bool)
        else:
            valid = (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
            )
        if not valid:
            raise ValueError("attribute type mismatch: " + key)


def _production_record(record: dict[str, Any]) -> dict[str, Any]:
    """Reuse volume parsing, correcting produced-water naming at this boundary."""
    from .production.monthly_loader import MonthlyProductionLoader

    if (
        record.get("prfInformationCarrierKind") != "FIELD"
        or not 1 <= (record.get("prfMonth") or 0) <= 12
        or record.get("prfYear") is None
        or not record.get("prfInformationCarrier")
    ):
        raise ValueError("processor adapter requires monthly field production")
    raw = dict(record)
    raw["fldName"] = record["prfInformationCarrier"]
    raw["prfPrdProducedWaterInFieldMillSm3"] = record.get(
        "prfPrdProducedWaterInFieldMillS"
    )
    parsed: dict[str, Any] = MonthlyProductionLoader().parse_raw_record(raw)
    parsed["water_produced_sm3"] = parsed.pop("water_injected_sm3")
    sources = {
        "oil_sm3": "prfPrdOilNetMillSm3",
        "gas_sm3": "prfPrdGasNetBillSm3",
        "ngl_sm3": "prfPrdNGLNetMillSm3",
        "condensate_sm3": "prfPrdCondensateNetMillSm3",
        "water_produced_sm3": "prfPrdProducedWaterInFieldMillS",
    }
    for target, source in sources.items():
        if record.get(source) is None:
            parsed[target] = None
    return parsed


def processor_record(entity: str, record: dict[str, Any]) -> dict[str, Any]:
    """Adapt source records without changing query results.

    Field/wellbore aliases include UTC ISO dates for the existing processors.
    Production returns final columns matching the monthly loader's volume units
    (Sm3), except water_produced_sm3 replaces its incorrect injection label.
    This final row shall not be passed back into the legacy raw-record loader.
    Annual and discovery profiles are rejected; absent volumes remain unknown.
    """
    validate_record(entity, record)
    if entity == "production":
        return _production_record(record)
    aliases = {
        "fields": {
            "fldCurrentActivitySatus": "fldStatus",
            "cmpLongName": "fldOperatorName",
        },
        "wellbores": {"wlbWellboreName": "wlbName"},
    }
    mapped = dict(record)
    for source, target in aliases[entity].items():
        if source in record:
            mapped[target] = record[source]
    for name, kind in SCHEMAS[entity]["properties"].items():
        if kind == "esriFieldTypeDate" and record.get(name) is not None:
            mapped[name] = (
                datetime.fromtimestamp(record[name] / 1000, timezone.utc)
                .date()
                .isoformat()
            )
    return mapped


def _read_response(
    client: Any, url: str, params: dict[str, Any], budget: int
) -> tuple[dict[str, Any], bytes, str]:
    """One capped request, with no redirects or retries after any error."""
    if client.session.get_adapter(url).max_retries.total != 0:
        raise ValueError("transport retries must be disabled")
    delay = 2 - (time.monotonic() - getattr(client, "_feature_last_request", 0))
    if delay > 0:
        time.sleep(delay)
    client._feature_last_request = time.monotonic()
    with client.session.get(
        url,
        params=params,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=client.timeout,
        stream=True,
        allow_redirects=False,
    ) as response:
        if response.status_code != 200:
            raise ValueError(f"HTTP {response.status_code}; request stopped")
        raw = bytearray()
        for chunk in response.iter_content(8192):
            if len(raw) + len(chunk) > budget:
                raise ValueError("response byte cap exceeded")
            raw.extend(chunk)
        client._feature_last_request = time.monotonic()
        client.feature_observations.append(
            {
                "source_url": response.url,
                "status": response.status_code,
                "size_bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )
        payload = json.loads(raw)
        if not isinstance(payload, dict) or "error" in payload:
            raise ValueError("service error or invalid response")
        return payload, bytes(raw), response.url


def _query_parameters(
    client: Any,
    entity: str,
    select: Any,
    where: str,
    page_size: int,
    max_pages: int,
    max_bytes: int,
) -> tuple[str, dict[str, Any], str]:
    schema = _entity_schema(client, entity)
    _validate_limits(client, page_size, max_pages, max_bytes)
    if not isinstance(where, str) or not where.strip():
        raise ValueError("where must be nonempty")
    if select is not None and not isinstance(select, (list, tuple)):
        raise ValueError("select must be a list or tuple of field names")
    fields = list(DEFAULT_FIELDS[entity]) if select is None else list(select)
    if not fields or any(
        not isinstance(f, str) or f not in schema["properties"] for f in fields
    ):
        raise ValueError("unknown or empty select")
    if len(set(fields)) != len(fields):
        raise ValueError("duplicate select fields")
    oid = schema["object_id_field"]
    if oid not in fields:
        raise ValueError("select must include object ID for stable paging")
    url = client.base_url + SERVICE + f"/{schema['layer_id']}/query"
    params = {
        "f": "json",
        "where": where,
        "outFields": ",".join(fields),
        "returnGeometry": "false",
        "orderByFields": oid + " ASC",
        "resultRecordCount": page_size,
    }
    return url, params, oid


def query_entity(
    client: Any,
    entity: str,
    select: list[str] | None = None,
    where: str = "1=1",
    page_size: int = 2,
    max_pages: int = 1,
    max_bytes: int = 1048576,
) -> list[dict[str, Any]]:
    """Read bounded ArcGIS pages, failing rather than returning truncated data.

    Field and wellbore defaults use projections exercised against the live source.
    The production default, including the kind key, was exercised in a two-row probe.
    Select additional schema properties explicitly for processor adaptation,
    including each additional production volume needed by the caller.
    Every requested attribute must be present, although its value may be null.
    """
    url, params, oid = _query_parameters(
        client, entity, select, where, page_size, max_pages, max_bytes
    )
    records: list[dict[str, Any]] = []
    used = 0
    client.feature_observations = []
    previous_oid = None
    for _ in range(max_pages):
        params["resultOffset"] = len(records)
        payload, raw, source_url = _read_response(client, url, params, max_bytes - used)
        used += len(raw)
        rows = payload.get("features")
        if not isinstance(rows, list) or len(rows) > page_size:
            raise ValueError("invalid feature array")
        for feature in rows:
            record = feature.get("attributes") if isinstance(feature, dict) else None
            validate_record(entity, record)
            if not isinstance(record, dict):
                raise ValueError("invalid attributes")
            if not set(params["outFields"].split(",")).issubset(record):
                raise ValueError("missing requested attributes")
            identifier = record.get(oid)
            if identifier is None or (
                previous_oid is not None and identifier <= previous_oid
            ):
                raise ValueError("missing or nonascending object ID")
            previous_oid = identifier
            records.append(record)
        more = payload.get("exceededTransferLimit", False)
        if not isinstance(more, bool):
            raise ValueError("invalid transfer limit flag")
        if not more:
            return records
        if not rows:
            raise ValueError("empty continuation page")
    raise ValueError("page cap reached; incomplete result discarded")


def emit_manifest(observations: list[dict[str, Any]]) -> bytes:
    """Serialize hand-assembled, curated observations deterministically.

    These records are declared inputs, not a manifest produced by the client."""
    return (
        json.dumps(
            {"source_id": "sodir-factpages", "observations": observations},
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
