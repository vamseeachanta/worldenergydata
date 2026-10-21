#!/usr/bin/env python3
"""Build an evidence-constrained portfolio map from an explicit JSON input."""

import argparse
from pathlib import Path

from worldenergydata.cost.portfolio.reporting import build


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--data-root", type=Path)
    args = parser.parse_args()
    build(
        args.input,
        args.output_dir,
        manifest=args.manifest,
        manifest_sha256=args.manifest_sha256,
        data_root=args.data_root,
    )


if __name__ == "__main__":
    main()
