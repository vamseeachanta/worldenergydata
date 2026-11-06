"""Prepare reviewed public notice files and export to an external data root.

This command is offline. --manual-hse prints official URLs when public access is
blocked. A config supplies reviewed text, curation, dates and spreadsheet layout;
it must never contain personal names, contact details or private information.
The existing offshore importer enforces source keys and writes the audit manifest.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

from worldenergydata.hse.importers.notice_loaders import (
    load_hse_notices,
    manual_hse_step,
    parse_pon1,
)
from worldenergydata.hse.importers.offshore_importer import OffshoreImporter


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manual-hse", action="store_true")
    parser.add_argument("--pon1", type=Path)
    parser.add_argument("--hse-xlsx", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument(
        "--data-root", type=Path, default=os.environ.get("WED_DATA_ROOT")
    )
    parser.add_argument("--export", help="new immutable export directory name")
    args = parser.parse_args(argv)
    if args.manual_hse:
        print(json.dumps(asdict(manual_hse_step("BLOCKED-NETWORK")), indent=2))
        return 0
    if not (args.pon1 or args.hse_xlsx) or args.config is None:
        parser.error("a public notice file and --config are required")
    repo = Path(__file__).resolve().parents[1]
    if args.data_root is None or args.data_root.resolve().is_relative_to(repo):
        parser.error("--data-root or WED_DATA_ROOT must identify an external data root")
    if (
        not args.export
        or Path(args.export).name != args.export
        or args.export in {".", ".."}
    ):
        parser.error("--export must be a single directory name")
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        access = date.fromisoformat(config["access_date"])
        reviewed = config["reviewed_text"]
        if args.pon1:
            packet = parse_pon1(
                args.pon1.read_text(encoding="utf-8"),
                context=config["context"],
                url=config["pon1_url"],
                access_date=access,
                reviewed_text=reviewed,
            )
        else:
            packet = {
                "events": config.get("events", []),
                "sources": [],
                "reviewed_text": reviewed,
            }
        if args.hse_xlsx:
            result = load_hse_notices(
                args.hse_xlsx,
                columns=config["columns"],
                sheet=config["sheet"],
                header_row=config["header_row"],
                associations=config["associations"],
                date_format=config["date_format"],
                access_date=access,
                reviewed_text=reviewed,
            )
            if result.status != "ready":
                print(json.dumps(asdict(result), indent=2))
                return 2
            packet["sources"].extend(
                row.model_dump(mode="json") for row in result.sources
            )
        # Additional reviewed source metadata may contextualize the same event;
        # copyrighted prose is not acquired or copied by this command.
        packet["sources"].extend(config.get("sources", []))
        root = args.data_root / "modules" / "hse" / "offshore"
        importer = OffshoreImporter(root / "offshore.sqlite")
        stats = importer.ingest(packet)
        manifest = importer.export(root / args.export)
        print(json.dumps({"intake": stats, "manifest": manifest}, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError):
        # Raw validation errors can contain identity strings and local paths.
        print(
            "Notice intake refused; review configuration, privacy and input layout locally.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
