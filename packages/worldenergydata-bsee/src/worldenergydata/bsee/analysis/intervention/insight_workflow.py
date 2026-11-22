"""Read-only, aggregate-only seam for reviewed enriched WAR snapshots.

This is a local analysis bundle, not a publication or a replacement for the
upstream run-manifest/readiness contracts. Evidence is a caller attestation;
this module verifies its shape and content digest, not its authenticity.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
from datetime import date, datetime
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd

from .comprehensive_analyzer import ComprehensiveActivityAnalyzer

SOURCE_ID = "bsee-data-center"
COUNT_BASIS = (
    "ComprehensiveActivityAnalyzer._analyze_cross_activity: "
    "count rows with ACTIVITY_CATEGORY exactly drilling or intervention; "
    "other = total - drilling - intervention."
)
_REQUIRED = {
    "dataset_id",
    "version",
    "source_url",
    "source_class",
    "license",
    "review_state",
    "readiness",
    "data_as_of",
    "retrieved_at",
    "sha256",
    "derivation",
}


def _validate_source(payload: bytes, source: dict) -> dict:
    if not _REQUIRED.issubset(source):
        raise ValueError("Source evidence is incomplete")
    expected = {
        "source_class": "public-federal",
        "license": "public-domain",
        "review_state": "reviewed",
        "readiness": "ready",
        "derivation": "reviewed-enriched-war",
    }
    if any(source[key] != value for key, value in expected.items()):
        raise ValueError(
            "Only reviewed, ready, public-federal enriched WAR is supported"
        )
    for key in ("dataset_id", "version"):
        if not isinstance(source[key], str) or not re.fullmatch(
            r"[a-zA-Z0-9][a-zA-Z0-9_-]*", source[key]
        ):
            raise ValueError("Dataset identity must be an opaque slug")
    url = urlsplit(source["source_url"])
    if (
        url.scheme != "https"
        or url.netloc not in {"www.data.bsee.gov", "data.bsee.gov", "www.bsee.gov"}
        or url.query
        or url.fragment
    ):
        raise ValueError("Source citation must be a public BSEE HTTPS URL")
    try:
        vintage = date.fromisoformat(source["data_as_of"])
        retrieval = datetime.fromisoformat(
            source["retrieved_at"].replace("Z", "+00:00")
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Source dates must be ISO dates/timestamps") from exc
    if retrieval.tzinfo is None or vintage > retrieval.date():
        raise ValueError("Source vintage must precede a timezone-aware retrieval")
    if source["sha256"] != hashlib.sha256(payload).hexdigest():
        raise ValueError("Input digest mismatch")
    # Explicit projection: no caller paths, names or arbitrary extra metadata.
    return {key: source[key] for key in sorted(_REQUIRED)}


def build_bundle(
    payload: bytes, *, source: dict, code_ref: str, catalog_ref: str
) -> dict:
    """Summarize one caller-selected local CSV without modifying its inputs.

    The source must attest to the reviewed enrichment derivation and current
    readiness. No download, source discovery, solver, or publication is invoked.
    Code/catalog refs are required immutable Git/SHA-256 digests respectively.
    """
    provenance = _validate_source(payload, source)
    if not re.fullmatch(r"[0-9a-f]{40}", code_ref) or not re.fullmatch(
        r"[0-9a-f]{64}", catalog_ref
    ):
        raise ValueError("Immutable code and catalog digests are required")
    try:
        # Select only the grouping column before the existing analyzer sees data.
        frame = pd.read_csv(
            io.BytesIO(payload),
            dtype="string",
            usecols=lambda column: column in {"ACTIVITY_CATEGORY", "YEAR"},
        )
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Expected enriched WAR CSV with ACTIVITY_CATEGORY") from exc
    if frame.empty or "ACTIVITY_CATEGORY" not in frame:
        raise ValueError("Empty data cannot establish zero activity")
    metrics = _counts(frame)
    drilling = metrics["drilling_records"]
    intervention = metrics["intervention_records"]
    total = metrics["record_count"]
    years = frame.get("YEAR", pd.Series(pd.NA, index=frame.index, dtype="string"))
    # ISO 8601 calendar-year representation: four digits. No dates are inferred.
    years = years.where(years.str.fullmatch(r"[0-9]{4}").fillna(False))
    by_year = []
    for year in sorted(years.dropna().unique()):
        by_year.append({"year": str(year), **_counts(frame.loc[years == year])})
    if years.isna().any():
        by_year.append({"year": None, **_counts(frame.loc[years.isna()])})
    return {
        "schema_version": "well-operations-insights-v1",
        "scope": "caller-selected enriched WAR snapshot; aggregate records only",
        "publication_state": "blocked_pending_bundle_review",
        "source_id": SOURCE_ID,
        "source": provenance,
        "code_ref": code_ref,
        "catalog_ref": catalog_ref,
        "upstream_issues": [450, 451],
        "upstream_links": {
            "run_manifest": "https://github.com/vamseeachanta/worldenergydata/issues/450",
            "source_readiness": "https://github.com/vamseeachanta/worldenergydata/issues/451",
        },
        "metrics": metrics,
        "by_year": by_year,
        "method": COUNT_BASIS,
        "findings": [
            (
                f"The selected snapshot contains {total} records: {drilling} drilling, "
                f"{intervention} intervention, and {total - drilling - intervention} other."
            ),
        ],
        "checks": dict.fromkeys(
            ["production", "fdas", "hse", "duration", "population_coverage"],
            "NOT_EVALUATED",
        ),
        "limitations": [
            "Counts describe snapshot rows, not unique wells or operation durations.",
            "Unknown and missing activity categories remain other records.",
            "Year buckets use supplied YEAR labels; absent or invalid years remain undated.",
            "No all-available-data coverage, risk rate or causal conclusion is established.",
            "Classification and readiness are caller attestations, not independently verified.",
            "No production, FDAS or HSE inputs are consumed or joined.",
            "Operator and raw record fields are excluded; no operator-level HSE cuts are emitted.",
            "Upstream manifest/history integration and publication review remain required.",
        ],
        "next_probes": [
            "Verify snapshot coverage and freshness against the source-readiness contract.",
            "Reconcile enriched categories with the pinned raw WAR derivation.",
            "Classify production and FDAS sources before joining production context.",
            "Establish HSE provenance and aggregation rules before evaluating risk signals.",
        ],
    }


def _counts(frame: pd.DataFrame) -> dict:
    counts = ComprehensiveActivityAnalyzer(frame[["ACTIVITY_CATEGORY"]]).analyze()[
        "cross_activity"
    ]
    drilling = counts["drilling_count"]
    intervention = counts["intervention_count"]
    return {
        "record_count": len(frame),
        "drilling_records": drilling,
        "intervention_records": intervention,
        "other_records": len(frame) - drilling - intervention,
    }


def _json_bytes(value: dict) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode()


def write_bundle(bundle: dict, destination: Path) -> None:
    """Write a new local directory, refusing overwrite; hash every output.

    Local files are not a publication. A failed write may leave an incomplete
    directory, which must be inspected before retrying at a fresh destination.
    """
    destination = Path(destination)
    sections = []
    for title, entries in (
        ("Findings", bundle["findings"]),
        ("Limitations", bundle["limitations"]),
        ("Next probes", bundle["next_probes"]),
    ):
        items = "".join(f"<li>{escape(item)}</li>" for item in entries)
        sections.append(f"<h2>{title}</h2><ul>{items}</ul>")
    source = bundle["source"]
    html = (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        "<title>Well-operations snapshot analysis</title>"
        "<h1>Well-operations snapshot analysis</h1>"
        f"<p>{escape(bundle['scope'])}</p>"
        "<h2>Revision history</h2><table><tr><th>Revision</th><th>Date</th>"
        "<th>Change and reason</th></tr>"
        f"<tr><td>Initial</td><td>{escape(source['data_as_of'])}</td>"
        "<td>Snapshot analysis; source vintage shown, issue date not established.</td></tr>"
        "</table>"
        + "".join(sections)
        + "<h2>Counts by supplied year</h2><pre>"
        + escape(json.dumps(bundle["by_year"], indent=2))
        + "</pre>"
        + f"<h2>Method</h2><p>{escape(bundle['method'])}</p>"
        + f"<h2>Source</h2><p>{escape(source['source_url'])}</p>"
        + f"<p>Input SHA-256: {escape(source['sha256'])}</p>"
        + "<h2>Checks</h2><pre>"
        + escape(json.dumps(bundle["checks"], indent=2))
        + "</pre><p>Publication blocked pending bundle review.</p></html>"
    ).encode()
    outputs = {"insights.json": _json_bytes(bundle), "findings.html": html}
    manifest = {
        "schema_version": bundle["schema_version"],
        "source": source,
        "source_id": bundle["source_id"],
        "code_ref": bundle["code_ref"],
        "catalog_ref": bundle["catalog_ref"],
        "upstream_issues": bundle["upstream_issues"],
        "upstream_links": bundle["upstream_links"],
        "publication_state": bundle["publication_state"],
        "outputs": {
            name: hashlib.sha256(data).hexdigest() for name, data in outputs.items()
        },
    }
    destination.mkdir(parents=True, exist_ok=False)
    for name, data in {**outputs, "manifest.json": _json_bytes(manifest)}.items():
        path = destination / name
        with path.open("xb") as stream:
            stream.write(data)
        if path.read_bytes() != data:
            raise OSError("Bundle readback mismatch")


def main(argv: list[str] | None = None) -> int:
    """Run a bounded local snapshot analysis; no discovery or publication."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--code-ref", required=True)
    parser.add_argument("--catalog-ref", required=True)
    args = parser.parse_args(argv)
    source = json.loads(args.source.read_text(encoding="utf-8"))
    if not isinstance(source, dict):
        raise TypeError("Source evidence must be an object")
    bundle = build_bundle(
        args.input.read_bytes(),
        source=source,
        code_ref=args.code_ref,
        catalog_ref=args.catalog_ref,
    )
    write_bundle(bundle, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
