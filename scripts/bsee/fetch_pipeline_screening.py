#!/usr/bin/env python3
"""Restore a screening CSV from a verified external content-addressed store."""

import argparse
import json
from pathlib import Path

from worldenergydata.bsee.pipeline_screening_io import fetch_payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.destination.resolve() == root or root in args.destination.resolve().parents:
        raise ValueError("Full dataset destination must remain outside the repository")
    fetch_payload(json.loads(args.manifest.read_text()), args.store, args.destination)
    print("External payload digest and byte count verified")


if __name__ == "__main__":
    main()
