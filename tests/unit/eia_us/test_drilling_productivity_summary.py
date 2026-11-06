"""Independent normalized-frame examples for DPR summaries (issue #1607).

All inputs are arbitrary synthetic examples. Each basin has January and February
observations: rig counts 3 then 5 for basin A, 7 then 2 for basin B. Latest counts
therefore sort as A: 5, B: 2. Hand calculations in bbl/day are 120 + (-50) = 70
for A and 40 + (-60) = -20 for B at each period. Dates establish order only.
"""

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from worldenergydata.eia_us.production.drilling_productivity import (
    DrillingProductivityReport,
)


@pytest.fixture
def normalized_frame():
    """Interleave basins and dates, with non-default labels, without a loader."""
    return pd.DataFrame(
        {
            "basin": ["B", "A", "B", "A"],
            "period": pd.to_datetime(
                ["2024-02-01", "2024-01-01", "2024-01-01", "2024-02-01"]
            ),
            "rig_count": [2, 3, 7, 5],
            "new_well_ip_bopd": [40.0, 120.0, 40.0, 120.0],
            "legacy_decline_bopd": [-60.0, -50.0, -60.0, -50.0],
        },
        index=["b-latest", "a-earlier", "b-earlier", "a-latest"],
    )


@pytest.mark.parametrize("reverse_input", [False, True])
def test_latest_rig_count_and_order(normalized_frame, reverse_input):
    frame = normalized_frame.iloc[::-1] if reverse_input else normalized_frame
    before = frame.copy(deep=True)

    result = DrillingProductivityReport().rig_count_summary(frame)

    expected = pd.DataFrame(
        {
            "basin": ["A", "B"],
            "period": pd.to_datetime(["2024-02-01", "2024-02-01"]),
            "rig_count": [5, 2],
        }
    )
    assert_frame_equal(result, expected, check_exact=True)
    assert_frame_equal(frame, before, check_exact=True)


def test_net_change_hand_arithmetic(normalized_frame):
    before = normalized_frame.copy(deep=True)

    result = DrillingProductivityReport().net_change_summary(normalized_frame)

    expected = pd.DataFrame(
        {
            "basin": ["B", "A", "B", "A"],
            "period": pd.to_datetime(
                ["2024-02-01", "2024-01-01", "2024-01-01", "2024-02-01"]
            ),
            "net_change_bopd": [-20.0, 70.0, -20.0, 70.0],
        }
    )
    assert_frame_equal(result, expected, check_exact=True)
    assert_frame_equal(normalized_frame, before, check_exact=True)


@pytest.mark.parametrize("with_columns", [False, True])
def test_empty_summary_schema(normalized_frame, with_columns):
    """Both a bare empty frame and an empty normalized frame retain the schema."""
    frame = normalized_frame.iloc[:0] if with_columns else pd.DataFrame()
    before = frame.copy(deep=True)
    report = DrillingProductivityReport()

    rigs = report.rig_count_summary(frame)
    net = report.net_change_summary(frame)

    assert rigs.empty
    assert list(rigs.columns) == ["basin", "period", "rig_count"]
    assert net.empty
    assert list(net.columns) == ["basin", "period", "net_change_bopd"]
    assert_frame_equal(frame, before, check_exact=True)
