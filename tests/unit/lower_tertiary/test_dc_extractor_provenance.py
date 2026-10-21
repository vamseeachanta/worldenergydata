"""Offline workbook tests with independently counted synthetic WAR dates."""

import subprocess
import sys

import pandas as pd
import pytest

from tests.unit.lower_tertiary.test_dc_provenance import REPO

EXTRACTOR = (
    REPO
    / "docs/modules/bsee/analysis/production/FDAS_V30"
    / "extract_drilling_completion_days.py"
)
LABELS = ["BASIS", "PND_DAYS", "DAYS_STATUS"]


@pytest.fixture(scope="module", params=["DRL_COM", "DRL_COM_PND"])
def workbook(tmp_path_factory, request):
    """Hand calculation: Jan 5..11 = 11 - 5 + 1 = 7 DRL,
    Jan 12..18 = 18 - 12 + 1 = 7 COM, Jan 19..25 = 25 - 19 + 1 = 7 PND.
    Disjoint inclusive weeks give D&C = 7 + 7 = 14,
    and separate PND = 7 under DRL_COM. DRL_COM_PND instead credits
    completion = 7 + 7 = 14 while separate PND stays 7.
    No dates are milestones in this fixture: WAR coverage alone establishes
    the day counts. Another bore
    has an unclassified week, so its activity counts remain unknown. A third
    has no valid WAR endpoints, so every activity count remains unknown.

    Source for inclusive calendar-week counting: 30 CFR 250.743(a),
    2016 final rule, as amended, accessed 2026:
    https://www.law.cornell.edu/cfr/text/30/250.743
    These dates and API identifiers are synthetic inputs, not field data.
    """
    folder = tmp_path_factory.mktemp("extractor")
    leases = pd.DataFrame(
        [{"LEASE_NUM": "G00001", "LEASE_NAME": "synthetic", "WATER_DEPTH": None}]
    )
    main = pd.DataFrame(
        [
            {
                "SN_WAR": sn,
                "API_WELL_NUMBER": api,
                "SURF_LEASE_NUM": "G00001",
                "WELL_NAME": "synthetic",
                "LEASE_NAME": "synthetic",
                "WAR_START_DT": start,
                "WAR_END_DT": end,
            }
            for sn, api, start, end in [
                (1, "100000000100", "2020-01-05", "2020-01-11"),
                (2, "100000000100", "2020-01-12", "2020-01-18"),
                (3, "100000000100", "2020-01-19", "2020-01-25"),
                (4, "100000000200", "2020-01-05", "2020-01-11"),
                (5, "100000000300", None, None),
            ]
        ]
    )
    boreholes = pd.DataFrame(
        {
            "API_WELL_NUMBER": ["100000000100", "100000000200", "100000000300"],
            "WELL_SPUD_DATE": [None, None, None],
            "TOTAL_DEPTH_DATE": [None, None, None],
        }
    )
    remarks = pd.DataFrame(columns=["SN_WAR", "TEXT_REMARK"])
    prop = pd.DataFrame(
        {"SN_WAR": [1, 2, 3], "WELL_ACTIVITY_CD": ["DRL", "COM", "PND"]}
    )
    argv = [sys.executable, str(EXTRACTOR)]
    for flag, frame in (
        ("leases", leases),
        ("war-main", main),
        ("war-boreholes", boreholes),
        ("war-remarks", remarks),
        ("war-prop", prop),
    ):
        path = folder / f"{flag}.csv"
        frame.to_csv(path, index=False)
        argv.extend([f"--{flag}", str(path)])
    target = folder / "days.xlsx"
    result = subprocess.run(
        [*argv, "--basis", request.param, "--out", str(target)],
        cwd=folder,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return pd.read_excel(target, sheet_name=None), request.param


@pytest.mark.parametrize("sheet", ["Sheet1", "Diagnostics"])
def test_every_day_bearing_sheet_has_provenance(workbook, sheet):
    workbook, basis = workbook
    table = workbook[sheet].set_index("API_WELL_NUMBER")
    assert set(LABELS) <= set(table.columns)
    measured = table.loc[100000000100]
    assert (
        measured["DRILLING_DAYS"],
        measured["COMPLETION_DAYS"],
        measured["PND_DAYS"],
    ) == (7, {"DRL_COM": 7, "DRL_COM_PND": 14}[basis], 7)
    assert measured["DAYS_STATUS"] == "war_covered"
    assert measured["BASIS"].startswith(basis + "(")
    unknown = table.loc[100000000200]
    assert pd.isna(unknown["DRILLING_DAYS"])
    assert pd.isna(unknown["COMPLETION_DAYS"])
    assert unknown["DAYS_STATUS"] == "war_covered_no_activity_code"
    absent = table.loc[100000000300]
    assert absent[["DRILLING_DAYS", "COMPLETION_DAYS", "PND_DAYS"]].isna().all()
    assert absent["DAYS_STATUS"] == "no_war_activity"
    pd.testing.assert_frame_equal(
        workbook["Sheet1"][LABELS], workbook["Diagnostics"][LABELS]
    )
