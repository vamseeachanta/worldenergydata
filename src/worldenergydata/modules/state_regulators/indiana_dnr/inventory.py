"""Map official Indiana records without inferring missing well attributes.

Schema and table identifiers: Indiana GIS, OilAndGasWells FeatureServer,
layers 0 (wells), 1 (completions), 2 (image catalogue), inspected 2026-10-20:
https://gisdata.in.gov/server/rest/services/Hosted/OilAndGasWells/FeatureServer
The misspelling ``totaldepthloggeer`` is the published field name. Depth units,
status-code meanings, API numbers and spud dates are not specified there.
"""

from __future__ import annotations

import copy
import re
from collections import defaultdict
from datetime import datetime
from typing import Any

from ..fetch.policy import origin_of

SERVICE_URL = (
    "https://gisdata.in.gov/server/rest/services/Hosted/OilAndGasWells/FeatureServer"
)
# Matching policy from issue #1129's published research, section 3 (2026-10-12).
# These are text tokens, not engineering coefficients or entity-identity proof.
ENTITY_SUFFIXES = {
    "INC",
    "INCORPORATED",
    "LLC",
    "CORP",
    "CORPORATION",
    "CO",
    "COMPANY",
    "LTD",
    "LP",
}
# Indiana DNR, State Form 56442, Part II: lease/production unit, list of permits,
# monthly oil and gas totals; https://forms.in.gov/Download.aspx?id=13638
PRODUCTION_NOTE = (
    "Indiana annual production is reported per lease; this inventory contains no "
    "production data and supports no well-level production claim. Lease-level "
    "figures require separate filings; statewide totals cannot be allocated to wells."
)


def normalize_operator(name: str) -> str:
    """Return a candidate-match stem; preserve every original spelling in output."""
    text = name.upper().replace("&", " AND ")
    text = re.sub(r"\b(?:[A-Z]\.){2,}", lambda m: m.group().replace(".", ""), text)
    tokens = re.sub(r"[\W_]+", " ", text, flags=re.UNICODE).split()
    while tokens and tokens[-1] in ENTITY_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def features(value: Any) -> list[dict]:
    """Accept feature arrays or complete ArcGIS query responses; reject errors."""
    if isinstance(value, dict):
        if "error" in value:
            raise ValueError("ArcGIS returned an error; no inventory was produced")
        if value.get("exceededTransferLimit"):
            raise ValueError("ArcGIS response is truncated; collect remaining pages")
        value = value.get("features")
    if not isinstance(value, list) or any(
        not isinstance(f, dict) or not isinstance(f.get("attributes"), dict)
        for f in value
    ):
        raise ValueError("Expected ArcGIS features with attributes")
    return value


def _key(value: Any) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip()
    return str(int(text)) if text.isdecimal() else text


def _required_key(value: Any, name: str) -> str:
    key = _key(value)
    if key is None:
        raise ValueError(f"Missing {name}")
    return key


def _group(rows: list[dict], field: str) -> dict[str, list[dict]]:
    result = defaultdict(list)
    seen = set()
    for feature in rows:
        oid = _required_key(feature["attributes"].get("objectid"), "related objectid")
        if oid in seen:
            raise ValueError("Duplicate related objectid")
        seen.add(oid)
        key = _required_key(feature["attributes"].get(field), field)
        result[key].append(feature)
    return result


def _source(source: str, layer: int, attributes: dict, captured: str) -> dict:
    return {
        "url": f"{source}/{layer}",
        "objectid": attributes.get("objectid"),
        "captured_at": captured,
    }


def _supplements(rows: list[dict]) -> dict[str, dict]:
    result = {}
    for row in rows:
        key = _required_key(row.get("igs_id"), "supplement igs_id")
        if key in result:
            raise ValueError("Duplicate supplement igs_id")
        if not isinstance(row.get("source_record"), dict) or not row["source_record"]:
            raise ValueError("Every supplement requires a source_record")
        _required_key(row.get("permit_no"), "supplement permit_no")
        for field in ("api_number", "contract_operator", "spud_date"):
            if row.get(field) is not None and not isinstance(row[field], str):
                raise ValueError(f"Supplement {field} must be a string")
        for field in ("completion_zones", "formation_tops"):
            if field in row and not isinstance(row[field], list):
                raise ValueError(f"Supplement {field} must be a list")
        result[key] = row
    return result


