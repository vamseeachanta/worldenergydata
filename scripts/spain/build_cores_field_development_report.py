#!/usr/bin/env python
"""Build the Spain CORES field-development report (#810)."""

from __future__ import annotations

import argparse
from pathlib import Path

from worldenergydata.spain.reports.cores_field_development import build_report

DEFAULT_OUTPUT_HTML = Path("reports/field_development/spain_cores.html")
DEFAULT_OUTPUT_JSON = Path("reports/field_development/spain_cores.json")


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--output-html", type=Path, default=DEFAULT_OUTPUT_HTML)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    args = parser.parse_args(argv)
    return build_report(
        args.cache_root,
        output_html=args.output_html,
        output_json=args.output_json,
    )


if __name__ == "__main__":
    main()
