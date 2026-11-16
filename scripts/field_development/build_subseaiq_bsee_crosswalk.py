#!/usr/bin/env python3
"""The historical crosswalk is held privately pending redistribution-terms review."""

import sys
from pathlib import Path

SOURCE_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SOURCE_DIR))
from worldenergydata.field_development.data_availability import (  # noqa: E402
    load_withheld_dataset,
)


def main() -> None:
    """Reject default generation instead of reading the withheld source catalog."""
    load_withheld_dataset("subseaiq_bsee_block_crosswalk.csv")


if __name__ == "__main__":
    main()
