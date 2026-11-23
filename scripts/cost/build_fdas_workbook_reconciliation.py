#!/usr/bin/env python3
"""Generate a frozen, read-only FDAS comparison into a fresh output directory."""

import argparse
import json
from pathlib import Path

from worldenergydata.cost.workbook_reconciliation import (
    reconcile_workbooks,
    write_outputs,
)
from worldenergydata.cost.workbook_reconciliation.integration import (
    attach_existing_evidence,
)
from worldenergydata.cost.workbook_reconciliation.workbook_reader import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, required=True, help="fresh output directory"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    contract_path = root / "config/analysis/lower_tertiary/fdas_workbook_vintages.json"
    contract_data = contract_path.read_bytes()
    result = reconcile_workbooks(
        root / "docs/modules/bsee/analysis/production/FDAS_V30",
        json.loads(contract_data),
    )
    attach_existing_evidence(result, root)
    producer = (
        root
        / "packages/worldenergydata-cost/src/worldenergydata/cost/workbook_reconciliation"
    )
    sources = [
        Path(__file__),
        contract_path,
        *sorted(producer.glob("*.py")),
        root
        / "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/cost_map.py",
        root
        / "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/project_trace.py",
    ]
    result["producer_hashes"] = {
        str(p.relative_to(root)): digest(p.read_bytes()) for p in sources
    }
    write_outputs(result, args.output.resolve())
    print(
        f"Generated reconciliation for {len(result['projects'])} workbook projects; external comparisons NOT_EVALUATED."
    )


if __name__ == "__main__":
    main()
