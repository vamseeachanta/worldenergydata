"""Offline command for generating a landman diligence pack."""

import argparse
from pathlib import Path

from worldenergydata.underwriting.diligence import write_pack


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Normalized evidence JSON")
    parser.add_argument("output", type=Path, help="New output directory")
    parser.add_argument(
        "--repository-url", default="../../", help="Root URL for repository citations"
    )
    args = parser.parse_args()
    write_pack(args.input, args.output, args.repository_url)


if __name__ == "__main__":
    main()
