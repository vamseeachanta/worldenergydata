"""Reproduce the area/operator-class fixture example without fetching archives."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from worldenergydata.bsee.analysis.completion_intervention.activity import analyse
from worldenergydata.bsee.analysis.completion_intervention.report import (
    digest,
    render_report,
)

FIXTURES = Path("tests/fixtures/bsee/completion_intervention")
OUTPUT = Path(
    "docs/modules/bsee/analysis/completion_intervention/area_operator_example.html"
)
REVISION = {
    "revision": "2",
    "history": [
        {
            "revision": "1",
            "date": "2026-10-19",
            "change": "Fixture demonstration of area counts and unavailable operator classes.",
        },
        {
            "revision": "2",
            "date": "2026-10-21",
            "change": "Distinguished the fixture example and archive digests; omitted unevaluated operator charts and made generation reproducible.",
        },
    ],
}


def build(fixtures=FIXTURES, output=OUTPUT):
    """Check projection bytes and derive every catalogue row from the manifest."""
    fixtures, output = Path(fixtures), Path(output)
    manifest = json.loads((fixtures / "manifest.json").read_text(encoding="utf-8"))
    tables, catalogue = {}, []
    for name, item in sorted(manifest["files"].items()):
        if Path(name).name != name or Path(name).suffix != ".csv":
            raise ValueError("fixture name must be a single CSV filename")
        path = fixtures / name
        if digest(path) != item["sha256"]:
            raise ValueError(f"fixture digest mismatch: {name}")
        frame = pd.read_csv(path, dtype=str).fillna("")
        if len(frame) != item["rows"]:
            raise ValueError(f"fixture row count mismatch: {name}")
        tables[path.stem] = frame
        catalogue.append(
            {
                "publisher_name": "BSEE public-source fixture projection",
                "member": name,
                "url": item["source_url"],
                "status": "fixture subset",
                "retrieved_at": "not recorded for projection",
                "years": "subset only",
                "record_count": len(frame),
                "sha256": item["sha256"],
                "archive_sha256": item["archive_sha256"],
                "member_sha256": None,
                "fields": list(frame.columns),
                "reason": "Existing digest-pinned projection; not a complete archive. File SHA-256 identifies the CSV projection; the raw member digest is not established.",
            }
        )
    result = analyse(tables)
    result["catalogue"] = catalogue
    page = render_report(
        result, REVISION, title="Area and operator-class activity: fixture example"
    )
    output.write_text(page, encoding="utf-8", newline="\n")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=FIXTURES)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    build(args.fixtures, args.output)


if __name__ == "__main__":
    main()
