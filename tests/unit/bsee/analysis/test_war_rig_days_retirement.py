"""Independent hand calculations for the retained capabilities of #1112.

All dates, identities and weights below are synthetic test inputs, not field
measurements or acceptance limits. Inclusive calendar counting follows
30 CFR 250.743(b), 2024 edition (Sunday through Saturday reporting week).
The arithmetic is written out in each test instead of calling the union engine
to construct expected results. Fluid input validity is the contract documented
in docs/modules/bsee/analysis/legacy_component_retirement.md (2026-10-20).
"""

import runpy
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.war_rig_days import rig_days_by_bore

API = "120000000100"  # Synthetic wellbore identifier.
COLUMNS = [
    "API_WELL_NUMBER",
    "WAR_START_DT",
    "WAR_END_DT",
    "WELL_ACTIVITY_CD",
    "DRILL_FLUID_WGT",
]


@pytest.mark.parametrize(
    "invalid", [None, "not reported", 0, -1, float("nan"), float("inf"), -float("inf")]
)
def test_fluid_max_uses_only_positive_finite_reported_values(invalid):
    """Hand calculation: valid set {12.0, 14.0}; its maximum is 14.0 ppg.

    Invalid input and reversed-date row (99.0 ppg) do not enter the set.
    No upper engineering limit is assumed; 99.0 is merely a test input.
    """
    war = pd.DataFrame(
        [
            [API, "2024-01-07", "2024-01-13", "DRL", "12.0"],
            [API, "2024-01-14", "2024-01-20", "DRL", 14.0],
            [API, "2024-01-21", "2024-01-27", "DRL", invalid],
            [API, "2024-02-10", "2024-02-04", "DRL", 99.0],
        ],
        columns=COLUMNS,
    )
    row = rig_days_by_bore(war).iloc[0]
    assert row.max_drill_fluid_wgt == 14.0
    assert row.war_weeks_rejected == 1


def test_no_valid_fluid_weight_remains_null():
    """The valid set is empty after excluding infinity; its maximum is unknown."""
    war = pd.DataFrame(
        [[API, "2024-01-07", "2024-01-13", "DRL", float("inf")]], columns=COLUMNS
    )
    assert pd.isna(rig_days_by_bore(war).iloc[0].max_drill_fluid_wgt)


def test_retained_capabilities_worked_example(capsys):
    """Hand calculation for examples/bsee/war_rig_days.py.

    Bore 00: DRL Jan 7-13 union Jan 10-16 = Jan 7-16 = 10 days.
    ST Jan 14-20, TA Jan 21-27, PA Feb 4-10 and COM Feb 11-17
    each cover 7 days. Overall union Jan 7-27 plus Feb 4-17 = 21+14=35.
    Rig credits: Unit A=10; Unit B=7+14=21; missing identity=7.
    Their sum is 38 because Jan 14-16 credits both rigs (3 days).
    Bore 01 adds Jan 14-20 DRL: well DRL union Jan 7-20 = 14;
    bore DRL sum=10+7=17, overall bore sum=35+7=42, well union=35.
    Valid weights on bore 00 are 12.0, 14.0, 13.5: max=14.0 ppg.
    The reporting gap Jan 28-Feb 3 contributes no measured activity.
    """
    root = Path(__file__).resolve().parents[4]
    example = runpy.run_path(str(root / "examples/bsee/war_rig_days.py"))
    bores, wells = example["analyse"]()
    row = bores.set_index("api12").loc[API]
    assert row.drilling_days == 10
    assert row.completion_days == 7
    assert row.sidetrack_days == 7
    assert row.temp_abandonment_days == 7
    assert row.perm_abandonment_days == 7
    assert row.war_days_total == 35
    assert row.rig_days_by_rig == {"Unit A": 10, "Unit B": 21, None: 7}
    assert row.max_drill_fluid_wgt == 14.0
    well = wells.iloc[0]
    assert well.drilling_days == 14
    assert well.drilling_days_additive == 17
    assert well.war_days_total == 35
    assert well.war_days_additive == 42
    assert well.overlap_days == 7
    assert "days=inclusive" in row.basis
    assert not any("npt" in column.casefold() for column in bores.columns)
    assert not any("npt" in column.casefold() for column in wells.columns)
    example["main"]()
    assert "14.0 ppg" in capsys.readouterr().out
