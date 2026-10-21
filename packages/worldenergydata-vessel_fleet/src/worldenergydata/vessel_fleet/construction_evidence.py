"""Sourced construction-vessel evidence, offline ingest and pipelay shortlists.

The historical CSV is a roster, not verification of its engineering values.
Queries use only the linked evidence bundle. Results are screening candidates,
not confirmation of availability or suitability for a particular installation.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import math
import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

DATA_DIR = Path(__file__).resolve().parent / "_data" / "curated"
EVIDENCE_NAME = "construction_evidence.json"
CRANE_NAME = "construction_crane_ratings.csv"
MANIFEST_NAME = "construction_evidence_manifest.json"
_METHODS = {"s-lay", "j-lay", "reel-lay", "flex-lay", "tow"}
_FACTS = ("imo", "current_name", "owner", "operator", "status")
_UNITS = {
    "capacity_t": "metric tonnes",
    "radius_min_m": "metres",
    "radius_max_m": "metres",
    "tension_t": "metric tonnes",
}
_CRANE_COLUMNS = (
    "vessel_name",
    "crane",
    "mode",
    "capacity_t",
    "radius_kind",
    "radius_min_m",
    "radius_max_m",
    "evidence_kind",
    "source_id",
    "locator",
    "source_url",
    "retrieved_at",
    "value_quote",
)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _number(value, *, zero=False):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and (value >= 0 if zero else value > 0)
    )


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _citation(item, sources, *, identity=False):
    _require(isinstance(item, dict), "Citation must be an object")
    source = sources.get(item.get("source_id"))
    _require(source is not None, "Unknown source")
    _require(_text(item.get("locator")), "Missing source locator")
    if identity:
        quote = source.get("quotes", {}).get(item.get("quote_key"))
        _require(_text(quote), "Missing identity quotation")


def _validate_sources(sources):
    _require(isinstance(sources, dict) and sources, "Missing sources")
    for source in sources.values():
        _require(isinstance(source, dict), "Source must be an object")
        url = urlparse(source.get("url", ""))
        _require(url.scheme == "https" and bool(url.netloc), "Invalid source URL")
        for field in ("sha256", "refetch_sha256"):
            _require(
                bool(re.fullmatch(r"[0-9a-f]{64}", source.get(field, ""))),
                "Invalid source digest",
            )
        try:
            retrieved = datetime.fromisoformat(source["retrieved_at"])
            refetched = datetime.fromisoformat(source["refetched_at"])
            valid = retrieved.tzinfo is not None and refetched >= retrieved
        except (KeyError, ValueError, TypeError):
            valid = False
        _require(valid, "Invalid source date")
        _require(_number(source.get("size_bytes")), "Invalid source size")
        _require(_text(source.get("publisher")), "Missing source publisher")
        _require(
            source.get("refetch_verified") is True, "Source not verified on re-fetch"
        )
        _require(
            source.get("copy_permitted", True) is True, "Source copying restricted"
        )


def _validate_vessel(row, sources, seen_imos):
    _require(_text(row.get("provenance")), "Missing record provenance")
    _require(row.get("hull_model") == "none", "Unverified hull link")
    identity_status = row.get("identity_status")
    _require(
        identity_status in {"unresolved", "partial", "resolved"},
        "Invalid identity status",
    )
    for field in _FACTS:
        _require(field in row, "Missing identity field")
        fact = row[field]
        if fact is None:
            continue
        _citation(fact, sources, identity=True)
        _require(_text(fact.get("value")), "Invalid identity value")
    imo = row["imo"]
    if imo is not None:
        value = imo["value"]
        _require(bool(re.fullmatch(r"[0-9]{7}", value)), "Invalid IMO format")
        quote = sources[imo["source_id"]]["quotes"][imo["quote_key"]]
        _require(
            bool(re.search(r"(?<![0-9])" + value + r"(?![0-9])", quote)),
            "IMO absent from cited quotation",
        )
        _require(value not in seen_imos, "Duplicate IMO")
        seen_imos.add(value)
    if row["status"]:
        _require(
            row["status"]["value"] in {"active", "laid_up", "scrapped"},
            "Invalid lifecycle status",
        )
    present = any(row[field] is not None for field in _FACTS)
    complete = all(
        row[field] is not None for field in ("imo", "current_name", "status")
    )
    complete = complete and (row["owner"] is not None or row["operator"] is not None)
    expected = "resolved" if complete else "partial" if present else "unresolved"
    _require(identity_status == expected, "Identity disposition conflicts with facts")
    for field in ("aka", "candidates", "pipelay"):
        _require(isinstance(row.get(field), list), f"Missing {field} list")
    if identity_status == "unresolved":
        _validate_research(row)
    for item in row["aka"] + row["candidates"]:
        _citation(item, sources, identity=True)
        _require(_text(item.get("value")), "Invalid alternate name")
    for capability in row["pipelay"]:
        _citation(capability, sources)
        _require(capability.get("method") in _METHODS, "Invalid lay method")
        _require(_number(capability.get("tension_t")), "Invalid lay tension")
        _require(_text(capability.get("rating_basis")), "Missing lay rating basis")
        _require(_text(capability.get("value_quote")), "Missing printed lay value")


def _validate_research(row):
    searches = row.get("searched")
    _require(isinstance(searches, list), "Missing searched list")
    expected = "researched, unresolved" if searches else "not researched"
    _require(
        row.get("limitation") == expected,
        "Research disposition conflicts with searches",
    )
    for attempt in searches:
        _require(isinstance(attempt, dict), "Search attempt must be an object")
        url = urlparse(attempt.get("url", ""))
        _require(url.scheme == "https" and bool(url.netloc), "Invalid searched URL")
        try:
            value = attempt.get("date")
            valid = (
                isinstance(value, str)
                and date.fromisoformat(value).isoformat() == value
            )
        except (TypeError, ValueError):
            valid = False
        _require(valid, "Invalid search date")
        _require(_text(attempt.get("outcome")), "Missing search outcome")
        _require(_text(attempt.get("locator")), "Missing search locator")
    _require(bool(searches) or not row["candidates"], "Unresearched row has candidates")
    if not row["candidates"]:
        summary = "not researched"
        if searches:
            sources = "; ".join(attempt["url"] for attempt in searches)
            summary = "no candidate found in " + sources
        _require(
            row.get("candidate_summary") == summary,
            "Invalid candidate summary for research disposition",
        )


def _validate_cranes(cranes, names, sources):
    _require(isinstance(cranes, list), "Missing crane table")
    seen = set()
    for row in cranes:
        _require(row.get("vessel_name") in names, "Crane vessel not in roster")
        _citation(row, sources)
        _require(
            row.get("evidence_kind") in {"printed_table", "printed_text"},
            "Crane value is not printed evidence",
        )
        _require(_text(row.get("value_quote")), "Missing printed crane value")
        _require(
            _text(row.get("crane")) and _text(row.get("mode")),
            "Missing crane configuration",
        )
        _require(_number(row.get("capacity_t")), "Invalid crane capacity")
        lo, hi = row.get("radius_min_m"), row.get("radius_max_m")
        _require(_number(hi), "Invalid crane radius")
        kind = row.get("radius_kind")
        valid = kind == "up_to" and lo is None
        if kind in {"point", "interval"}:
            valid = _number(lo) and lo <= hi
            valid = valid and (lo == hi if kind == "point" else lo < hi)
        _require(valid, "Invalid crane radius interval")
        key = tuple(row.get(k) for k in _CRANE_COLUMNS[:7])
        _require(key not in seen, "Duplicate crane rating")
        seen.add(key)


def validate_evidence(bundle, roster_path=None):
    """Reject incomplete provenance, invalid units/ranges and roster drift.

    Unknown identity fields must be null. ``none`` means no confirmed hull link;
    future positive links require an explicit extension of this reviewed contract.
    """
    _require(
        isinstance(bundle, dict) and bundle.get("schema_version") == 1,
        "Invalid schema version",
    )
    sources = bundle.get("sources")
    _validate_sources(sources)
    rows = bundle.get("vessels")
    _require(isinstance(rows, list) and rows, "Missing vessels")
    roster = Path(roster_path) if roster_path else DATA_DIR / "construction_vessels.csv"
    with roster.open(encoding="utf-8", newline="") as stream:
        expected = [row["VESSEL_NAME"] for row in csv.DictReader(stream)]
    names = [row.get("vessel_name") for row in rows]
    _require(
        names == expected and len(names) == len(set(names)),
        "Roster coverage or uniqueness mismatch",
    )
    seen_imos = set()
    for row in rows:
        _validate_vessel(row, sources, seen_imos)
    _validate_cranes(bundle.get("cranes"), set(names), sources)


def _json_bytes(value):
    return (
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def _crane_bytes(bundle):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=_CRANE_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in bundle["cranes"]:
        source = bundle["sources"][row["source_id"]]
        writer.writerow(
            {**row, "source_url": source["url"], "retrieved_at": source["retrieved_at"]}
        )
    return stream.getvalue().encode("utf-8")


def _source_manifest(bundle):
    fields = (
        "url",
        "publisher",
        "retrieved_at",
        "size_bytes",
        "sha256",
        "refetched_at",
        "refetch_sha256",
        "raw_disposition",
    )
    return {
        sid: {field: source[field] for field in fields}
        for sid, source in bundle["sources"].items()
    }


def ingest_evidence(bundle, output_dir, *, roster_path=None):
    """Validate reviewed evidence and deterministically write the linked dataset.

    This operation is offline. It does not discover sources, infer identity or modify
    the historical CSV/Parquet. Validation completes before the first output write.
    """
    validate_evidence(bundle, roster_path)
    outputs = {EVIDENCE_NAME: _json_bytes(bundle), CRANE_NAME: _crane_bytes(bundle)}
    manifest = {
        "schema_version": 1,
        "record_count": len(bundle["vessels"]),
        "crane_rating_count": len(bundle["cranes"]),
        "source_count": len(bundle["sources"]),
        "sources": _source_manifest(bundle),
        "units": _UNITS.copy(),
        "files": {
            name: {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
            for name, raw in outputs.items()
        },
    }
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    for name, raw in outputs.items():
        (destination / name).write_bytes(raw)
    (destination / MANIFEST_NAME).write_bytes(_json_bytes(manifest))
    return manifest


def load_evidence(data_dir=None):
    """Read back all outputs and verify digests, counts and export equivalence."""
    directory = Path(data_dir) if data_dir else DATA_DIR
    manifest = json.loads((directory / MANIFEST_NAME).read_text(encoding="utf-8"))
    _require(manifest.get("schema_version") == 1, "Invalid manifest schema")
    _require(manifest.get("units") == _UNITS, "Invalid manifest units")
    _require(
        set(manifest.get("files", {})) == {EVIDENCE_NAME, CRANE_NAME},
        "Invalid manifest files",
    )
    for name, entry in manifest["files"].items():
        raw = (directory / name).read_bytes()
        _require(
            hashlib.sha256(raw).hexdigest() == entry["sha256"], "Output digest mismatch"
        )
        _require(len(raw) == entry["size_bytes"], "Output size mismatch")
    bundle = json.loads((directory / EVIDENCE_NAME).read_text(encoding="utf-8"))
    validate_evidence(bundle)
    _require(
        manifest.get("sources") == _source_manifest(bundle),
        "Manifest source metadata differs from evidence",
    )
    for key, count in (
        ("record_count", len(bundle["vessels"])),
        ("crane_rating_count", len(bundle["cranes"])),
        ("source_count", len(bundle["sources"])),
    ):
        _require(manifest.get(key) == count, "Manifest count mismatch")
    _require(
        (directory / CRANE_NAME).read_bytes() == _crane_bytes(bundle),
        "Crane export differs from evidence",
    )
    return bundle


def find_by_imo(imo, *, bundle=None):
    """Return an accepted identity by its exact IMO string, or None.

    The existing evidence contract requires seven ASCII digits and a cited
    quotation. This lookup does not establish registry or checksum validity.
    Candidate identifiers and legacy roster values never qualify. The detached
    result retains identity limitations, provenance and the hull disposition.
    """
    _require(
        isinstance(imo, str) and bool(re.fullmatch(r"[0-9]{7}", imo)),
        "IMO must be a seven-digit ASCII string",
    )
    evidence = load_evidence() if bundle is None else bundle
    validate_evidence(evidence)
    for row in evidence["vessels"]:
        if row["imo"] is not None and row["imo"]["value"] == imo:
            return copy.deepcopy(row)
    return None


def screen_crane(
    vessel_name, *, crane, mode, radius_m, minimum_capacity_t, bundle=None
):
    """Screen one named hoist/configuration using printed evidence only.

    MATCH and BELOW_CAPACITY describe the printed rating, not operational
    suitability. A point covers only its exact radius; a bounded interval
    covers its inclusive bounds. An up_to rating excludes its printed endpoint
    as well as its unbounded interior. No interpolation, extrapolation, tandem
    sum or assumed lower bound is applied. Missing or conflicting coverage is
    NOT_EVALUATED. Identity limitations and source metadata accompany results.

    Interval semantics follow the Main Hoist Capacity table in the 2021
    equipment folder referenced by the bundle's sources:
    https://www.heerema.com/hubfs/HMC%20Equipment%20Folder_20211108.pdf?hsLang=en
    The comparison capacity >= caller demand is a screening predicate, not a
    design acceptance limit. The caller supplies radius and demand in m and t.
    """
    for name, value in (("vessel", vessel_name), ("crane", crane), ("mode", mode)):
        _require(_text(value), f"Missing {name} selection")
    _require(_number(radius_m), "Crane radius must be finite and positive")
    _require(
        _number(minimum_capacity_t, zero=True),
        "Minimum capacity must be finite and nonnegative",
    )
    evidence = load_evidence() if bundle is None else bundle
    validate_evidence(evidence)
    # Exact labels avoid merging configurations or roster spelling variants.
    vessels = [row for row in evidence["vessels"] if row["vessel_name"] == vessel_name]
    _require(bool(vessels), "Unknown vessel")
    selected_ratings = [
        rating
        for rating in evidence["cranes"]
        if rating["vessel_name"] == vessel_name
        and rating["crane"] == crane
        and rating["mode"] == mode
    ]
    ratings = []
    for rating in selected_ratings:
        lo, hi = rating["radius_min_m"], rating["radius_max_m"]
        if rating["radius_kind"] in {"point", "interval"} and lo <= radius_m <= hi:
            ratings.append(rating)

    result = {
        "evaluation": "NOT_EVALUATED",
        "reason": "No printed point or bounded interval covers the requested radius",
        "radius_m": radius_m,
        "minimum_capacity_t": minimum_capacity_t,
        "crane": crane,
        "mode": mode,
        "capacity_t": None,
        "vessel": copy.deepcopy(vessels[0]),
        "matched_ratings": copy.deepcopy(ratings),
        "sources": {
            sid: copy.deepcopy(evidence["sources"][sid])
            for sid in sorted({rating["source_id"] for rating in ratings})
        },
    }
    if not selected_ratings:
        result["reason"] = "No printed rating for the selected hoist and configuration"
        return result
    if not ratings:
        if any(
            rating["radius_kind"] == "up_to" and radius_m <= rating["radius_max_m"]
            for rating in selected_ratings
        ):
            result["reason"] = (
                "Unknown lower bound for up_to rating; its printed endpoint is also excluded"
            )
        return result
    capacities = {rating["capacity_t"] for rating in ratings}
    if len(capacities) != 1:
        result["reason"] = "Conflicting printed capacities cover the requested radius"
        return result
    capacity = capacities.pop()
    result["capacity_t"] = capacity
    if capacity >= minimum_capacity_t:
        result["evaluation"] = "MATCH"
        result["reason"] = "Printed capacity meets the requested screening demand"
    else:
        result["evaluation"] = "BELOW_CAPACITY"
        result["reason"] = "Printed capacity is below the requested screening demand"
    return result


def find_pipelay(method, minimum_tension_t, *, rating_basis=None, bundle=None):
    """Return sourced candidates with method-specific tension >= the minimum.

    Missing capacity never qualifies. Method matching ignores case and surrounding
    spaces, but does not equate distinct lay methods. Returned records are detached
    copies retaining identity limitations and the matched capability's provenance.
    Supply an exact ``rating_basis`` label to avoid comparing holding, dynamic and
    lay-tension ratings as equivalent. None preserves unqualified legacy screening;
    the matched basis is always retained and no basis conversion is performed.
    """
    method = method.strip().lower() if isinstance(method, str) else None
    _require(method in _METHODS, "Unknown lay method")
    _require(
        _number(minimum_tension_t, zero=True),
        "Minimum tension must be finite and nonnegative",
    )
    _require(rating_basis is None or _text(rating_basis), "Invalid lay rating basis")
    evidence = load_evidence() if bundle is None else bundle
    validate_evidence(evidence)
    result = []
    for row in evidence["vessels"]:
        for capability in row["pipelay"]:
            if (
                capability["method"] == method
                and (rating_basis is None or capability["rating_basis"] == rating_basis)
                and capability["tension_t"] >= minimum_tension_t
            ):
                result.append(
                    {
                        **copy.deepcopy(row),
                        "matched_capability": copy.deepcopy(capability),
                    }
                )
                break
    return result


def main():
    """Offline ingest: python -m worldenergydata.vessel_fleet.construction_evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="Reviewed evidence JSON")
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    manifest = ingest_evidence(bundle, args.output_dir)
    load_evidence(args.output_dir)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
