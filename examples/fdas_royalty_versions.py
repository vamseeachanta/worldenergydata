"""Synthetic royalty migration example; see docs/modules/fdas/ROYALTY-VERSIONS.md.

Rates: Gulf deck revision-1 source_ref (2026), 12.5% dry, 18.75% deep water;
legacy-v1 preserves core/config.py at revision f82ff2f. All production, price,
cost and discount inputs below are synthetic, not field estimates.
"""

from datetime import datetime

import numpy as np
import pandas as pd

from worldenergydata.fdas.analysis.cashflow import CashflowEngine
from worldenergydata.fdas.core.config import AssumptionsManager
from worldenergydata.fdas.core.financial import calculate_npv


def main():
    production = pd.DataFrame(
        {"YEAR_MONTH": ["2025-01", "2025-02"], "MONTHLY_OIL_BBL": [1000, 1000]}
    )
    prices = {"2025-01": 100.0, "2025-02": 100.0}
    print("system version monthly_royalty monthly_net npv_zero npv_12_percent")
    for system in ("dry", "subsea15", "subsea20", "default"):
        for version in ("source-note-v2", "legacy-v1"):
            assumptions = AssumptionsManager(version=version)
            assumptions.assumptions["HOST_CAPEX_MM"] = 0.0
            assumptions.assumptions["VARIABLE_OPEX_$/BBL"] = 10.0
            engine = CashflowEngine(assumptions, dev_system=system)
            rows = engine.generate_monthly_cashflow(
                production, {}, prices, datetime(2025, 1, 1)
            )
            values = np.array([row.net_cashflow_usd for row in rows])
            print(
                f"{system} {assumptions.version} {rows[0].royalty_usd:.1f} "
                f"{rows[0].net_cashflow_usd:.1f} {calculate_npv(values, 0.0):.1f} "
                f"{calculate_npv(values, 0.12):.1f}"
            )


if __name__ == "__main__":
    main()
