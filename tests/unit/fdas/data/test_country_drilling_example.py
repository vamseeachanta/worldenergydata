"""Worked example: independent day enumeration and dimensional multiplication."""

import runpy
from pathlib import Path


def test_worked_example():
    """Jan 30+31 = 2 days; Feb 1+2 = 2 days; 2*0.5 = 1 million USD
    in each month and 1+1 = 2 million USD total. All inputs are synthetic
    scenario choices, not measured costs or an inferred spud-to-release span.
    The multiplication matches CashflowEngine.calculate_drilling_capex's
    documented days * million-USD-per-day dimensional equation.
    """
    root = Path(__file__).resolve().parents[4]
    example = runpy.run_path(str(root / "examples/fdas/country_wells.py"))
    result = example["run_example"]()
    assert result["status"] == "EVALUATED"
    assert result["drilling_monthly"] == {"2024-01": 2, "2024-02": 2}
    assert result["drilling_capex_mm_usd"] == {"2024-01": 1, "2024-02": 1}
    assert result["total_drilling_capex_mm_usd"] == 2
