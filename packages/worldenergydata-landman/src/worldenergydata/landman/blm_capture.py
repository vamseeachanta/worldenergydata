"""Bounded BLM raw capture; no normalization or completeness qualification."""

import json
import re
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import httpx

LAYER_URL = (
    "https://nlsdbpubgis.blm.gov/arcgis/rest/services/Fluid_Minerals/"
    "Oil_Gas_Leases_Case_Disp/MapServer/0"
)
MAX_RECORDS = 10
MAX_BYTES = 1_000_000
QUERY_URL = (
    LAYER_URL
    + "/query?"
    + urlencode(
        {
            "f": "json",
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "false",
            "orderByFields": "OBJECTID",
            "resultRecordCount": str(MAX_RECORDS),
        }
    )
)


@dataclass(frozen=True)
class Evidence:
    """Caller-reviewed terms evidence; a declaration, not automatic permission."""

    kind: str
    terms_url: str
    terms_note: str
    access_note: str
    checked_at: datetime
    retention: str


def _utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("An aware timestamp is required")
    if value > datetime.now(timezone.utc):
        raise ValueError("Future evidence is invalid")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_evidence(evidence: Evidence, *, live: bool = False) -> dict:
    if evidence.kind not in {"public", "synthetic"}:
        raise ValueError("Unknown evidence kind")
    if live and evidence.kind != "public":
        raise ValueError("Live requests require public access evidence")
    terms = urlsplit(evidence.terms_url)
    if (
        terms.scheme != "https"
        or not terms.hostname
        or terms.username is not None
        or terms.password is not None
        or terms.port is not None
        or terms.query
        or terms.fragment
        or not (terms.hostname == "blm.gov" or terms.hostname.endswith(".blm.gov"))
    ):
        raise ValueError("A credential-free publisher terms reference is required")
    if evidence.retention != "permitted" or not evidence.terms_note.strip():
        raise ValueError("Recorded payload retention permission is required")
    if not evidence.access_note.strip():
        raise ValueError("Recorded publisher access evidence is required")
    return {
        "kind": evidence.kind,
        "publisher": "Bureau of Land Management",
        "metadata_url": LAYER_URL + "?f=pjson",
        "url": QUERY_URL,
        "terms_url": evidence.terms_url,
        "terms_note": evidence.terms_note,
        "access_note": evidence.access_note,
        "checked_at": _utc(evidence.checked_at),
        "retention": evidence.retention,
    }


def _unique_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON member")
        result[key] = value
    return result


def _invalid_constant(value: str):
    raise ValueError("Non-finite JSON value")


def _payload(raw: bytes) -> dict:
    if len(raw) > MAX_BYTES:
        raise ValueError("Response exceeds byte cap")
    data = json.loads(
        raw, object_pairs_hook=_unique_object, parse_constant=_invalid_constant
    )
    if not isinstance(data, dict) or "error" in data:
        raise ValueError("Invalid response or service error")
    features = data.get("features")
    if not isinstance(features, list) or len(features) > MAX_RECORDS:
        raise ValueError("Missing feature list or record cap exceeded")
    if any(
        not isinstance(feature, dict) or not isinstance(feature.get("attributes"), dict)
        for feature in features
    ):
        raise ValueError("Invalid feature attributes")
    if (
        "exceededTransferLimit" in data
        and type(data["exceededTransferLimit"]) is not bool
    ):
        raise ValueError("Invalid transfer-limit flag")
    return data


def _destination(root: Path, capture_id: str) -> Path:
    root = Path(root)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", capture_id):
        raise ValueError("Capture identifier must be one portable path segment")
    if ".." in root.parts or any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError("Traversal and symlink destinations are forbidden")
    return root / capture_id


def write_capture(
    root: Path,
    capture_id: str,
    raw: bytes,
    *,
    evidence: Evidence,
    request_url: str = QUERY_URL,
) -> Path:
    """Create a new bundle; an existing capture is never replaced.

    A failed disk write may leave an incomplete directory. No completion
    manifest is written until the raw response has passed readback.
    """
    if request_url != QUERY_URL:
        raise ValueError("Only the fixed public query is supported")
    source = _validate_evidence(evidence)
    data = _payload(raw)
    destination = _destination(root, capture_id)
    destination.mkdir(parents=True, exist_ok=False)
    raw_path = destination / "response.json"
    with raw_path.open("xb") as stream:
        stream.write(raw)
    if raw_path.read_bytes() != raw:
        raise OSError("Raw capture readback mismatch")
    manifest = {
        "schema_version": 1,
        "status": "captured",
        "coverage": "partial",
        "captured_at": _utc(datetime.now(timezone.utc)),
        "source": source,
        "record_cap": MAX_RECORDS,
        "record_count": len(data["features"]),
        "exceeded_transfer_limit": data.get("exceededTransferLimit"),
        "raw": {
            "path": "response.json",
            "sha256": sha256(raw).hexdigest(),
            "size_bytes": len(raw),
        },
    }
    text = json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n"
    manifest_path = destination / "manifest.json"
    with manifest_path.open("x", encoding="utf-8") as stream:
        stream.write(text)
    if manifest_path.read_text(encoding="utf-8") != text:
        raise OSError("Manifest readback mismatch")
    return destination


def fetch_capture(
    root: Path,
    capture_id: str,
    *,
    evidence: Evidence,
    client: httpx.Client | None = None,
) -> Path:
    """Opt in to one request, without redirects, retries or pagination.

    An injected client supports offline transport tests. Permission evidence
    must be reviewed by the caller before invoking this function.
    """
    _validate_evidence(evidence, live=True)
    destination = _destination(root, capture_id)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Capture already exists")
    context = httpx.Client(trust_env=False) if client is None else nullcontext(client)
    with context as transport:
        with transport.stream(
            "GET", QUERY_URL, timeout=15.0, follow_redirects=False
        ) as response:
            response.raise_for_status()
            raw = bytearray()
            for chunk in response.iter_bytes(chunk_size=65_536):
                if len(raw) + len(chunk) > MAX_BYTES:
                    raise ValueError("Response exceeds byte cap")
                raw.extend(chunk)
    return write_capture(root, capture_id, bytes(raw), evidence=evidence)
