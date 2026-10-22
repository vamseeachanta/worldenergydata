"""Build an offline career packet; evidence presence does not prove authorship.

Contract: issue #1087 requires artifact-linked claims and a distinction between
hands-on work and research. There are no engineering equations or default limits.
"""

from __future__ import annotations

import argparse
import json
import os
from html import escape
from pathlib import Path
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "docs/career/semiconductor-packet.json"
REPORT = ROOT / "docs/reports/semiconductor-career-packet.html"
BUILT = "hands-on artifact built"
RESEARCHED = "concept researched"
PENDING = "NOT_EVALUATED"


def validate(packet: dict, root: Path) -> None:
    """Reject unsupported claims and evidence paths outside the checkout."""
    root = root.resolve()
    sources = {}
    for source in packet["sources"]:
        parsed = urlsplit(source["url"])
        if parsed.scheme != "https" or not parsed.netloc or parsed.username:
            raise ValueError("sources must use public HTTPS URLs")
        if source["id"] in sources:
            raise ValueError("duplicate source")
        sources[source["id"]] = source

    artifacts = {}
    for artifact in packet["artifacts"]:
        key = artifact["id"]
        if key in artifacts:
            raise ValueError("duplicate artifact")
        artifacts[key] = artifact
        if artifact["status"] not in {BUILT, RESEARCHED, PENDING}:
            raise ValueError("unsupported evidence status")
        for name in artifact["paths"]:
            path = Path(name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("evidence must be repository-relative")
            resolved = (root / path).resolve()
            if not resolved.is_relative_to(root):
                raise ValueError("evidence must be repository-relative")
            if not resolved.is_file():
                raise ValueError("missing evidence file")
        if artifact["status"] == BUILT and not artifact["paths"]:
            raise ValueError("built evidence requires files")
        if artifact["status"] == RESEARCHED and not artifact["sources"]:
            raise ValueError("missing research source")
        if not set(artifact["sources"]) <= sources.keys():
            raise ValueError("unknown research source")
    if not {"research", "eda", "layout", "fem", "reports"} <= artifacts.keys():
        raise ValueError("missing required portfolio slots")

    claims = {}
    for claim in packet["claims"]:
        if claim["id"] in claims:
            raise ValueError("duplicate claim")
        claims[claim["id"]] = claim
        for key in claim["evidence"]:
            if key not in artifacts:
                raise ValueError("unknown evidence")
            if artifacts[key]["status"] != BUILT:
                raise ValueError("claims require built evidence")
        if not claim["evidence"]:
            raise ValueError("claims require built evidence")
    for role in packet["roles"]:
        if not role["claims"] or not set(role["claims"]) <= claims.keys():
            raise ValueError("role requires known claims")
    for note in packet["interview"]:
        if note["status"] not in {RESEARCHED, PENDING}:
            raise ValueError("interview evidence status must be explicit")
        if note["status"] == RESEARCHED and not note["sources"]:
            raise ValueError("missing research source")
        if not set(note["sources"]) <= sources.keys():
            raise ValueError("unknown research source")


def render(packet: dict, root: Path, output: Path) -> str:
    """Render deterministic HTML with links relative to its destination."""
    validate(packet, root)
    sources = {s["id"]: s for s in packet["sources"]}
    artifacts = {a["id"]: a for a in packet["artifacts"]}
    claims = {c["id"]: c for c in packet["claims"]}

    def local(name: str) -> str:
        href = quote(Path(os.path.relpath(root / name, output.parent)).as_posix())
        return f'<a href="{href}">{escape(name)}</a>'

    def citations(keys: list[str]) -> str:
        return "; ".join(
            f'<a href="{escape(sources[k]["url"], quote=True)}">'
            f'{escape(sources[k]["title"])}</a>'
            for k in keys
        )

    def evidence(keys: list[str]) -> str:
        return "; ".join(local(p) for k in keys for p in artifacts[k]["paths"])

    parts = [
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Semiconductor career packet</title>",
        "<style>body{font:1rem/1.6 system-ui,sans-serif;max-width:72rem;",
        "margin:auto;padding:1.5rem;color:#172534;background:#fafcff}",
        "table{border-collapse:collapse;width:100%}th,td{border:1px solid #b8c6d4;",
        "padding:.6rem;text-align:left;vertical-align:top}a{color:#12529b}",
        "td,li{overflow-wrap:anywhere}article{border-left:solid #b8c6d4;",
        "padding-left:1rem;margin:1.5rem 0}code{white-space:pre-wrap}</style>",
        "</head><body><main><h1>Semiconductor career packet</h1>",
        "<h2>Summary</h2>",
        f'<p>{escape(packet["summary"])}</p>',
        "<h2>Revision history</h2>",
        "<table><tr><th>Revision</th><th>Date</th><th>Change and reason</th></tr>",
    ]
    for revision in packet["revisions"]:
        parts.append(
            "<tr>"
            + "".join(
                f"<td>{escape(revision[k])}</td>"
                for k in ("revision", "date", "change")
            )
            + "</tr>"
        )
    parts.extend(
        [
            "</table><h2>Portfolio index</h2>",
            (
                "<p>Built status identifies available repository work, not candidate "
                "authorship, personal proficiency or semiconductor qualification.</p>"
            ),
            (
                "<table><tr><th>Artifact</th><th>Evidence class</th>"
                "<th>Scope and limits</th><th>Evidence</th></tr>"
            ),
        ]
    )
    for artifact in packet["artifacts"]:
        links = evidence([artifact["id"]]) or citations(artifact["sources"])
        parts.append(
            f'<tr><td>{escape(artifact["title"])}</td>'
            f'<td>{escape(artifact["status"])}</td>'
            f'<td>{escape(artifact["summary"])}</td>'
            f'<td>{links or "Evidence required"}</td></tr>'
        )
    parts.extend(
        [
            "</table><h2>Resume bullet candidates</h2>",
            (
                "<p>Use only after confirming personal contribution. Replace "
                "the contribution placeholder; omit any bullet that cannot be defended.</p>"
            ),
        ]
    )
    for claim in packet["claims"]:
        parts.append(
            f'<article><p>{escape(claim["text"])}</p>'
            "<p>Personal contribution: [describe and verify before use].</p>"
            f'<p>Evidence: {evidence(claim["evidence"])}</p></article>'
        )
    parts.append("<h2>Role-specific application templates</h2>")
    for role in packet["roles"]:
        parts.append(
            f'<article><h3>{escape(role["title"])}</h3>'
            f'<p>{escape(role["template"])}</p>'
        )
        for key in role["claims"]:
            claim = claims[key]
            parts.append(
                f'<p>Available repository example: {escape(claim["text"])} '
                f'{evidence(claim["evidence"])}</p>'
            )
        parts.append(f'<p>Gap: {escape(role["gap"])}</p></article>')
    parts.append("<h2>Interview preparation</h2>")
    for note in packet["interview"]:
        parts.append(
            f'<article><h3>{escape(note["term"])}</h3>'
            f'<p>{escape(note["status"])}: {escape(note["note"])}</p>'
            f'<p>{citations(note["sources"]) or "Source and worked artifact required"}'
            "</p></article>"
        )
    parts.append("<h2>Tailoring checklist</h2><ol>")
    parts.extend(f"<li>{escape(step)}</li>" for step in packet["tailoring"])
    parts.append("</ol><h2>Sources and reproducibility</h2><ul>")
    for source in packet["sources"]:
        parts.append(
            f'<li>{citations([source["id"]])}. '
            f'{escape(source["edition"])}; checked {escape(source["checked"])}.</li>'
        )
    parts.extend(
        [
            "</ul><p>Data:",
            local("docs/career/semiconductor-packet.json"),
            (
                "</p><p>Regenerate from the repository root: <code>python "
                "scripts/career/build_semiconductor_packet.py</code>. "
                "Generation is offline and uses the Python standard library.</p>"
            ),
            "<h2>Known limits and later work</h2><ul>",
        ]
    )
    parts.extend(f"<li>{escape(limit)}</li>" for limit in packet["limits"])
    parts.append("</ul></main></body></html>\n")
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--output", type=Path, default=REPORT)
    args = parser.parse_args()
    packet = json.loads(args.data.read_text(encoding="utf-8"))
    content = render(packet, ROOT, args.output.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
