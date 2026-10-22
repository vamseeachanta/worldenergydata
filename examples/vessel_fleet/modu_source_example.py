"""Assess the selected public candidate without fetching or inferring inputs."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from worldenergydata.vessel_fleet.modu_source import assess, load_record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-file",
        type=Path,
        help="Optional retained public rig-page bytes for digest verification",
    )
    args = parser.parse_args()
    record = load_record()
    payloads = None
    if args.source_file:
        payloads = {record.sources[0].source_id: args.source_file.read_bytes()}
    print(json.dumps(asdict(assess(record, source_bytes=payloads)), indent=2))


if __name__ == "__main__":
    main()
