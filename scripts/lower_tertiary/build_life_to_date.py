#!/usr/bin/env python3
"""Build the Julia observed-production assumption analysis."""

import argparse
from pathlib import Path

from worldenergydata.lower_tertiary.life_to_date import build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/economics/julia_life_to_date"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = build(args.data_dir, args.output_dir)
    for output in manifest["outputs"]:
        print(output["path"], output["bytes"], output["sha256"])


if __name__ == "__main__":
    main()
