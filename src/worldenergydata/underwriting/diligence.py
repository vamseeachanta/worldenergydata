"""Build diligence packs from explicitly cleared, normalized evidence.

Contract basis: #916 acceptance criteria and #910--#915 source boundaries.
No engineering equation, conversion factor or acceptance limit is applied.
Observation counts are row counts, never well counts or coverage estimates.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime, timezone
from html import escape
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

SECTIONS = {
    "asset_location": "Asset/location",
    "wells": "Wells",
    "production": "Production",
    "pressure": "Pressure/depletion",
    "permits_completions": "Permits/completions",
    "infrastructure": "Infrastructure",
    "hse": "HSE/environmental overlays",
    "lease_title_mineral": "Lease/title/mineral availability",
}
REFERENCE_LABELS = {"Data inventory", "U.S. onshore matrix", "Source modules/issues"}
STATUSES = {
    "downloaded",
    "derived",
    "configured-only",
    "partial/error",
    "missing",
    "private/legacy",
}
KINDS = {"regulator", "lease", "title", "mineral", "infrastructure", "hse", "synthetic"}
CAUTIONS = {
    "asset_location": "Location observations do not establish a legal tract boundary.",
    "wells": "Observation counts are not a complete or deduplicated well census.",
    "production": (
        "Production is reported at its supplied scope and period; no well allocation is inferred."
    ),
    "pressure": (
        "No depletion estimate: pressure basis, datum, test type and comparability need review."
    ),
    "permits_completions": (
        "A permit or completion record does not establish current authorization."
    ),
    "infrastructure": (
        "Mapped infrastructure does not establish capacity, access rights or tie-in feasibility."
    ),
    "hse": "Missing overlay records are not evidence of environmental clearance.",
    "lease_title_mineral": (
        "No ownership or title conclusion is inferred from regulator or production data."
    ),
}


def _fields(record: dict, required: set, optional: set | None = None) -> None:
    if not isinstance(record, dict) or not required <= record.keys():
        raise ValueError("Missing required fields")
    if record.keys() - required - (optional or set()):
        raise ValueError("Unknown fields")


def _text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Expected nonempty text")
    return value


def _texts(value: object) -> list[str]:
    if not isinstance(value, list):
        raise TypeError("Expected text list")
    return [_text(item) for item in value]


def _day(value: object) -> date:
    return date.fromisoformat(_text(value))


def _url(value: object) -> str:
    value = _text(value)
    parsed = urlsplit(value)
    if (
        parsed.scheme in {"https", "http"}
        and parsed.hostname
        and not parsed.username
        and not parsed.password
        and not any(char.isspace() for char in value)
    ):
        return value
    # Repository-relative references are resolved by the renderer to its supplied
    # repository root. Local filesystem paths and parent traversal are excluded.
    path = PurePosixPath(value)
    decoded_parts = unquote(parsed.path).split("/")
    if (
        not parsed.scheme
        and not parsed.netloc
        and path.parts
        and path.parts[0] in {"docs", "src", "packages", "examples"}
        and ".." not in path.parts
        and "\\" not in value
        and not any(part in {".", ".."} for part in decoded_parts)
        and not any(token in parsed.path.lower() for token in ("%2f", "%5c"))
    ):
        return value
    raise ValueError("Unsafe or unsupported URL")


def _source(record: dict, as_of: date) -> dict:
    _fields(
        record,
        {
            "id",
            "kind",
            "status",
            "publication",
            "citation",
            "url",
            "retrieved_at",
            "sha256",
            "license",
            "coverage",
            "caveats",
        },
    )
    for key in record.keys() - {"caveats"}:
        _text(record[key])
    if record["kind"] not in KINDS or record["status"] not in STATUSES:
        raise ValueError("Unknown source kind or status")
    if record["status"] == "private/legacy":
        raise ValueError("Source is not publicly materialized")
    expected_clearance = (
        "synthetic" if record["kind"] == "synthetic" else "public-approved"
    )
    if record["publication"] != expected_clearance:
        raise ValueError("Explicit publication clearance required")
    _url(record["url"])
    retrieved = datetime.fromisoformat(record["retrieved_at"])
    if retrieved.tzinfo is None or retrieved.astimezone(timezone.utc).date() > as_of:
        raise ValueError("Source retrieval needs a timezone and must not follow as_of")
    # SHA-256 byte length is supplied by Python's hashlib algorithm definition;
    # each byte is represented by a pair of hexadecimal characters.
    digest = record["sha256"]
    if len(digest) != hashlib.sha256().digest_size * len("ff") or any(
        char not in "0123456789abcdef" for char in digest
    ):
        raise ValueError("Invalid SHA-256 digest")
    return {**record, "caveats": _texts(record["caveats"])}


def build_pack(payload: dict) -> dict:
    """Validate and copy observations; never infer missing facts or ownership.

    Publication clearance and source digests are declarations by the caller,
    not proof of rights or byte verification against external source artifacts.
    Dates and subject keys remain explicit to avoid unqualified cross-source joins.
    as_of is both the UTC evidence cutoff date and the issue date. A reissue
    advances as_of to its issue date while retaining earlier observation dates.
    """
    _fields(
        payload,
        {
            "asset",
            "as_of",
            "revision",
            "revision_note",
            "sources",
            "observations",
            "gaps",
            "references",
        },
        {"previous_revisions"},
    )
    for key in ("asset", "revision", "revision_note"):
        _text(payload[key])
    as_of = _day(payload["as_of"])
    previous_revisions = payload.get("previous_revisions", [])
    if not isinstance(previous_revisions, list):
        raise TypeError("Previous revisions must be a list")
    revision_history = []
    revision_ids = {payload["revision"]}
    previous_date = date.min
    for prior in previous_revisions:
        _fields(prior, {"revision", "date", "change"})
        revision_id = _text(prior["revision"])
        _text(prior["change"])
        issued = _day(prior["date"])
        if revision_id in revision_ids or not previous_date <= issued <= as_of:
            raise ValueError("Duplicate or out-of-order revision")
        revision_ids.add(revision_id)
        previous_date = issued
        revision_history.append(dict(prior))
    revision_history.append(
        {
            "revision": payload["revision"],
            "date": payload["as_of"],
            "change": payload["revision_note"],
        }
    )
    if not isinstance(payload["sources"], list) or not isinstance(
        payload["observations"], list
    ):
        raise TypeError("Sources and observations must be lists")
    sources = {}
    for record in payload["sources"]:
        source = _source(record, as_of)
        if source["id"] in sources:
            raise ValueError("Duplicate source ID")
        sources[source["id"]] = source
    gaps = payload["gaps"]
    if not isinstance(gaps, dict) or gaps.keys() - SECTIONS.keys():
        raise ValueError("Unknown gap section")
    sections = {
        key: {
            "title": title,
            "observations": [],
            "gaps": _texts(gaps.get(key, [])),
            "caution": CAUTIONS[key],
        }
        for key, title in SECTIONS.items()
    }
    seen = set()
    for record in payload["observations"]:
        _fields(
            record,
            {
                "section",
                "subject",
                "label",
                "value",
                "unit",
                "source_id",
                "locator",
                "observed_on",
            },
        )
        for key in record.keys() - {"value"}:
            _text(record[key])
        section = record["section"]
        if section not in sections or record["source_id"] not in sources:
            raise ValueError("Unknown section or source")
        source = sources[record["source_id"]]
        if source["status"] not in {"downloaded", "derived"}:
            raise ValueError("Observation source is not materialized")
        if section == "lease_title_mineral" and source["kind"] not in {
            "lease",
            "title",
            "mineral",
            "synthetic",
        }:
            raise ValueError("Regulator evidence cannot establish ownership")
        if _day(record["observed_on"]) > as_of:
            raise ValueError("Observation follows as_of")
        value = record["value"]
        if type(value) not in {str, int, float}:
            raise ValueError("Observation value must be text or a finite number")
        if isinstance(value, str):
            _text(value)
        elif isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Observation value must be finite")
        identity = tuple(
            record[key]
            for key in (
                "section",
                "subject",
                "label",
                "source_id",
                "locator",
                "observed_on",
            )
        )
        if identity in seen:
            raise ValueError("Duplicate observation identity")
        seen.add(identity)
        sections[section]["observations"].append(dict(record))
    for section in sections.values():
        count = len(section["observations"])
        section.update(
            observation_count=count,
            status="OBSERVATIONS_ONLY" if count else "NOT_EVALUATED",
        )
        if not count:
            section["gaps"].append(
                "No admissible observations supplied; obtain source evidence."
            )
    if not isinstance(payload["references"], list):
        raise TypeError("References must be a list")
    references = []
    labels = set()
    for record in payload["references"]:
        _fields(record, {"label", "url", "status", "note"})
        label = _text(record["label"])
        _text(record["note"])
        if label in labels:
            raise ValueError("Duplicate reference label")
        labels.add(label)
        if record["status"] not in {"AVAILABLE", "NOT_EVALUATED"}:
            raise ValueError("Unknown reference status")
        if record["status"] == "AVAILABLE":
            _url(record["url"])
        elif record["url"] != "":
            raise ValueError("Unavailable reference must have an empty URL")
        references.append(dict(record))
    if not REFERENCE_LABELS <= labels:
        raise ValueError("Inventory, matrix and source-module references required")
    return {
        "asset": payload["asset"],
        "as_of": payload["as_of"],
        "revision": payload["revision"],
        "revision_note": payload["revision_note"],
        "revision_history": revision_history,
        "synthetic": any(s["kind"] == "synthetic" for s in sources.values()),
        "observation_count": len(seen),
        "sections": sections,
        "sources": list(sources.values()),
        "references": references,
    }


def _e(value: object) -> str:
    return escape(str(value), quote=True)


def render_html(pack: dict, repository_url: str = "../../") -> str:
    """Render a validated pack, with no scripts or remote assets.

    repository_url resolves repository-relative citations. The default suits
    the committed example location; copied reports should supply a public
    repository URL or retain the same directory layout.
    """
    if repository_url != "../../":
        _url(repository_url)
        parsed_root = urlsplit(repository_url)
        if (
            parsed_root.scheme not in {"https", "http"}
            or parsed_root.query
            or parsed_root.fragment
        ):
            raise ValueError("Repository URL must be an HTTP(S) root")
        repository_url = repository_url.rstrip("/") + "/"

    def link(url: str, label: str) -> str:
        target = url if urlsplit(url).scheme else repository_url + url
        return f'<a href="{_e(target)}">{_e(label)}</a>'

    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        "<title>Landman diligence pack</title>",
        "<style>body{font-family:system-ui;margin:2em;max-width:80em;color:#172b4d}",
        "table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;",
        "padding:.5em;text-align:left;overflow-wrap:anywhere}aside{background:#fff3cd;",
        "padding:1em}section{margin-block:2em}a{color:#0645ad}</style></head><body>",
        "<main><h1>Landman diligence pack</h1><h2>Summary</h2>",
        f'<p>{_e(pack["asset"])}; evidence cutoff {_e(pack["as_of"])}. ',
        f'{pack["observation_count"]} supplied observations; no completeness claim.</p>',
        "<aside>Missing data is not evidence of absence. This is an evidence inventory, ",
        "not a title opinion, reserves estimate or environmental clearance.</aside>",
    ]
    if pack["synthetic"]:
        parts.append(
            "<p><strong>SYNTHETIC demonstration: includes invented inputs; "
            "not asset evidence.</strong></p>"
        )
    parts.append(
        "<h2>Revision history</h2><table><tr><th>Revision</th><th>Date</th>"
        "<th>Change and reason</th></tr>"
    )
    for revision in pack["revision_history"]:
        parts.append(
            f'<tr><td>{_e(revision["revision"])}</td><td>{_e(revision["date"])}</td>'
            f'<td>{_e(revision["change"])}</td></tr>'
        )
    parts.append("</table>")
    for key, section in pack["sections"].items():
        noun = "observation" if section["observation_count"] == 1 else "observations"
        parts += [
            f'<section id="{key}"><h2>{_e(section["title"])}</h2>',
            f'<p>{_e(section["status"])}; {section["observation_count"]} {noun}.</p>',
            f'<p>{_e(section["caution"])}</p>',
        ]
        if section["observations"]:
            parts.append(
                "<table><tr><th>Subject</th><th>Observation</th><th>Value</th><th>Unit</th>"
                "<th>Observed on</th><th>Source / locator</th></tr>"
            )
            for row in section["observations"]:
                parts.append(
                    "<tr>"
                    + "".join(
                        f"<td>{_e(row[field])}</td>"
                        for field in (
                            "subject",
                            "label",
                            "value",
                            "unit",
                            "observed_on",
                        )
                    )
                    + f'<td><a href="#sources">{_e(row["source_id"])}</a> / '
                    + f'{_e(row["locator"])}</td></tr>'
                )
            parts.append("</table>")
        parts += [f"<p>Gap: {_e(gap)}</p>" for gap in section["gaps"]]
        parts.append("</section>")
    parts.append("<h2>Explicit data gaps</h2><ul>")
    for section in pack["sections"].values():
        parts += [
            f'<li>{_e(section["title"])}: {_e(gap)}</li>' for gap in section["gaps"]
        ]
    parts.append('</ul><h2 id="sources">Sources and provenance</h2>')
    for source in pack["sources"]:
        parts += [
            f'<h3>{_e(source["id"])}</h3><p>{link(source["url"], source["citation"])}</p>',
            "<dl>",
        ]
        for field in (
            "kind",
            "status",
            "publication",
            "retrieved_at",
            "sha256",
            "license",
            "coverage",
        ):
            parts.append(f"<dt>{_e(field)}</dt><dd>{_e(source[field])}</dd>")
        parts.append("</dl>")
        parts += [f"<p>Caveat: {_e(note)}</p>" for note in source["caveats"]]
    parts.append("<h2>Coverage references</h2>")
    for ref in pack["references"]:
        label = link(ref["url"], ref["label"]) if ref["url"] else _e(ref["label"])
        parts.append(f'<p>{label}: {_e(ref["status"])}. {_e(ref["note"])}</p>')
    parts.append("</main></body></html>\n")
    return "".join(parts)


def _unique_json_members(pairs: list[tuple[str, object]]) -> dict:
    """Reject ambiguous declarations before JSON object members are discarded."""
    record = {}
    for key, value in pairs:
        if key in record:
            raise ValueError("Duplicate JSON member")
        record[key] = value
    return record


def write_pack(
    input_path: Path, output_dir: Path, repository_url: str = "../../"
) -> None:
    """Write deterministic HTML and a separate JSON summary to a new directory.

    Existing output directories are refused to preserve earlier artifacts.
    Input bytes are hashed; externally declared source digests are not verified.
    """
    raw = Path(input_path).read_bytes()
    pack = build_pack(json.loads(raw, object_pairs_hook=_unique_json_members))
    report = render_html(pack, repository_url)
    pack["input_sha256"] = hashlib.sha256(raw).hexdigest()
    report_bytes = report.encode("utf-8")
    summary_bytes = (
        json.dumps(pack, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "index.html").write_bytes(report_bytes)
    (output_dir / "summary.json").write_bytes(summary_bytes)
