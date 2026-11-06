"""Offline synthetic input, duplicate intake and review-preparation example.

Run with an explicit new output directory outside the repository:
    python examples/offshore_hse_review.py --output-dir "$EXAMPLE_OUTPUT"
No official event or completed independent review is represented.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from worldenergydata.hse.importers.offshore_importer import OffshoreImporter
from worldenergydata.hse.offshore_review import (
    build_review_worklist,
    collection_readiness,
)


def _example_event():
    return {
        "event_id": "example-event",
        "event_date": "2024-02-01",
        "country": "GB",
        "basin_or_area": "synthetic basin",
        "installation_name": "synthetic installation",
        "operation": "lifting",
        "equipment": ["hoist"],
        "failure_mode": "not established",
        "failure_summary": "synthetic event for software demonstration",
    }


def _example_source():
    return {
        "event_id": "example-event",
        "source": "bsee",
        "source_ref": "synthetic-example",
        "title": "synthetic report; no official source is represented",
        "doc_type": "investigation report",
        "issue_date": "2024-02-02",
        "status": "synthetic",
        "url": "https://www.bsee.gov/synthetic-example",
        "access_date": "2024-02-03",
        "licence": "synthetic metadata only",
        "evidence_level": "regulator",
        "access_status": "public",
    }


def example_input():
    """Declare synthetic facts and their explicit, non-production text inventory."""
    # Explicit synthetic text inventory. Real collection requires human curation;
    # deriving an inventory from arbitrary report text would defeat admission.
    reviewed_text = [
        "example-event",
        "2024-02-01",
        "GB",
        "synthetic basin",
        "synthetic installation",
        "lifting",
        "hoist",
        "not established",
        "synthetic event for software demonstration",
        "bsee",
        "synthetic-example",
        "synthetic report; no official source is represented",
        "investigation report",
        "2024-02-02",
        "synthetic",
        "https://www.bsee.gov/synthetic-example",
        "2024-02-03",
        "synthetic metadata only",
        "regulator",
        "public",
    ]
    return {
        "events": [_example_event()],
        "sources": [_example_source()],
        "reviewed_text": reviewed_text,
    }


def run_example(output_dir):
    output_dir = Path(output_dir).resolve()
    if output_dir.is_relative_to(Path(__file__).resolve().parents[1]):
        raise ValueError("example output must be outside the repository")
    output_dir.mkdir(parents=True, exist_ok=False)
    packet = example_input()
    input_path = output_dir / "input.json"
    input_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    importer = OffshoreImporter(output_dir / "collection.sqlite")
    packet = json.loads(input_path.read_text(encoding="utf-8"))
    result = {
        "data_basis": "synthetic software example; not collected incident evidence",
        "first_intake": importer.ingest(packet),
        "repeat_intake": importer.ingest(packet),
        "readiness": collection_readiness(importer),
        "worklist": build_review_worklist(importer, stage="pilot"),
    }
    answer_path = output_dir / "answer.json"
    answer_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if json.loads(answer_path.read_text(encoding="utf-8")) != result:
        raise OSError("example answer readback differs")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run_example(args.output_dir), indent=2))


if __name__ == "__main__":
    main()
