"""Synthetic operator registry worked example, using no external data.

Hand calculation: 12*(150+0) = 1800 bbl oil; 12*(10+20) = 360 Mcf gas;
12*(100+150) = 3000 bbl water; water fraction = 3000/4800 = 0.625.
Two of three wells share a field: field HHI = (2/3)^2+(1/3)^2 = 5/9.
Only the gas well has an individual gas rate: 240/365 Mcf/calendar day.
The two oil wells retain lease-level production without inferred allocation.
All dates, IDs, volumes, bands and thresholds here are synthetic input choices.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from worldenergydata.texas_rrc.operators.io import write_operator_registry
from worldenergydata.texas_rrc.operators.registry import (
    RegistryPolicy,
    build_operator_registry,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        required=True,
        help="Fresh example snapshot root outside the repository",
    )
    args = parser.parse_args()
    production = pd.DataFrame(
        [
            {
                "operator_no": "001",
                "operator_name": "EXAMPLE ENERGY LLC",
                "district": "08",
                "lease_no": lease,
                "oil_gas_code": kind,
                "field_no": field,
                "production_month": f"2025-{month:02d}",
                "oil_bbl": oil,
                "gas_mcf": gas,
                "water_bbl": water,
            }
            for month in range(1, 13)
            for lease, kind, field, oil, gas, water in [
                ("L1", "O", "F1", 150, 10, 100),
                ("L2", "G", "F2", 0, 20, 150),
            ]
        ]
    )
    wells = pd.DataFrame(
        [
            {
                "operator_no": "001",
                "operator_name": "Example Energy Inc.",
                "district": "08",
                "county": "101",
                "lease_no": lease,
                "oil_gas_code": kind,
                "field_no": field,
                "well_id": well,
                "well_status": status,
            }
            for lease, kind, field, well, status in [
                ("L1", "O", "F1", "W1", "producing"),
                ("L1", "O", "F1", "W2", "inactive"),
                ("L2", "G", "F2", "W3", "producing"),
            ]
        ]
    )
    policy = RegistryPolicy(
        "2025-12", size_bands=((2, "small"), (4, "medium")), stripper_bopd=2
    )
    result = build_operator_registry(production, wells, policy)
    write_operator_registry(
        result,
        args.output_root,
        policy,
        code_revision="synthetic-example",
        allow_non_catalog_root=True,
    )
    row = result.registry.iloc[0]
    print(f"Oil: {row.oil_bbl_last12:.1f} bbl; gas: {row.gas_mcf_last12:.1f} Mcf")
    print(f"Water cut estimate: {row.water_cut_est:.1%}")
    print(
        f"Eligible gas-well median: {row.gas_mcfd_per_well_median:.1f} Mcf/calendar day"
    )
    print(
        f"Eligible wells: {row.gas_rate_eligible_well_count}; status: {row.gas_per_well_metrics_status}"
    )
    print("Oil-well BOPD and stripper share: NOT_EVALUATED")
    print(
        f"Total/producing/inactive wells: {row.well_count_total}/{row.well_count_producing}/{row.well_count_inactive}"
    )


if __name__ == "__main__":
    main()
