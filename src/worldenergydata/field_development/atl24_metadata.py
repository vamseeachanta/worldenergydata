"""Offline, allowlisted ATL24 discovery summaries; never acquires science data.

Input digests identify supplied bytes, not their origin. Declared source URLs
describe the expected queries; acquisition receipts must be retained separately.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from pathlib import Path

COLLECTIONS = {"001": "C3433822507-NSIDC_CPRD", "002": "C4085168939-NSIDC_CPRD"}
COLLECTION_ID = COLLECTIONS["002"]
BASE = "https://cmr.earthdata.nasa.gov/search/"
SOURCE_URLS = {
    "collections": BASE + "collections.umm_json?short_name=ATL24&page_size=10",
    "granules": BASE + f"granules.umm_json?collection_concept_id={COLLECTION_ID}&page_size=1",
    "atom": BASE + f"granules.atom?collection_concept_id={COLLECTION_ID}&page_size=1",
}
NS = {"a": "http://www.w3.org/2005/Atom",
      "e": "https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html#atom"}
UNVERIFIED = "UNVERIFIED"


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _items(raw):
    data = json.loads(raw, object_pairs_hook=_unique_object)
    items = data["items"]
    if not isinstance(items, list) or not items:
        raise ValueError("metadata items must be a nonempty list")
    ids = [item["meta"]["concept-id"] for item in items]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate concept ids")
    return items


def _revision(meta):
    value = meta["revision-date"]
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", value
    ):
        raise ValueError("invalid revision date")
    return value


def _collection(item):
    umm, meta = item["umm"], item["meta"]
    version = umm["Version"]
    if (umm["ShortName"] != "ATL24" or version not in COLLECTIONS
            or meta["concept-id"] != COLLECTIONS[version]
            or umm["DOI"]["DOI"] != f"10.5067/ATLAS/ATL24.{version}"):
        raise ValueError("collection identity/version/DOI mismatch")
    return {"concept_id": COLLECTIONS[version], "version": version,
            "doi": f"10.5067/ATLAS/ATL24.{version}", "revision": _revision(meta)}


def _select_collection(items):
    matches = [item for item in items if item["meta"]["concept-id"] == COLLECTION_ID]
    if len(matches) != 1:
        raise ValueError("exactly one selected collection is required")
    selected = matches[0]
    record = _collection(selected)
    if record["version"] != "002":
        raise ValueError("selected collection must be version 002")
    access = selected["umm"]["AccessConstraints"]["Description"].lower()
    required_clause = "provided that you are logged into your nasa earthdata profile"
    if required_clause not in " ".join(access.split()):
        raise ValueError("Earthdata authentication requirement not established")
    historical = [_collection(item) for item in items
                  if item["meta"]["concept-id"] == COLLECTIONS["001"]]
    return selected, record, historical


def _element(entry, path):
    elements = entry.findall(path, NS)
    if len(elements) != 1 or not elements[0].text:
        raise ValueError("missing or ambiguous Atom identity")
    return elements[0].text


def _atom_entry(raw):
    # CMR Atom has no DTD. Reject entities, including UTF-16 encoded declarations.
    if b"<!" in raw.replace(b"\x00", b"").upper():
        raise ValueError("XML declarations/entities are not supported")
    root = ET.fromstring(raw)
    if root.tag != f"{{{NS['a']}}}feed":
        raise ValueError("expected Atom feed")
    entries = root.findall("a:entry", NS)
    if len(entries) != 1:
        raise ValueError("exactly one Atom granule is required")
    return entries[0]


def _size(entry):
    elements = entry.findall("e:granuleSizeMB", NS)
    if not elements:
        return UNVERIFIED
    if len(elements) != 1:
        raise ValueError("ambiguous advertised size")
    text = elements[0].text or ""
    value = Decimal(text)
    if not value.is_finite() or value < 0:
        raise ValueError("invalid advertised size")
    return {"value": str(value), "unit": "MB", "source": "atom"}


def _sample(item, selected, entry):
    meta, umm = item["meta"], item["umm"]
    concept_id = meta["concept-id"]
    if not re.fullmatch(r"G\d+-NSIDC_CPRD", concept_id):
        raise ValueError("invalid granule concept id")
    if meta["collection-concept-id"] != COLLECTION_ID:
        raise ValueError("granule belongs to another collection")
    title = selected["umm"]["EntryTitle"]
    if umm["CollectionReference"]["EntryTitle"] != title:
        raise ValueError("UMM collection reference mismatch")
    identifiers = [i["Identifier"] for i in umm["DataGranule"]["Identifiers"]
                   if i["IdentifierType"] == "ProducerGranuleId"]
    if len(identifiers) != 1 or not re.fullmatch(
        r"ATL24_\d{14}_\d{8}_\d{3}_\d{2}_002_\d{2}\.h5", identifiers[0]
    ):
        raise ValueError("missing or ambiguous ATL24 version 002 filename")
    expected = {"a:id": concept_id, "a:title": umm["GranuleUR"],
                "e:collectionConceptId": COLLECTION_ID, "e:datasetId": title,
                "e:producerGranuleId": identifiers[0]}
    if any(_element(entry, path) != value for path, value in expected.items()):
        raise ValueError("UMM and Atom granule identities disagree")
    units = [info.get("SizeUnit") for info in
             umm["DataGranule"].get("ArchiveAndDistributionInformation", [])]
    unit = units[0] if len(units) == 1 and units[0] in {"MB", "KB", "GB", "Bytes"} else UNVERIFIED
    return {"concept_id": concept_id, "filename": identifiers[0],
            "revision": _revision(meta), "advertised_size": _size(entry),
            "umm_size_unit": unit, "payload_bytes": UNVERIFIED,
            "payload_sha256": UNVERIFIED}


def summarize(collections: bytes, granules: bytes, atom: bytes) -> dict:
    """Validate supplied evidence and emit only public discovery fields.

    Raises ValueError for malformed, missing, duplicate or conflicting evidence.
    Missing advertised size remains UNVERIFIED; no numerical inference is made.
    """
    try:
        selected, record, historical = _select_collection(_items(collections))
        items = _items(granules)
        if len(items) != 1:
            raise ValueError("exactly one UMM granule is required")
        sample = _sample(items[0], selected, _atom_entry(atom))
    except (KeyError, TypeError, AttributeError, IndexError, ValueError,
            ET.ParseError, InvalidOperation, UnicodeError) as exc:
        # Do not echo arbitrary metadata, local paths, contacts or access URLs.
        raise ValueError("invalid or inconsistent ATL24 metadata evidence") from exc
    inputs = {"collections": collections, "granules": granules, "atom": atom}
    return {"schema_version": 1, "metadata_only": True,
            "metadata_status": "identity_consistent",
            "collection": record, "historical_collections": historical,
            "sample": sample, "science_access": "earthdata_authentication_required",
            "science_acquisition": UNVERIFIED, "engineering_qualification": UNVERIFIED,
            "collection_storage": {"total_bytes": UNVERIFIED, "size_range": UNVERIFIED},
            "sources": {key: {"declared_url": SOURCE_URLS[key],
                              "sha256": hashlib.sha256(raw).hexdigest(),
                              "retrieval_status": UNVERIFIED}
                        for key, raw in inputs.items()}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("collections", "granules", "atom", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args(argv)
    inputs = [args.collections, args.granules, args.atom]
    if args.out.resolve() in {path.resolve() for path in inputs}:
        parser.exit(2, "output must not overwrite metadata evidence\n")
    try:
        summary = summarize(*(path.read_bytes() for path in inputs))
        args.out.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    except (ValueError, OSError):
        parser.exit(2, "ATL24 summary failed: check metadata evidence and file access\n")


if __name__ == "__main__":
    main()
