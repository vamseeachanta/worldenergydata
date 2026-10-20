"""Generate frozen workbook reconciliation without editing workbook files."""

import argparse
from pathlib import Path

from worldenergydata.cost.workbook_reconciliation.report import build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--comparisons", type=Path, help="Explicit evidence and materiality policy JSON"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    build(root, args.output.resolve(), args.comparisons)


if __name__ == "__main__":
    main()
