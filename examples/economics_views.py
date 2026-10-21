"""Offline worked example for the canonical economics calculator.

Synthetic inputs and independent hand calculations are documented in
docs/architecture/economics-views.md. Equations: numpy-financial v1.0.0
(2019), NPV/MIRR/IRR; monthly conversion: FDAS financial module (2025).
"""

from math import isclose

import numpy as np

from worldenergydata.economics.cash_flow import CashFlowSchedule
from worldenergydata.fdas.core.financial import (
    calculate_irr,
    calculate_npv,
    excel_like_mirr,
)


def main() -> None:
    schedule = CashFlowSchedule(
        years=[0, 1],
        capex=[100, 0],
        revenue=[0, 141],
        opex=[0, 10],
        carbon_cost=[0, 10],
    )
    rate = 0.1  # Synthetic supplied annual rate; see worked example.
    flows = schedule.net_cashflows()
    npv = calculate_npv(flows, rate, period="annual")
    _, mirr = excel_like_mirr(flows, rate, period="annual")
    _, irr = calculate_irr(flows, period="annual")
    # Independent hand arithmetic: -100+121/1.1=10; 121/100-1=0.21.
    assert isclose(npv, 10)
    assert isclose(mirr, 0.21)
    assert isclose(irr, 0.21)
    print(f"Annual inputs: {flows.tolist()} USD; annual discount {rate:.1%}")
    print("Method: FDAS, first entry at t=0, annual periods")
    print(f"NPV {npv:.1f} USD; MIRR {mirr:.1%}; IRR {irr:.1%}")

    # Synthetic receipts twelve months apart: 110+110/1.1=210 USD.
    monthly = np.array([110] + [0] * 11 + [110])
    discounted = calculate_npv(monthly, rate, period="monthly")
    assert isclose(discounted, 210)
    print("Monthly inputs: 110.0 USD now and twelve months later")
    print("Method: effective annual rate converted to monthly; calendar gaps retained")
    print(f"Undiscounted {monthly.sum():.1f} USD; discounted {discounted:.1f} USD")


if __name__ == "__main__":
    main()
