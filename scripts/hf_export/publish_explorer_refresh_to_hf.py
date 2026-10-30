#!/usr/bin/env python3
"""Compatibility entry point for complete exact-revision Explorer snapshots.

The former floating-table patch operation is retired. Configuration and a clean
source SHA are mandatory; preview is local and write-free by default.
"""

from publish_explorer_snapshot_to_hf import main as snapshot_main

DATASET = "aceengineer/worldenergydata-explorer"


def main():
    return snapshot_main(default_dataset=DATASET)


if __name__ == "__main__":
    raise SystemExit(main())
