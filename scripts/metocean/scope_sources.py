#!/usr/bin/env python3
"""Validate and render frozen regional source observations without network I/O.

Regenerate with --input docs/research/metocean-adapter-scope.json --out-dir DIR.
Optional --evidence-dir verifies retained HTTP bodies named SOURCE_ID.body;
--repo-root defaults to this checkout and verifies local interface digests.
Embedded excerpts are checksummed independently. They are reviewed observations,
not a substitute for reopening a publisher's terms or inspecting dataset files.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import html
import json
import re
import zipfile
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

DATASETS = {"NORA3", "NorKyst800"}
METHOD_ROUTES = {
    "pot_extreme_selection": ["pyextremes"],
    "annual_max_selection": ["pandas"],
    "extreme_distribution_fitting": ["scipy.stats"],
    "cma_contours": ["virocon"],
    "three_parameter_weibull_moments": ["native"],
    "joint_distribution_Hs_Tp": ["native LoNoWe fit and contours"],
}
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
IDENTIFIER = re.compile(r"[a-zA-Z0-9_-]+\Z")
LICENCES = {"LGPL-2.1-or-later", "LGPL-2.1+"}
DATA_TERMS = {"CC-BY-4.0", "NLOD-2.0", "NLOD-2.0 AND CC-BY-4.0"}
STEM = "metocean-adapter-scope"


def require(condition, message):
    """Raise a stable, value-free validation error."""
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def valid_digest(value):
    return isinstance(value, str) and bool(SHA256.fullmatch(value))


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def utc_timestamp(value):
    require(nonempty(value), "retrieved_utc is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("retrieved_utc must be an ISO timestamp") from error
    require(
        parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0,
        "retrieved_utc must include UTC",
    )


def https_address(value):
    require(nonempty(value), "source_url is required")
    parsed = urlsplit(value)
    require(
        parsed.scheme == "https"
        and parsed.hostname
        and not parsed.username
        and not parsed.password
        and not parsed.query
        and not parsed.fragment,
        "source_url must be a credential-free HTTPS metadata address",
    )


def declaration_name(signature):
    """Parse a retained declaration header without executing package code."""
    try:
        tree = ast.parse(signature + "\n    pass\n")
    except (SyntaxError, TypeError) as error:
        raise ValueError("API signature must be a Python declaration header") from error
    require(
        len(tree.body) == 1
        and isinstance(tree.body[0], (ast.FunctionDef, ast.ClassDef))
        and len(tree.body[0].body) == 1
        and isinstance(tree.body[0].body[0], ast.Pass),
        "API evidence must contain only a declaration header",
    )
    return tree.body[0].name


class MetadataText(HTMLParser):
    """Collect metadata text without executing scripts or loading resources."""

    def __init__(self):
        super().__init__()
        self.chunks = []

    def handle_data(self, data):
        self.chunks.append(data)


def verify_excerpt(excerpt, body):
    """Bind a reviewed excerpt to its retained response or archive member."""
    if excerpt.get("archive_member"):
        with zipfile.ZipFile(body) as archive:
            raw = archive.read(excerpt["archive_member"])
        require(
            digest(raw) == excerpt.get("member_sha256"),
            "archive member digest mismatch",
        )
    else:
        raw = body.read_bytes()
    text = raw.decode("utf-8")
    extraction = excerpt.get("extraction", "text")
    if extraction == "json_fields":
        metadata = json.loads(text)
        values = {}
        for field in excerpt["fields"]:
            values[field] = metadata["info"][field]
        require(
            json.loads(excerpt["text"]) == values,
            "excerpt differs from retained source",
        )
        return
    if extraction == "html_text":
        parser = MetadataText()
        parser.feed(text)
        text = " ".join(parser.chunks)
    else:
        require(extraction == "text", "unknown excerpt extraction")
    segments = excerpt.get("segments", [excerpt["text"]])
    require("\n".join(segments) == excerpt["text"], "excerpt segments disagree")
    normalized = " ".join(text.split())
    require(
        all(" ".join(segment.split()) in normalized for segment in segments),
        "excerpt not found in retained source",
    )


def validate_document(document, *, repo_root=None, evidence_dir=None):
    """Reject unsupported or overstated claims; accept explicit blocked results.

    A digest authenticates consistency with retained bytes, not publisher identity.
    Claim-to-excerpt associations still require independent source review.
    """
    require(document.get("schema_version") == 1, "unsupported schema_version")
    require(
        type(document.get("validated_benchmark_count")) is int
        and document["validated_benchmark_count"] == 0,
        "source scope cannot claim validated benchmarks",
    )
    for field in ("title", "summary"):
        require(nonempty(document.get(field)), field + " is required")
    for field in ("scope", "inventory", "contract"):
        require(isinstance(document.get(field), dict) and document[field], field)
    revisions = document.get("revision_history")
    require(isinstance(revisions, list) and revisions, "revision_history is required")
    for revision in revisions:
        require(
            all(revision.get(key) for key in ("revision", "date", "change")),
            "revision_history entry is incomplete",
        )
    require(
        document.get("method_routes") == METHOD_ROUTES,
        "blanket delegation claims are prohibited; retain route-specific methods",
    )
    sources, excerpts = {}, {}
    require(isinstance(document.get("sources"), list), "sources must be a list")
    for source in document["sources"]:
        key = source.get("source_id")
        require(
            isinstance(key, str) and IDENTIFIER.fullmatch(key) and key not in sources,
            "source_id must be unique and safe",
        )
        https_address(source.get("source_url"))
        utc_timestamp(source.get("retrieved_utc"))
        require(
            type(source.get("http_status")) is int
            and (source["http_status"] == 0 or 100 <= source["http_status"] <= 599),
            "http_status is required",
        )
        require(
            type(source.get("command_exit")) is int and source["command_exit"] >= 0,
            "retrieval command_exit is required",
        )
        require(
            valid_digest(source.get("source_sha256"))
            or (
                "source_sha256" in source
                and source["source_sha256"] is None
                and source["command_exit"] != 0
            ),
            "source_sha256 is required for a retained body",
        )
        if evidence_dir is not None:
            body = Path(evidence_dir) / (key + ".body")
            if source["source_sha256"] is not None:
                require(body.is_file(), "retained retrieval body is missing")
                require(
                    digest(body.read_bytes()) == source["source_sha256"],
                    "source body digest mismatch",
                )
        sources[key] = source
        for excerpt in source.get("excerpts", []):
            eid = excerpt.get("excerpt_id")
            require(
                isinstance(eid, str) and IDENTIFIER.fullmatch(eid),
                "invalid excerpt_id",
            )
            ref = key + ":" + eid
            require(ref not in excerpts, "duplicate excerpt_id")
            require(nonempty(excerpt.get("locator")), "excerpt locator is required")
            require(nonempty(excerpt.get("text")), "excerpt text is required")
            require(
                digest(excerpt["text"].encode()) == excerpt.get("sha256"),
                "excerpt digest mismatch",
            )
            if evidence_dir is not None:
                verify_excerpt(excerpt, Path(evidence_dir) / (key + ".body"))
            excerpts[ref] = (key, excerpt)

    def evidence(refs, kind, provenance):
        require(isinstance(refs, list) and refs, kind + " evidence is required")
        found = []
        for ref in refs:
            require(ref in excerpts, kind + " evidence reference is missing")
            key, excerpt = excerpts[ref]
            require(key in provenance, kind + " evidence missing from provenance")
            require(excerpt.get("kind") == kind, kind + " evidence has wrong kind")
            require(
                sources[key]["http_status"] == 200
                and sources[key]["command_exit"] == 0,
                kind + " evidence retrieval was unsuccessful",
            )
            found.append(excerpt)
        return found

    seen = set()
    require(
        isinstance(document.get("records"), list) and document["records"], "records"
    )
    for record in document["records"]:
        dataset = record.get("dataset_id")
        require(
            dataset in DATASETS and dataset not in seen, "unsupported/duplicate dataset"
        )
        seen.add(dataset)
        require(record.get("package_name") == "metocean-api", "unsupported package")
        require(nonempty(record.get("package_version")), "package_version is required")
        require(record.get("readiness") in {"SCOPED", "BLOCKED"}, "invalid readiness")
        missing = record.get("missing_inputs")
        require(
            isinstance(missing, list) and all(nonempty(item) for item in missing),
            "missing_inputs must be a list of descriptions",
        )
        scoped = record["readiness"] == "SCOPED"
        require(
            not missing if scoped else bool(missing),
            "readiness/missing_inputs conflict",
        )
        require(
            not scoped or not document["contract"].get("missing_inputs"),
            "SCOPED cannot have unresolved contract inputs",
        )
        require(
            record.get("access_state") in {"METADATA_ONLY", "UNAVAILABLE"},
            "access_state must describe metadata access only",
        )
        provenance = record.get("provenance")
        require(
            isinstance(provenance, list)
            and provenance
            and all(key in sources for key in provenance),
            "provenance must reference retained retrievals",
        )
        require(
            any(
                all(
                    record.get(field) == sources[key][field]
                    for field in (
                        "source_url",
                        "retrieved_utc",
                        "http_status",
                        "source_sha256",
                    )
                )
                for key in provenance
            ),
            "record retrieval evidence differs from its source",
        )
        if scoped:
            require(record["access_state"] == "METADATA_ONLY", "retrieval unavailable")
            require(
                all(
                    sources[key]["http_status"] == 200
                    and sources[key]["command_exit"] == 0
                    for key in provenance
                ),
                "SCOPED retrieval must be successful",
            )
        for field in ("package_licence", "dataset_terms", "coverage"):
            claim = record.get(field)
            require(isinstance(claim, dict), field + " is required")
            require(claim.get("state") in {"CONFIRMED", "UNKNOWN", "AMBIGUOUS"}, field)
            if scoped:
                require(claim["state"] == "CONFIRMED", field + " is unconfirmed")
            if claim["state"] == "CONFIRMED":
                evidence(claim.get("evidence"), field, provenance)
                value = claim.get(
                    "description" if field == "coverage" else "expression"
                )
                require(nonempty(value), field + " licence/description is required")
                if field == "package_licence":
                    require(
                        value in LICENCES, "package licence is missing or ambiguous"
                    )
                if field == "dataset_terms":
                    require(
                        value in DATA_TERMS,
                        "dataset_terms licence is missing, ambiguous or unsupported",
                    )
                    require(
                        claim.get("redistribution") == "NOT_APPROVED",
                        "dataset_terms do not approve redistribution",
                    )
            else:
                require(
                    not claim.get("evidence"),
                    field + " unresolved evidence must be empty",
                )
        symbols = record.get("api_symbols")
        require(isinstance(symbols, list), "API symbols must be a list")
        require(not scoped or bool(symbols), "SCOPED requires API evidence")
        for symbol in symbols:
            matches = evidence(symbol.get("evidence"), "api", provenance)
            name = declaration_name(symbol.get("signature"))
            require(
                symbol.get("symbol", "").split(".")[-1] == name, "API symbol mismatch"
            )
            require(
                any(symbol["signature"] == match["text"] for match in matches),
                "API signature differs from retained declaration",
            )
            parent = symbol["symbol"].rsplit(".", 1)[0]
            require(
                "." not in symbol["symbol"]
                or any(parent in match["locator"] for match in matches),
                "API parent missing from source locator",
            )
    for interface in document.get("local_interfaces", []):
        relative = Path(interface.get("path", ""))
        require(
            not relative.is_absolute()
            and ".." not in relative.parts
            and relative.parts,
            "local interface path must be repository-relative",
        )
        require(
            valid_digest(interface.get("source_sha256")), "local source digest required"
        )
        if repo_root is not None:
            target = Path(repo_root) / relative
            require(target.is_file(), "local interface source is missing")
            require(
                digest(target.read_bytes()) == interface["source_sha256"],
                "local interface digest mismatch",
            )
    return document


def serialize_document(document):
    return (
        json.dumps(
            document, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False
        )
        + "\n"
    )


def render_html(document):
    """Render all reviewed fields, including evidence, with escaped content."""
    validate_document(document)

    def escaped(value):
        return html.escape(str(value), quote=True)

    def block(value):
        return "<pre>" + escaped(serialize_document(value)) + "</pre>"

    def prose(mapping):
        return (
            "<dl>"
            + "".join(
                "<dt><strong>"
                + escaped(key.replace("_", " ").capitalize())
                + "</strong></dt><dd>"
                + escaped(value)
                + "</dd>"
                for key, value in mapping.items()
            )
            + "</dl>"
        )

    counts = {
        state: sum(r["readiness"] == state for r in document["records"])
        for state in ("SCOPED", "BLOCKED")
    }
    parts = [
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>" + escaped(document["title"]) + "</title>",
        "<style>body{font:16px/1.6 system-ui;margin:2rem auto;max-width:76rem;",
        "padding:0 1rem;color:#172b3a}h1,h2{color:#164c63}pre{white-space:pre-wrap;",
        "overflow-wrap:anywhere;background:#f1f5f7;padding:1rem}table{border-collapse:",
        "collapse;width:100%}td,th{border:1px solid #b4c5cf;padding:.5rem;text-align:left}",
        "</style></head><body><h1>" + escaped(document["title"]) + "</h1>",
        "<h2>Summary</h2><p>" + escaped(document["summary"]) + "</p>",
        f'<p>SCOPED: {counts["SCOPED"]}; BLOCKED: {counts["BLOCKED"]}. '
        "Validated benchmarks: 0. Readiness is source scope only.</p>",
        "<h2>Revision history</h2><table><tr><th>Revision</th><th>Date</th><th>Change and reason</th></tr>",
    ]
    for revision in document["revision_history"]:
        parts.append(
            "<tr>"
            + "".join(
                "<td>" + escaped(revision[key]) + "</td>"
                for key in ("revision", "date", "change")
            )
            + "</tr>"
        )
    parts.append("</table><h2>Scope</h2>" + prose(document["scope"]))
    parts.append("<h2>Repository inventory</h2>" + prose(document["inventory"]))
    parts.append(
        "<details><summary>Local signatures and digests</summary>"
        + block(document["local_interfaces"])
        + "</details>"
    )
    parts.append(
        "<h2>Source observations</h2><table><tr><th>Dataset</th>"
        "<th>Package licence</th><th>Dataset terms</th><th>Readiness</th></tr>"
    )
    for record in document["records"]:
        parts.append(
            "<tr>"
            + "".join(
                "<td>" + escaped(value) + "</td>"
                for value in (
                    record["dataset_id"],
                    record["package_licence"].get("expression"),
                    record["dataset_terms"]["state"],
                    record["readiness"],
                )
            )
            + "</tr>"
        )
    parts.append("</table>")
    for record in document["records"]:
        parts.append(
            "<h3>"
            + escaped(record["dataset_id"])
            + " — "
            + escaped(record["readiness"])
            + "</h3><p>"
            + escaped(record["coverage"]["description"])
            + "</p>"
            + "<details><summary>Reviewed record and provenance</summary>"
            + block(record)
            + "</details>"
        )
    contract = document["contract"]
    parts.append(
        "<h2>Proposed contract</h2>"
        + prose(
            {key: value for key, value in contract.items() if isinstance(value, str)}
        )
    )
    if contract.get("field_mapping"):
        parts.append(
            "<table><tr><th>Upstream</th><th>Local field and unit</th>"
            "<th>State and unresolved input</th></tr>"
        )
        for row in contract["field_mapping"]:
            parts.append(
                "<tr>"
                + "".join(
                    "<td>" + escaped(value) + "</td>"
                    for value in (
                        row["upstream"],
                        row["local"] + " (" + row["local_unit"] + ")",
                        row["status"] + ": " + row["reason"],
                    )
                )
                + "</tr>"
            )
        parts.append("</table>")
    parts.append(
        "<details><summary>Complete proposed contract</summary>"
        + block(contract)
        + "</details>"
    )
    parts.append("<h2>Method boundaries</h2>" + block(document["method_routes"]))
    parts.append(
        "<h2>Unresolved inputs</h2>"
        + block({r["dataset_id"]: r["missing_inputs"] for r in document["records"]})
    )
    parts.append(
        "<h2>Retrieval evidence</h2><table><tr><th>Source</th><th>UTC</th>"
        "<th>HTTP / command exit</th><th>Retained body SHA-256</th></tr>"
    )
    for source in document["sources"]:
        parts.append(
            '<tr><td><a href="'
            + escaped(source["source_url"])
            + '">'
            + escaped(source["source_id"])
            + "</a></td><td>"
            + escaped(source["retrieved_utc"])
            + "</td><td>"
            + escaped(source["http_status"])
            + " / "
            + escaped(source["command_exit"])
            + "</td><td><code>"
            + escaped(source["source_sha256"])
            + "</code></td></tr>"
        )
    parts.append(
        "</table><details><summary>Frozen excerpts and retrieval metadata</summary>"
        + block(document["sources"])
        + "</details>"
    )
    if "historical_statistics_examples" in document:
        parts.append(
            "<h2>Historical example evidence boundary</h2>"
            + block(document["historical_statistics_examples"])
        )
    parts.append("<h2>Skipped</h2>" + block(document["skipped"]))
    parts.append("<h2>Known limits</h2>" + block(document["known_limits"]))
    return "\n".join(parts) + "\n</body></html>\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    parser.add_argument("--evidence-dir", type=Path)
    args = parser.parse_args()
    try:
        document = json.loads(args.input.read_text(encoding="utf-8"))
        validate_document(
            document, repo_root=args.repo_root, evidence_dir=args.evidence_dir
        )
        rendered = render_html(document)
    except (ValueError, OSError, TypeError, KeyError) as error:
        parser.exit(2, "Scope validation failed: " + type(error).__name__ + "\n")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / (STEM + ".json")).write_text(
        serialize_document(document), encoding="utf-8"
    )
    (args.out_dir / (STEM + ".html")).write_text(rendered, encoding="utf-8")
    print("Validated source records:", len(document["records"]))


if __name__ == "__main__":
    main()
