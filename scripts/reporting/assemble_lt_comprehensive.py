#!/usr/bin/env python
# ABOUTME: Driver script that assembles the LT comprehensive report (#377)
# ABOUTME: Calls comprehensive_report.render_all() and writes MD + HTML + PDF
"""Assemble the Lower Tertiary comprehensive report (#377).

Usage:
    uv run python scripts/reporting/assemble_lt_comprehensive.py
    uv run python scripts/reporting/assemble_lt_comprehensive.py --output-dir reports/lower_tertiary

Defaults to writing under `reports/lower_tertiary/`. Produces three files:
- comprehensive_2026.md (canonical for-humans Markdown)
- comprehensive_2026.html (buyer-presentable)
- comprehensive_2026.pdf (Chrome-headless rendering)
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from worldenergydata.lower_tertiary.comprehensive_report import (
    assemble_comprehensive_report,
    render_all,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/lower_tertiary"),
        help="Directory to write the report outputs (default: reports/lower_tertiary)",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable info-level logging"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    result = assemble_comprehensive_report()
    paths = render_all(result, args.output_dir)
    for name, path in paths.items():
        print(f"Wrote {name}: {path}")
    print(f"Fields covered: {len(result.economics_run.results)}")
    print(f"Executive findings: {len(result.executive_summary)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
