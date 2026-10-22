"""Regenerate the evidence-constrained transaction package without network calls.

Run with the repository on PYTHONPATH:
    python scripts/field_development/build_na_kika_coulomb_transaction.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from worldenergydata.field_development.transaction_package import build_package
from worldenergydata.field_development.transaction_report import write_package


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=root / "data/modules/offshore_assets/transactions/na_kika_coulomb.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=root / "reports/field_development/transactions/na_kika_coulomb",
    )
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    outputs = write_package(build_package(data, root), args.out, root)
    print(f"Generated and read back {len(outputs)} artifacts; economics NOT_EVALUATED")


if __name__ == "__main__":
    main()
