"""Regression test for the multi-well indexing bug in prepare_well_paths.

Before the fix, ``prepare_well_paths`` sliced each well's survey rows with
``.copy()`` (keeping the original non-zero index) and then read positionally
(``.iloc[df_row]``) but wrote by label (``.loc[df_row]``). The label writes
only aligned for the FIRST well (index 0..n); every later well kept inc/az at
0 -> a dead-vertical path -> plus phantom ``md==0`` rows. The fix adds
``.reset_index(drop=True)`` to the slice. This test guards against regression
by asserting the SECOND well is genuinely deviated.
"""

from __future__ import annotations

import pandas as pd

from worldenergydata.bsee.analysis.well_api12 import WellAPI12


def _two_well_inputs():
    """Two deviated wells; survey rows ordered so well B's slice index is non-zero."""
    rows = []
    for api12, az_deg in ((608124000401, 45), (608124000402, 135)):
        for md, inc in ((0, 0), (2000, 0), (5000, 20), (8000, 35)):
            rows.append(
                {
                    "API12": api12,
                    "API_WELL_NUMBER": api12,
                    "SURVEY_POINT_MD": md,
                    "INCL_ANG_DEG_VAL": inc,
                    "INCL_ANG_MIN_VAL": 0,
                    "DIR_DEG_VAL": az_deg,
                    "DIR_MINS_VAL": 0,
                    "WELL_N_S_CODE": "N",
                    "WELL_E_W_CODE": "E",
                    "SURVEY_POINT_TVD": md,
                }
            )
    directional_surveys = pd.DataFrame(rows)

    merged = pd.DataFrame(
        {
            "API12": [608124000401, 608124000402],
            "API10": [6081240004, 6081240004],
            "Well Name": ["WELL A-001", "WELL A-002"],
            "Sidetrack and Bypass": ["ST00", "ST00"],
            "SURF_x_rel": [0.0, 500.0],
            "SURF_y_rel": [0.0, 500.0],
            "Water Depth (feet)": [6600, 6600],
            "Total Measured Depth": [8000, 8000],
            "Total Depth Date": ["2023-06-15", "2023-07-20"],
            "Spud Date": ["2023-04-10", "2023-05-01"],
        }
    )
    return directional_surveys, {"merged_api12_df": merged}


def test_prepare_well_paths_multi_well_second_well_is_deviated():
    directional_surveys, well_data = _two_well_inputs()
    api = WellAPI12()
    api.prepare_well_paths(directional_surveys, well_data)

    paths = api.output_data_well_path
    assert set(paths) == {608124000401, 608124000402}

    for api12, survey in paths.items():
        # No phantom rows: every md must come from the input (max 8000).
        assert survey["md"].max() == 8000, f"{api12} has phantom/zero-MD rows"
        # The well is genuinely deviated: lateral offset must be non-trivial,
        # not stuck at the surface (the pre-fix dead-vertical symptom).
        lateral = (survey["x_coor"].abs() + survey["y_coor"].abs()).max()
        assert lateral > 100.0, f"{api12} rendered dead-vertical (offset={lateral})"
