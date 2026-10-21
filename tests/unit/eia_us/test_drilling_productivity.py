"""Independent DPR arithmetic benchmark, revision 1 (2026-10-21).

Method: EIA, Drilling Productivity Report: Report Background and Methodological
Overview (August 2014, updated February 2019), p. 18, "Production net change":
new-well production + legacy production change. Public source:
https://www.eia.gov/petroleum/drilling/pdf/dpr_methodology.pdf

Every input below is synthetic. new_well_ip_bopd means aggregate new-well
production in bbl/day, not production per well or per rig. Rig counts have
unit rigs. No measured field values or fitted coefficients are used.
"""

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from worldenergydata.eia_us.production.drilling_productivity import (
    DrillingProductivityReport,
)


@pytest.fixture
def report_and_data():
    """Unsorted inputs: basin A has latest 4 rigs, basin B has latest 7 rigs.

    Synthetic bbl/day pairs and hand answers in input order:
    120 + (-45) = 75; 90 + (-110) = -20; 50 + (-50) = 0;
    0 + (-10) = -10; 0 + 0 = 0. Older counts (9 and 12 rigs) deliberately
    exceed the latest counts, so maximum count is not mistaken for latest.
    """
    report = DrillingProductivityReport()
    records = [
        ("2024-02", "A", "4", "120", "-45", "1075"),
        ("2024-01", "B", "12", "90", "-110", "980"),
        ("2024-01", "A", "9", "50", "-50", "1000"),
        ("2024-03", "B", "7", "0", "-10", "970"),
        ("2024-02", "B", "8", "0", "0", "980"),
    ]
    columns = [
        "period",
        "basin",
        "rig_count",
        "new_well_ip_bopd",
        "legacy_decline_bopd",
        "total_production_bopd",
    ]
    return report, report.load_all_basins([dict(zip(columns, row)) for row in records])


def test_load_all_basins_normalizes_numeric_strings(report_and_data):
    """Hand inputs: first row is 4 rigs, 120, -45 and 1075 bbl/day."""
    _, df = report_and_data
    assert df.loc[0, "rig_count"] == 4.0
    assert df.loc[0, "new_well_ip_bopd"] == 120.0
    assert df.loc[0, "legacy_decline_bopd"] == -45.0
    assert df.loc[0, "total_production_bopd"] == 1075.0
    assert all(pd.api.types.is_numeric_dtype(df[column]) for column in df.columns[2:])


def test_rig_count_summary_selects_latest_period_then_sorts(report_and_data):
    """Hand selection: B March = 7 rigs, A February = 4 rigs, descending."""
    report, df = report_and_data
    # Non-default index also checks that summary selection uses row labels.
    df.index = [50, 20, 40, 10, 30]
    before = df.copy(deep=True)
    expected = pd.DataFrame(
        {"basin": ["B", "A"], "period": ["2024-03", "2024-02"], "rig_count": [7.0, 4.0]}
    )
    assert_frame_equal(report.rig_count_summary(df), expected)
    assert_frame_equal(df, before)


def test_net_change_summary_matches_hand_answers_in_input_order(report_and_data):
    """Independent answers: 75, -20, 0, -10, 0 bbl/day; see fixture derivation."""
    report, df = report_and_data
    df.index = [50, 20, 40, 10, 30]
    before = df.copy(deep=True)
    expected = pd.DataFrame(
        {
            "basin": ["A", "B", "A", "B", "B"],
            "period": ["2024-02", "2024-01", "2024-01", "2024-03", "2024-02"],
            "net_change_bopd": [75.0, -20.0, 0.0, -10.0, 0.0],
        }
    )
    assert_frame_equal(report.net_change_summary(df), expected)
    assert_frame_equal(df, before)


@pytest.mark.parametrize(
    "method, columns",
    [
        ("rig_count_summary", ["basin", "period", "rig_count"]),
        ("net_change_summary", ["basin", "period", "net_change_bopd"]),
    ],
)
def test_empty_summary_has_declared_schema(method, columns):
    """The empty input has no invented observations and preserves output columns."""
    report = DrillingProductivityReport()
    result = getattr(report, method)(report.load_all_basins([]))
    assert result.empty
    assert result.columns.tolist() == columns