def build_inventory(snapshot: dict, *, operator: str) -> dict:
    """Select matching permit records and join completions/images by official keys.

    This is a name-based candidate list, not proof that similarly named legal
    entities are identical. Supplied crosswalks require both IGS and permit keys.
    No production, contract-operator or plugging-obligation inference is made.
    """
    stem = normalize_operator(operator)
    if not stem:
        raise ValueError("A nonempty operator stem is required")
    source = snapshot["source_url"].rstrip("/")
    origin_of(source)
    captured = snapshot["captured_at"]
    if datetime.fromisoformat(captured.replace("Z", "+00:00")).utcoffset() is None:
        raise ValueError("captured_at must include a timezone")
    wells = features(snapshot["wells"])
    completions = _group(features(snapshot.get("completions", [])), "igs_id")
    images = _group(features(snapshot.get("images", [])), "permit_int")
    supplements = _supplements(snapshot.get("supplements", []))
    selected, identities, objectids = [], set(), set()
    for feature in wells:
        attrs = feature["attributes"]
        key = _required_key(attrs.get("igs_id"), "well igs_id")
        if _key(attrs.get("igs_int")) not in (None, key):
            raise ValueError("Well IGS relationship key disagrees with igs_id")
        oid = _required_key(attrs.get("objectid"), "well objectid")
        if key in identities or oid in objectids:
            raise ValueError("Duplicate well identity in snapshot")
        identities.add(key)
        objectids.add(oid)
        if normalize_operator(attrs.get("operator_name") or "") != stem:
            continue
        extra = supplements.get(key, {})
        if extra and _key(extra["permit_no"]) != _key(attrs.get("permit_number")):
            raise ValueError("Supplement permit does not match well permit")
        selected.append(
            _well(
                feature,
                key,
                extra,
                completions,
                images,
                source,
                captured,
                snapshot.get("spatial_reference"),
            )
        )
    with_api = sum(w["api_number"] is not None for w in selected)
    return {
        "operator_query": operator,
        "operator_stem": stem,
        "operator_spellings": sorted({w["operator_of_record"] for w in selected}),
        "matching_note": "Normalised-name candidates; legal entity identity is unverified.",
        "synthetic": snapshot.get("synthetic", False),
        "source_url": source,
        "captured_at": captured,
        "source_pages": copy.deepcopy(snapshot.get("source_pages", [])),
        "wells": selected,
        "coverage": {
            "scope": "supplied snapshot only; not statewide completeness",
            "input_wells": len(wells),
            "matched_wells": len(selected),
            "with_api_number": with_api,
            "without_api_number": len(selected) - with_api,
            "with_completions": sum(bool(w["completions"]) for w in selected),
            "with_image_catalogue": sum(bool(w["image_catalogue"]) for w in selected),
            "with_completion_zones": sum(bool(w["completion_zones"]) for w in selected),
            "with_formation_tops": sum(bool(w["formation_tops"]) for w in selected),
            "tables_not_supplied": [
                t for t in ("completions", "images") if t not in snapshot
            ],
        },
        "production_granularity": "NOT_EVALUATED",
        "production_note": PRODUCTION_NOTE,
    }


def _well(feature, key, extra, completions, images, source, captured, spatial_ref):
    attrs = feature["attributes"]
    completed = [
        {
            "reported": copy.deepcopy(f["attributes"]),
            "source_record": _source(source, 1, f["attributes"], captured),
        }
        for f in completions.get(key, [])
    ]
    catalogue = [
        {
            **copy.deepcopy(f["attributes"]),
            "source_record": _source(source, 2, f["attributes"], captured),
        }
        for f in images.get(_key(attrs.get("permit_int")), [])
    ]
    result = {
        "igs_id": attrs["igs_id"],
        "api_number": extra.get("api_number") or None,
        "permit_no": attrs.get("permit_number"),
        "operator_of_record": attrs.get("operator_name"),
        "contract_operator": extra.get("contract_operator"),
        "lease_name": attrs.get("lease_name"),
        "well_number": attrs.get("well_number"),
        "county": attrs.get("county"),
        "location": {
            "geometry": copy.deepcopy(feature.get("geometry")),
            "spatial_reference": copy.deepcopy(spatial_ref),
            "reported": {
                k: attrs.get(k)
                for k in (
                    "utmx",
                    "utmy",
                    "township",
                    "range",
                    "land_type",
                    "land_number",
                    "twp_direction",
                    "rng_direction",
                    "method",
                )
            },
        },
        "well_status": attrs.get("status"),
        "current_status": attrs.get("currentstat"),
        "class_ii": attrs.get("classii"),
        "idle_status": "NOT_EVALUATED",
        "plugging_obligation": "NOT_EVALUATED",
        "total_depth": [
            {
                "driller": c["reported"].get("totaldepthdriller"),
                "logger": c["reported"].get("totaldepthloggeer"),
                "unit": None,
            }
            for c in completed
        ],
        "completion_zones": copy.deepcopy(extra.get("completion_zones", [])),
        "formation_tops": copy.deepcopy(extra.get("formation_tops", [])),
        "spud_date": extra.get("spud_date"),
        "completion_dates": [
            c["reported"]["compdate"]
            for c in completed
            if c["reported"].get("compdate")
        ],
        "completions": completed,
        "scan_count_reported": attrs.get("scancount"),
        "scan_status_reported": attrs.get("scanstat"),
        "image_catalogue": catalogue,
        "image_note": "Catalogue only; imaged PDFs were not downloaded or interpreted.",
        "source_record": _source(source, 0, attrs, captured),
        "supplement_source_record": copy.deepcopy(extra.get("source_record")),
    }
    result["not_evaluated"] = [
        field
        for field in (
            "api_number",
            "contract_operator",
            "completion_zones",
            "formation_tops",
            "spud_date",
        )
        if not result[field]
    ] + ["idle_status", "plugging_obligation", "depth_units", "status_code_meaning"]
    return result
