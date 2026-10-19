"""Synthetic decline-to-NPV worked example; see docs/guides/decline-npv.md.

All amounts below are chosen example inputs, not recommended assumptions.
Rate equation: public decline-analysis manual, section 2.1.1 (2026 access).
NPV equation: NumPy Financial 1.0.0 (2019), npv Notes.
"""

import numpy as np

from worldenergydata.common.decline import exponential_rate
from worldenergydata.common.finance import net_present_value


def run_example():
    """Return the hand-checkable example's rates, cash flows and NPV.

    qi=100 volume/year, D=ln(2)/year, years=[1,2] -> rates=[50,25].
    Each rate represents the assumed volume in a unit-length annual bucket;
    these are sampled rates, not integrated continuous production volumes.
    Chosen price=4 currency/volume and capex=200 currency give
    flows=[-200,200,100]. At chosen annual r=.25,
    NPV=-200+200/1.25+100/1.25**2=-200+160+64=24 currency.
    """
    rates = exponential_rate([1, 2], initial_rate=100, nominal_decline=np.log(2))
    cash_flows = np.concatenate(([-200], rates * 4))
    return {
        "sampled_rates": rates,
        "cash_flows": cash_flows,
        "npv": net_present_value(cash_flows, discount_rate=0.25),
    }


if __name__ == "__main__":
    result = run_example()
    print(
        "Sampled annual rates: "
        + ", ".join(f"{q:.1f}" for q in result["sampled_rates"])
    )
    print("Cash flows: " + ", ".join(f"{cf:.1f}" for cf in result["cash_flows"]))
    print(f"NPV: {result['npv']:.1f}")
