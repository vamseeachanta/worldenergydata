"""Import curated public metadata to an explicitly selected external data root.

The source-neutral collector never downloads reports or invokes the old ORM.
Run pilot -> independent pilot receipt -> candidate intake -> existing-index
reconciliation -> independent bulk receipt. Each export is an immutable directory.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from worldenergydata.hse.importers.offshore_importer import OffshoreImporter
from worldenergydata.hse.offshore_review import (
    build_review_worklist,
    collection_readiness,
)


def _build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root", type=Path, default=os.environ.get("WED_DATA_ROOT")
    )
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--stage", choices=("pilot", "candidate"), default="pilot")
    parser.add_argument("--pilot-review", type=Path)
    parser.add_argument("--pilot-event-id")
    parser.add_argument("--existing-indexes", type=Path)
    parser.add_argument("--bulk-review", type=Path)
    parser.add_argument(
        "--export", help="new export directory name beneath the collection root"
    )
    parser.add_argument("--digest", action="store_true")
    parser.add_argument(
        "--readiness",
        action="store_true",
        help="report recorded gates and missing evidence",
    )
    parser.add_argument(
        "--review-worklist",
        choices=("pilot", "bulk"),
        help="prepare cited evidence for independent review; grants no approval",
    )
    return parser


def _validate_args(parser, args):
    repo_root = Path(__file__).resolve().parents[1]
    if args.data_root is None or args.data_root.resolve().is_relative_to(repo_root):
        parser.error(
            "an external data root is required via --data-root or WED_DATA_ROOT"
        )
    if args.export and (
        Path(args.export).name != args.export or args.export in {".", ".."}
    ):
        parser.error("export must be a single directory name")
    if args.pilot_review and not args.pilot_event_id:
        parser.error("--pilot-event-id is required with --pilot-review")
    if args.bulk_review and not args.existing_indexes:
        parser.error("--existing-indexes is required with --bulk-review")


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
    _validate_args(parser, args)
    root = args.data_root / "modules" / "hse" / "offshore"
    report_only = (args.readiness or args.review_worklist is not None) and not any(
        (
            args.packet,
            args.pilot_review,
            args.existing_indexes,
            args.bulk_review,
            args.export,
        )
    )
    importer = OffshoreImporter(root / "offshore.sqlite", read_only=report_only)
    result = {}
    if args.packet:
        result["intake"] = importer.ingest(
            json.loads(args.packet.read_text()), stage=args.stage
        )
    if args.pilot_review:
        importer.approve_pilot(
            args.pilot_event_id, json.loads(args.pilot_review.read_text())
        )
    indexes = None
    if args.existing_indexes:
        indexes = json.loads(args.existing_indexes.read_text())
        result["reconciliation"] = importer.reconcile_existing(indexes)
    if args.bulk_review:
        importer.approve_bulk(json.loads(args.bulk_review.read_text()), indexes)
    if args.export:
        result["manifest"] = importer.export(root / args.export)
    if args.digest:
        result["dataset_sha256"] = importer.content_digest()
    if args.readiness:
        result["readiness"] = collection_readiness(importer)
    if args.review_worklist:
        result["review_worklist"] = build_review_worklist(
            importer, stage=args.review_worklist, pilot_event_id=args.pilot_event_id
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
