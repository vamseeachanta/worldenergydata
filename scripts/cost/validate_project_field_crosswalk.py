#!/usr/bin/env python3
"""Validate the held cost-project/field crosswalk without modifying inputs."""

import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "project_field_crosswalk",
    ROOT
    / "packages/worldenergydata-cost/src/worldenergydata/cost/project_field_crosswalk.py",
)
API = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(API)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository input root")
    parser.add_argument(
        "--crosswalk",
        type=Path,
        help="candidate CSV; inputs must match the held manifest",
    )
    args = parser.parse_args(argv)
    try:
        result = API.validate_repository(args.root, args.crosswalk)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
