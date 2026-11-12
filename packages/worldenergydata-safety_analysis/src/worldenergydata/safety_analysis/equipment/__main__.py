# ABOUTME: Command line for the equipment failure table: build it, show coverage, write a report section.
# ABOUTME: Inputs are listed in a small JSON file so each source keeps its URL and retrieval date.

"""Command line.

::

    python -m worldenergydata.safety_analysis.equipment build \
        --sources sources.json --out-dir out/
    python -m worldenergydata.safety_analysis.equipment section \
        --sources sources.json --equipment-class mooring_line --out section.md

``sources.json`` is a list of objects with ``source_id``, ``path``, ``url``,
``retrieved`` (YYYY-MM-DD), and optionally ``title`` and ``licence``. A relative
``path`` resolves against the JSON file's directory.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from worldenergydata.safety_analysis.equipment.cases import load_cases
from worldenergydata.safety_analysis.equipment.report_section import (
    build_section,
    render_markdown,
)
from worldenergydata.safety_analysis.equipment.table import (
    SourceFile,
    build_table,
    coverage,
    write_csv,
    write_summary,
)
from worldenergydata.safety_analysis.equipment.taxonomy import EQUIPMENT_CLASSES


def load_sources(path: Path) -> list[SourceFile]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError("sources file must be a non-empty JSON list")
    out = []
    for item in raw:
        file_path = Path(item["path"])
        if not file_path.is_absolute():
            file_path = Path(path).parent / file_path
        out.append(
            SourceFile(
                source_id=item["source_id"],
                path=file_path,
                url=item["url"],
                retrieved=item["retrieved"],
                title=item.get("title", ""),
                licence=item.get("licence", ""),
            )
        )
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m worldenergydata.safety_analysis.equipment",
        description="Equipment failure table and HSE report section",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="write the table CSV and summary JSON")
    build.add_argument("--sources", required=True, type=Path)
    build.add_argument("--out-dir", required=True, type=Path)
    section = sub.add_parser("section", help="write the HSE and safety appendix")
    section.add_argument("--sources", required=True, type=Path)
    section.add_argument(
        "--equipment-class", required=True, choices=sorted(EQUIPMENT_CLASSES)
    )
    section.add_argument("--cases", type=Path, help="case register (YAML)")
    section.add_argument("--case-id", action="append", help="case to show (repeat)")
    section.add_argument(
        "--design-links", type=Path, help='JSON {"<case id>#<n>": "Section ..."}'
    )
    section.add_argument("--letter", default="F", help="appendix letter")
    section.add_argument("--out", required=True, type=Path)
    section.add_argument(
        "--allow-open", action="store_true", help="exit 0 with open items"
    )
    args = parser.parse_args(argv)

    try:
        rows, stats = build_table(load_sources(args.sources))
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.command == "build":
        write_csv(rows, args.out_dir / "equipment-failure-table.csv")
        write_summary(rows, stats, args.out_dir / "equipment-failure-summary.json")
        for line in coverage(rows):
            print(
                f"{line['equipment_class']:20s} {line['records']:5d} records, "
                f"{line['mechanism_stated']:5d} with a stated cause"
            )
        return 0

    links = {}
    if args.design_links:
        links = json.loads(args.design_links.read_text(encoding="utf-8"))
    try:
        built = build_section(
            args.equipment_class,
            rows,
            stats,
            load_cases(args.cases),
            design_links=links,
            case_ids=args.case_id,
            letter=args.letter,
        )
    except (ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_markdown(built), encoding="utf-8", newline="\n")
    args.out.with_suffix(".json").write_text(
        json.dumps(built.to_dict(), indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    for item in built.open_items:
        print(f"open: {item}", file=sys.stderr)
    return 0 if (not built.open_items or args.allow_open) else 1


if __name__ == "__main__":
    raise SystemExit(main())
