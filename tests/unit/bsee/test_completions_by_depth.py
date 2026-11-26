"""Conservation and hand-count checks for the completions example.

Written before the counting code. Each test asserts an invariant that a wrong
count would break. Tolerances are fixed here, before the first run:

- every count comparison is exact (tolerance 0);
- a percentage stored to one decimal equals its counts within 0.05 point;
- day quantiles are exact for the stated interpolation rule.

Three levels:

- A, synthetic rows counted by hand in this file; always runs.
- B, the delivered output tables; always runs, reads no raw archive.
- C, the raw BSEE archives of the series basis; runs when the environment
  variable BSEE_SERIES_BASIS_DIR names the folder that holds them, and is
  skipped only when it is not set. The comparator classes are stated per test.

The hand counts of level B and C were taken from the extracted text with a
plain listing, before any counting code existed (README, "Hand counts").
"""

import csv
import datetime as dt
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
EXAMPLE = ROOT / "examples/bsee/completions_by_depth"
C6 = ROOT / "examples/bsee/interventions_by_depth"
sys.path.insert(0, str(C6))
sys.path.insert(0, str(EXAMPLE))
import count_completions as cc  # noqa: E402
import count_interventions as ci  # noqa: E402

OUT = EXAMPLE / "output"
B = ci.BANDS  # under 100 m, 100 to 500 m, 500 to 1500 m, 1500 m and deeper, no depth

# Hand counts on the 23 Nov 2026 files (README, "Hand counts").
HAND_APPROVALS_2025_03 = {
    "comp_permits_listed": 30,
    "with_change_zone": 3,
    "completion_approvals": 27,
    "by_band": {B[0]: 8, B[1]: 0, B[2]: 5, B[3]: 14, B[4]: 0},
    "initial_completion": 25,
    "initial_by_band": {B[0]: 7, B[1]: 0, B[2]: 5, B[3]: 13, B[4]: 0},
    "bores_with_initial_completion": 14,
}
HAND_REPORTS_2025_Q1 = {
    "completion_reports": 18,
    "by_band": {B[0]: 4, B[1]: 2, B[2]: 5, B[3]: 7, B[4]: 0},
    "bores": 17,
}


# --------------------------------------------------------------------------
# Level A: synthetic rows, counted by hand
# --------------------------------------------------------------------------
def bore_rows():
    def row(api, depth, region="G"):
        return {"API_WELL_NUMBER": api, "WATER_DEPTH": depth, "REGION_CODE": region}

    return [
        row("177000000100", "200"),  # 61 m
        row("177000000200", "1000"),  # 305 m
        row("608000000300", "3000"),  # 914 m
        row("608000000301", "3000"),
        row("608000000400", "6000"),  # 1,829 m
        row("608000000500", ""),  # no depth on this bore
        row("608000000501", "5000"),  # 1,524 m, the only depth of the well
        row("608000000600", "100"),
        row("608000000601", "9000"),  # two depths in one well: no fallback
        row("043000000700", "300", "P"),  # Pacific
    ]


def apm_rows():
    def row(sn, api, date, code="COMP", lease="G00001"):
        return {
            "SN_APM": sn,
            "API_WELL_NUMBER": api,
            "ACC_STATUS_DATE": date,
            "APM_OP_CD": code,
            "SURF_LEASE_NUM": lease,
        }

    rows = [
        row("-1", "177000000100", "3/1/2006 10:00:00 AM"),
        row("-2", "177000000100", "4/1/2006 9:15:00 AM"),
        row("-3", "177000000200", "5/5/2007 8:00:00 AM"),  # change zone
        row("-4", "177000000200", "6/1/2007 8:00:00 AM"),  # perforations
        row("-5", "608000000301", "12/31/2006 11:59:59 PM"),
        row("-6", "608000000400", "1/1/2007 12:00:00 AM"),  # plugback
        row("-7", "608000000400", "2/2/2007 1:00:00 PM", code="WORKOVER"),
        row("-8", "608000000500", "7/7/2008 1:00:00 PM"),  # depth by well
        row("-9", "608000000602", "8/8/2008 1:00:00 PM"),  # two depths
        row("-10", "043000000700", "9/9/2008 1:00:00 PM", lease="P00001"),
        row("-11", "999999999999", "10/10/2008 1:00:00 PM", lease="G12345"),
        row("-12", "177000000100", "3/3/2009 1:00:00 PM"),  # no sub-operation
        row("-13", "608000000400", "5/5/2009 1:00:00 PM"),  # drills new hole
        row("-14", "608000000400", "6/6/2009 1:00:00 PM"),  # negated
    ]
    return rows + [dict(rows[0])]  # one raw row repeated in the feed


def subop_rows():
    pairs = [
        ("-1", "INITCOMP"),
        ("-2", "INITCOMP"),
        ("-2", "FRAC"),
        ("-2", "FRAC"),
        ("-3", "ZONE"),
        ("-4", "PERF"),
        ("-5", "INITCOMP"),
        ("-6", "INITCOMP"),
        ("-6", "PLUGBACK"),
        ("-7", "INITCOMP"),
        ("-8", "INITCOMP"),
        ("-9", "OTHRCOMP"),
        ("-10", "INITCOMP"),
        ("-11", "INITCOMP"),
        ("-13", "INITCOMP"),
        ("-14", "INITCOMP"),
    ]
    return [{"SN_APM_FK": sn, "APM_SUBOP_CD": code} for sn, code in pairs]


def narrative_rows():
    return [
        {"SN_APM": "-13", "APM_OP_DESC": "Drill a new sidetrack to the target sand."},
        {
            "SN_APM": "-14",
            "APM_OP_DESC": "Complete the well. Do not drill a sidetrack.",
        },
    ]


def eor_rows():
    def row(sn, code, api, status, date, flag, lease="G00001"):
        return {
            "SN_EOR": sn,
            "EOR_OPERATION_CD": code,
            "API_WELL_NUMBER": api,
            "BOREHOLE_STAT_CD": status,
            "BOREHOLE_STAT_DT": date,
            "SURF_LEASE_NUMBER": lease,
            "SUBSEA_COMPLETION_FLAG": flag,
        }

    return [
        row("-101", "C", "177000000100", "COM", "3/20/2006", "NO"),
        row("-102", "C", "177000000100", "COM", "3/20/2006", "NO"),
        row("-103", "W", "177000000100", "COM", "3/20/2006", "NO"),
        row("-104", "C", "608000000301", "COM", "1/15/2007", "YES"),
        row("-105", "C", "608000000400", "COM", "7/1/2009", ""),
        row("-106", "C", "608000000400", "COM", "8/1/2010", "YES"),
        row("-107", "A", "608000000400", "PA", "1/1/2020", "NO"),
        row("-108", "C", "043000000700", "COM", "2/2/2008", "NO", lease="P00001"),
        row("-109", "C", "177000000200", "TA", "6/30/2007", "NO"),
    ]


def interval_rows():
    rows = [
        ("-101", "-1001", "S1", "POW"),
        ("-102", "-1002", "S2", "PGW"),
        ("-103", "-1003", "S3", "POW"),  # on a workover report: not read
        ("-104", "-1004", "D1", "POW"),
        ("-104", "-1005", "D2", "GLO"),
        ("-106", "-1006", "S1", "WIW"),
        ("-109", "-1009", "S1", "GSI"),
    ]
    keys = ["SN_EOR_FK", "SN_EOR_WELL_COMP", "INTERVAL", "COMP_STATUS_CD"]
    return [dict(zip(keys, r)) for r in rows]


def perf_rows():
    counts = {"-1001": 2, "-1002": 1, "-1004": 1, "-1006": 3, "-1009": 1, "-9999": 4}
    return [
        {"SN_EOR_WELL_COMP_FK": comp} for comp, n in counts.items() for _ in range(n)
    ]


@pytest.fixture()
def approvals():
    return cc.completion_approvals(
        apm_rows(), subop_rows(), narrative_rows(), bore_rows()
    )


@pytest.fixture()
def reports():
    return cc.completion_reports(eor_rows(), bore_rows())


def tally(events, key):
    out = {}
    for e in events:
        out[e[key]] = out.get(e[key], 0) + 1
    return out


def test_small_sample_matches_the_hand_count(approvals):
    assert sorted(a["sn"] for a in approvals) == sorted(
        ["-1", "-2", "-4", "-5", "-8", "-9", "-11", "-12", "-14"]
    )
    assert tally(approvals, "kind") == {
        "initial completion": 6,
        "other completion work": 3,
    }
    assert tally(approvals, "year") == {2006: 3, 2007: 1, 2008: 3, 2009: 2}
    assert tally(approvals, "band") == {B[0]: 3, B[1]: 1, B[2]: 1, B[3]: 2, B[4]: 2}
    assert [a["sn"] for a in approvals if a["frac"]] == ["-2"]


def test_each_completion_is_counted_once(approvals):
    # The feed repeats one raw row and one sub-operation row; neither may
    # add a count. Removing the repeat from the input must change nothing.
    assert len({a["sn"] for a in approvals}) == len(approvals) == 9
    once = cc.completion_approvals(
        apm_rows()[:-1], subop_rows(), narrative_rows(), bore_rows()
    )
    assert [a["sn"] for a in once] == [a["sn"] for a in approvals]


def test_conflicting_repeat_of_a_permit_stops_the_count():
    rows = apm_rows()
    rows.append(dict(rows[0], API_WELL_NUMBER="177000000200"))
    with pytest.raises(ValueError):
        cc.completion_approvals(rows, subop_rows(), narrative_rows(), bore_rows())


def test_band_and_year_counts_sum_to_the_total(approvals):
    years = range(2006, 2010)
    table = cc.year_band_table(approvals, years, kinds=cc.KINDS)
    # The grid is complete: every year, band and kind has a row, zero or not.
    assert len(table) == len(years) * len(B) * len(cc.KINDS)
    total = sum(r["count"] for r in table)
    assert total == len(approvals) == 9
    by_band = {b: sum(r["count"] for r in table if r["band"] == b) for b in B}
    by_year = {y: sum(r["count"] for r in table if r["year"] == y) for y in years}
    assert sum(by_band.values()) == total and sum(by_year.values()) == total
    assert by_band == {B[0]: 3, B[1]: 1, B[2]: 1, B[3]: 2, B[4]: 2}
    assert by_year == {2006: 3, 2007: 1, 2008: 3, 2009: 2}
    # A narrower window drops the 2006 approvals and reports them as outside.
    narrow = cc.year_band_table(approvals, range(2007, 2010), kinds=cc.KINDS)
    assert sum(r["count"] for r in narrow) == 6
    checks = cc.conservation(approvals, narrow, range(2007, 2010))
    assert checks["outside_window"] == 3
    assert checks["in_window"] + checks["outside_window"] == checks["counted"] == 9
    assert checks["ok"] is True


def test_conservation_fails_on_a_dropped_or_doubled_row(approvals):
    years = range(2006, 2010)
    table = cc.year_band_table(approvals, years, kinds=cc.KINDS)
    assert cc.conservation(approvals, table, years)["ok"] is True
    doubled = table + [dict(table[0], count=1)]
    assert cc.conservation(approvals, doubled, years)["ok"] is False
    assert cc.conservation(approvals + [approvals[0]], table, years)["ok"] is False


def test_shared_rule_is_the_group_c6_excludes():
    # The kind is defined only where C6 classifies the permit as its excluded
    # completion group; every other permit is left to C6.
    cases = [
        ("COMP", {"INITCOMP"}, ""),
        ("COMP", {"INITCOMP", "FRAC"}, ""),
        ("COMP", {"PERF"}, ""),
        ("COMP", set(), ""),
        ("COMP", {"ZONE"}, ""),
        ("COMP", {"INITCOMP", "ZONE"}, ""),
        ("COMP", {"ZONEISO"}, ""),
        ("COMP", {"INITCOMP", "PLUGBACK"}, ""),
        ("COMP", {"INITCOMP"}, "Drill a new sidetrack to the target sand."),
        ("COMP", {"INITCOMP"}, "Do not drill a sidetrack."),
        ("WORKOVER", {"INITCOMP"}, ""),
        ("ENHANCE", {"INITCOMP"}, ""),
        ("ABANDON", {"PERMABAN"}, ""),
        ("SIDETRACK", {"INITCOMP"}, ""),
    ]
    for code, subs, text in cases:
        shared = ci.classify_operation(code, subs, text) == ci.GROUPS[7]
        kind = cc.completion_kind(code, subs, text)
        assert (kind is not None) == shared, (code, subs, text)
        if shared:
            expected = cc.KINDS[0] if "INITCOMP" in subs else cc.KINDS[1]
            assert kind == expected
    assert ci.GROUPS[7] == "initial completion excluded"
    assert cc.SHARED_GROUP == ci.GROUPS[7]


def test_bands_are_the_bands_c6_uses():
    assert cc.BANDS == ci.BANDS
    for feet in [0, 328, 328.1, 1640.4, 1640.5, 4921.2, 4921.3, 9000, "", "x", -1]:
        assert cc.band_of(feet) == ci.band_from_feet(feet)


def test_first_approval_per_bore(approvals):
    first = cc.first_per_bore([a for a in approvals if a["kind"] == cc.KINDS[0]])
    assert {f["api12"]: f["sn"] for f in first} == {
        "177000000100": "-1",
        "608000000301": "-5",
        "608000000500": "-8",
        "999999999999": "-11",
        "608000000400": "-14",
    }
    assert tally(first, "year") == {2006: 2, 2008: 2, 2009: 1}
    assert len({f["api10"] for f in first}) == 5


def test_reports_match_the_hand_count(reports):
    assert sorted(r["sn"] for r in reports) == sorted(
        ["-101", "-102", "-104", "-105", "-106", "-109"]
    )
    assert tally(reports, "year") == {2006: 2, 2007: 2, 2009: 1, 2010: 1}
    assert tally(reports, "band") == {B[0]: 2, B[1]: 1, B[2]: 1, B[3]: 2}
    first = cc.first_per_bore(reports)
    assert {f["api12"]: f["date"] for f in first} == {
        "177000000100": dt.date(2006, 3, 20),
        "608000000301": dt.date(2007, 1, 15),
        "608000000400": dt.date(2009, 7, 1),
        "177000000200": dt.date(2007, 6, 30),
    }


def test_bore_attributes_match_the_hand_count(reports):
    attrs = cc.bore_attributes(reports, interval_rows(), perf_rows())
    assert {k: v["fluid"] for k, v in attrs.items()} == {
        "177000000100": "oil and gas",
        "608000000301": "oil",
        "608000000400": "injection or source",
        "177000000200": "gas",
    }
    assert {k: v["subsea"] for k, v in attrs.items()} == {
        "177000000100": "NO",
        "608000000301": "YES",
        "608000000400": "YES",
        "177000000200": "NO",
    }
    assert {k: v["intervals"] for k, v in attrs.items()} == {
        "177000000100": 2,
        "608000000301": 2,
        "608000000400": 1,
        "177000000200": 1,
    }
    assert {k: v["dual"] for k, v in attrs.items()} == {
        "177000000100": False,
        "608000000301": True,
        "608000000400": False,
        "177000000200": False,
    }
    # Perforated intervals per completion interval, over all six intervals
    # read: 2, 1, 1, 0, 3, 1. The orphan rows and the workover report's
    # interval are not read.
    assert sorted(n for v in attrs.values() for n in v["perforations"]) == [
        0,
        1,
        1,
        1,
        2,
        3,
    ]


def test_bore_without_an_interval_row_is_not_given_a_fluid():
    only = [r for r in cc.completion_reports(eor_rows(), bore_rows())]
    attrs = cc.bore_attributes(only, [], [])
    assert {v["fluid"] for v in attrs.values()} == {"not reported"}
    assert {v["intervals"] for v in attrs.values()} == {0}


def test_approval_to_report_match(approvals, reports):
    first_a = cc.first_per_bore([a for a in approvals if a["kind"] == cc.KINDS[0]])
    first_r = cc.first_per_bore(reports)
    match = cc.match_summary(first_a, first_r)
    assert match["bores_with_initial_completion_approval"] == 5
    assert match["of_which_with_completion_report"] == 3
    assert match["bores_with_completion_report"] == 4
    assert match["of_which_with_initial_completion_approval"] == 3
    assert match["lag_days"] == [15, 19, 25]
    assert match["lag_median_days"] == 19


def test_quantile_rule():
    # Linear interpolation between closest ranks, positions 0 to n - 1.
    assert cc.quantile([15, 19, 25], 0.5) == 19
    assert cc.quantile([1, 2, 3, 4], 0.5) == 2.5
    assert cc.quantile([1, 2, 3, 4], 0.25) == 1.75
    assert cc.quantile([7], 0.75) == 7
    with pytest.raises(ValueError):
        cc.quantile([], 0.5)


def test_dates_and_window():
    assert cc.parse_date("12/19/2023 10:49:45 AM") == dt.date(2023, 12, 19)
    assert cc.parse_date("1/3/2014") == dt.date(2014, 1, 3)
    assert cc.parse_date("") is None and cc.parse_date("not a date") is None
    # The first full year is the first year whose January is in the feed.
    assert cc.window(dt.date(2004, 4, 2), dt.date(2026, 11, 23)) == (2005, 2025, 2026)
    assert cc.window(dt.date(2005, 1, 9), dt.date(2025, 12, 31)) == (2005, 2025, None)


def test_basis_digest_mismatch_stops(tmp_path):
    (tmp_path / "a.zip").write_bytes(b"abc")
    good = {
        "files": [
            {
                "name": "a.zip",
                "bytes": 3,
                "sha256": "ba7816bf8f01cfea414140de5dae2223"
                "b00361a396177a9cb410ff61f20015ad",
            }
        ]
    }
    assert cc.verify_basis(tmp_path, good) == ["a.zip"]
    bad = {"files": [dict(good["files"][0], sha256="0" * 64)]}
    with pytest.raises(cc.BasisError):
        cc.verify_basis(tmp_path, bad)
    missing = {"files": [dict(good["files"][0], name="b.zip")]}
    with pytest.raises(cc.BasisError):
        cc.verify_basis(tmp_path, missing)


def test_suboperations_are_counted_by_kind(approvals):
    # Hand count on the sample: nine approvals, six initial (-1, -2, -5, -8,
    # -11, -14) and three other (-4 PERF, -9 OTHRCOMP, -12 no sub-operation).
    subcodes = cc.grouped(subop_rows(), "SN_APM_FK", "APM_SUBOP_CD")
    rows = cc.suboperation_table(approvals, subcodes, {"PERF": "Modify Perforations"})
    got = {
        r["suboperation"]: (
            r["approvals"],
            r["on_initial_completion"],
            r["on_other_completion_work"],
        )
        for r in rows
    }
    assert got == {
        "INITCOMP": (6, 6, 0),
        "FRAC": (1, 1, 0),
        "PERF": (1, 0, 1),
        "OTHRCOMP": (1, 0, 1),
        "(none)": (1, 0, 1),
    }
    assert rows[0]["suboperation"] == "INITCOMP"
    perf = next(r for r in rows if r["suboperation"] == "PERF")
    assert perf["description"] == "Modify Perforations"
    assert perf["share_of_other_percent"] == 33.3


def test_first_drilling_period_and_approval_observed_by_snapshot():
    cutoff = dt.date(2026, 11, 23)
    wells = [
        ("a", "2005-01-01", B[0], "exploration"),
        ("b", "2009-12-31", B[0], "exploration"),
        ("c", "2010-01-01", B[1], "exploration"),
        ("d", "2025-01-01", B[3], "development"),
        ("e", "2026-11-23 16:30", B[3], "development"),
        ("f", "2026-11-24", B[3], "development"),
        ("g", "2004-12-31", B[0], "exploration"),
        ("h", None, B[0], "exploration"),
        ("i", "2009-01-01", B[0], "other or not stated"),
        ("j", "2020-01-01", "no depth", "development"),
        ("k", "2015-01-01", B[2], "development"),
        ("l", "2004-12-31", "no depth", "exploration"),
        ("m", "2004-12-31", B[1], "other or not stated"),
    ]
    inventory = ci.pd.DataFrame(
        [(api, ci.pd.Timestamp(spud), band) for api, spud, band, _ in wells],
        columns=["api10", "spud", "band"],
    )
    types = {api: kind for api, _, _, kind in wells}
    initial = [
        dict(api10="a", date=dt.date(2016, 1, 1)),
        dict(api10="a", date=dt.date(2018, 1, 1)),
        dict(api10="b", date=None),
        dict(api10="c", date=dt.date(2026, 11, 24)),
        dict(api10="e", date=cutoff),
        dict(api10="k", date=dt.date(2004, 12, 31)),
    ]
    assert cc.drilled_spud_exclusions(inventory, types, 2005, cutoff) == {
        "before_first_year": 1,
        "after_file_date": 1,
    }
    rows = cc.drilled_period_table(inventory, types, initial, cutoff)
    assert list(dict.fromkeys(r["group"] for r in rows)) == [
        "Exploratory wells",
        "Development wells",
    ]
    cells = {(r["group"], r["period"], r["band"]): r for r in rows}
    assert len(cells) == len(rows) == 40
    actual = {
        key: (
            r["wells_first_drilled"],
            r["with_initial_completion_approval"],
            r["share_percent"],
        )
        for key, r in cells.items()
        if r["wells_first_drilled"]
    }
    assert actual == {
        ("Exploratory wells", "2005 to 2009", "Under 100 m"): (2, 1, 50.0),
        ("Exploratory wells", "2010 to 2014", "100 to 500 m"): (1, 0, 0.0),
        ("Development wells", "2015 to 2019", "500 to 1,500 m"): (1, 1, 100.0),
        ("Development wells", "2025 to 2026 (partial)", "1,500 m and deeper"): (
            2,
            1,
            50.0,
        ),
    }
    assert all(r["share_percent"] == "" for r in rows if not r["wells_first_drilled"])
    assert all(
        "little time" in r["follow_up"].lower()
        for r in rows
        if r["period"] == "2025 to 2026 (partial)"
    )


# --------------------------------------------------------------------------
# Level B: the delivered output tables (comparator class: conservation, and
# the hand counts above; the C6 comparison is read from verification.json)
# --------------------------------------------------------------------------
def table(name, out=OUT):
    with open(out / f"{name}.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def js(name):
    return json.loads((OUT / f"{name}.json").read_text(encoding="utf-8"))


def test_delivered_approvals_conserve():
    rows = table("completion_approvals_by_year_band")
    summary = js("summary")
    years = range(summary["first_full_year"], summary["partial_year"] + 1)
    assert len(rows) == len(years) * len(B) * len(cc.KINDS)
    assert {int(r["year"]) for r in rows} == set(years)
    total = sum(int(r["approvals"]) for r in rows)
    assert total == summary["completion_approvals"]
    by_band = {b: sum(int(r["approvals"]) for r in rows if r["band"] == b) for b in B}
    by_year = {
        y: sum(int(r["approvals"]) for r in rows if int(r["year"]) == y) for y in years
    }
    by_kind = {
        k: sum(int(r["approvals"]) for r in rows if r["kind"] == k) for k in cc.KINDS
    }
    assert sum(by_band.values()) == total
    assert sum(by_year.values()) == total
    assert sum(by_kind.values()) == total
    assert by_band == summary["completion_approvals_by_band"]
    assert by_kind[cc.KINDS[0]] == summary["initial_completion_approvals"]
    assert {str(y): n for y, n in by_year.items()} == summary[
        "completion_approvals_by_year"
    ]


def test_delivered_counts_equal_the_c6_count():
    # Comparator class: cross-solver. C6's own code, unmodified, classified
    # the same archives in the same run; verification.json holds both sides.
    check = js("verification")["c6_cross_check"]
    rows = table("completion_approvals_by_year_band")
    total = sum(int(r["approvals"]) for r in rows)
    assert check["approvals"]["this_article"] == total
    assert check["approvals"]["c6_code"] == total
    assert check["approvals"]["cells_compared"] == len(rows) // len(cc.KINDS)
    assert check["approvals"]["cells_different"] == 0
    reports = table("completion_reports_by_year_band")
    total_reports = sum(int(r["reports"]) for r in reports)
    assert check["reports"]["this_article"] == total_reports
    assert check["reports"]["c6_code"] == total_reports
    assert check["reports"]["cells_different"] == 0
    assert check["tolerance"] == 0


def test_delivered_bores_conserve():
    rows = table("bores_first_completed_by_year_band")
    summary = js("summary")
    for basis, key in [
        ("approval", "bores_first_completed_by_approval"),
        ("report", "bores_first_completed_by_report"),
    ]:
        part = [r for r in rows if r["basis"] == basis]
        assert sum(int(r["bores"]) for r in part) == summary[key]
    # A bore is one approval at least: bores cannot exceed approvals.
    assert (
        summary["bores_first_completed_by_approval"]
        <= summary["initial_completion_approvals"]
    )
    assert (
        summary["wells_first_completed_by_approval"]
        <= summary["bores_first_completed_by_approval"]
    )
    attrs = table("bore_attributes_by_band")
    for attribute in {r["attribute"] for r in attrs}:
        part = [r for r in attrs if r["attribute"] == attribute]
        assert (
            sum(int(r["bores"]) for r in part)
            == summary["bores_first_completed_by_report"]
        ), attribute
    fluid = table("fluid_by_year")
    assert (
        sum(int(r["bores"]) for r in fluid)
        == summary["bores_first_completed_by_report"]
    )


def test_delivered_hand_counts():
    hand = js("verification")["hand_counts"]
    assert hand["approvals_2025_03"] == HAND_APPROVALS_2025_03
    assert hand["reports_2025_q1"] == HAND_REPORTS_2025_Q1


def test_delivered_hand_count_csv_identifies_the_source_and_period():
    approvals, reports = table("hand_counts")
    assert (approvals["sample"], approvals["period"], int(approvals["count"])) == (
        "completion_approvals",
        "2025-03",
        27,
    )
    assert (reports["sample"], reports["period"], int(reports["count"])) == (
        "completion_reports",
        "2025-Q1",
        18,
    )
    for row, archive, fields in [
        (
            approvals,
            cc.APM,
            ["SN_APM", "ACC_STATUS_DATE", "APM_OP_CD", "APM_SUBOP_CD", "APM_OP_DESC"],
        ),
        (reports, cc.EOR, ["SN_EOR", "BOREHOLE_STAT_DT", "EOR_OPERATION_CD"]),
    ]:
        assert archive in row["source_files"] and cc.BOREHOLE in row["source_files"]
        assert all(field in row["source_fields"] for field in [*fields, "REGION_CODE"])
        assert row["selection"]


def test_delivered_status_counts_reconcile_with_all_reports():
    rows = table("report_status_counts")
    counts = {r["report_status_code"]: int(r["reports"]) for r in rows}
    assert len(counts) == len(rows)
    assert counts == js("summary")["completion_reports_in_window_by_status"]
    assert counts["COM"] == 5173
    assert sum(counts.values()) == 5276
    assert {int(r["all_reports_in_window"]) for r in rows} == {sum(counts.values())}


def test_delivered_shares_follow_their_counts():
    for r in table("drilled_to_completed"):
        wells = int(r["wells_first_drilled"])
        done = int(r["with_initial_completion_approval"])
        assert done <= wells
        if wells:
            assert abs(float(r["share_percent"]) - 100 * done / wells) <= 0.05
    for r in table("fracturing_by_year"):
        assert int(r["with_fracturing_suboperation"]) <= int(r["bores_first_approved"])


def test_delivered_run_record():
    v = js("verification")
    assert v["conservation"]["ok"] is True
    assert all(v["conservation"]["checks"].values())
    run = v["run"]
    for key in ["code_commit", "command", "python", "timestamp_utc"]:
        assert run[key], key
    assert len(run["code_commit"]) == 40
    basis = json.loads((EXAMPLE / "series_basis.json").read_text(encoding="utf-8"))
    assert {f["name"]: f["sha256"] for f in v["basis"]["files"]} == {
        f["name"]: f["sha256"] for f in basis["files"]
    }


def test_delivered_suboperations_split_by_kind():
    rows = {r["suboperation"]: r for r in table("completion_approval_suboperations")}
    s = js("summary")
    for r in rows.values():
        initial = int(r["on_initial_completion"])
        other = int(r["on_other_completion_work"])
        assert initial + other == int(r["approvals"])
        assert other <= s["other_completion_work_approvals"]
    assert int(rows["INITCOMP"]["approvals"]) == s["initial_completion_approvals"]
    assert int(rows["INITCOMP"]["on_other_completion_work"]) == 0


def test_period_shares_are_ratios_of_wells():
    rows = table("appendix_04_drilled_to_completed")
    assert len(rows) == 40
    totals = {}
    for row in rows:
        wells = int(row["wells_first_drilled"])
        approved = int(row["with_initial_completion_approval"])
        assert 0 <= approved <= wells
        if wells:
            assert float(row["share_percent"]) == round(100 * approved / wells, 1)
        else:
            assert row["share_percent"] == ""
        key = row["group"], row["band"].lower().replace(",", "")
        prior_wells, prior_approved = totals.get(key, (0, 0))
        totals[key] = (prior_wells + wells, prior_approved + approved)

    # Add the annual partial-year cells to the earlier pooled cohort.
    additions = {
        (row["group"], row["band"].lower().replace(",", "")): (
            int(row["wells_first_drilled"]),
            int(row["with_initial_completion_approval"]),
        )
        for row in table("04_drilled_to_completed")
        if row["year"] == "2026"
    }
    group = {"exploration": "Exploratory wells", "development": "Development wells"}
    for row in table("drilled_to_completed"):
        if row["well_type"] in group and row["band"] in B[:4]:
            key = group[row["well_type"]], row["band"]
            wells, approved = additions[key]
            assert totals[key] == (
                int(row["wells_first_drilled"]) + wells,
                int(row["with_initial_completion_approval"]) + approved,
            )


# --------------------------------------------------------------------------
# Level C: the raw archives (skipped only when the folder is not named)
# --------------------------------------------------------------------------
DATA = os.environ.get("BSEE_SERIES_BASIS_DIR")
needs_data = pytest.mark.skipif(
    not DATA, reason="BSEE_SERIES_BASIS_DIR is not set; raw archives are not read"
)


@pytest.fixture(scope="module")
def recount(tmp_path_factory):
    out = tmp_path_factory.mktemp("completions")
    cc.run(Path(DATA), out)
    return out


@needs_data
def test_raw_recount_reproduces_the_delivered_tables(recount):
    # Comparator class: archived-run. This guards the delivered tables
    # against drift; correctness rests on the other tests of this level.
    for path in sorted(OUT.glob("*.csv")):
        assert (recount / path.name).read_bytes() == path.read_bytes(), path.name
    old, new = js("summary"), json.loads((recount / "summary.json").read_text())
    assert old == new


@needs_data
def test_raw_count_equals_c6_code_on_the_same_files(recount):
    # Comparator class: cross-solver. C6's classified_permits reads, removes
    # repeats, joins depth and classifies with pandas; this article reads and
    # counts with the standard library. Only the classification rule is shared.
    bore = ci.read_table(DATA, "BoreholeRawData.zip", "mv_boreholes_all")
    _, apm, _, _ = ci.classified_permits(DATA, bore)
    summary = json.loads((recount / "summary.json").read_text())
    years = range(summary["first_full_year"], summary["partial_year"] + 1)
    c6 = apm[apm.group.eq(ci.GROUPS[7]) & apm.year.isin(years)]
    theirs = c6.groupby(["year", "band"]).size().to_dict()
    with open(recount / "completion_approvals_by_year_band.csv", newline="") as f:
        mine = {}
        for r in csv.DictReader(f):
            key = (int(r["year"]), r["band"])
            mine[key] = mine.get(key, 0) + int(r["approvals"])
    assert {k: v for k, v in mine.items() if v} == {
        (int(y), b): int(n) for (y, b), n in theirs.items()
    }
    assert sum(mine.values()) == len(c6)

    march = ci.dates(c6.ACC_STATUS_DATE).dt.to_period("M").eq("2025-03")
    approvals, _ = table("hand_counts", recount)
    assert c6.loc[march, "SN_APM"].nunique() == int(approvals["count"]) == 27


@needs_data
def test_raw_report_status_and_quarter_counts(recount):
    bore = ci.read_table(DATA, cc.BOREHOLE, "mv_boreholes_all")
    reports = ci.read_table(DATA, cc.EOR, "mv_eor_mainquery")
    reports = ci.gulf_only(reports[reports.EOR_OPERATION_CD.eq("C")], bore)
    reports = reports[reports.region.eq("G")].drop_duplicates("SN_EOR")
    dates = ci.dates(reports.BOREHOLE_STAT_DT)
    _, sample = table("hand_counts", recount)
    assert dates.dt.to_period("Q").eq("2025Q1").sum() == int(sample["count"]) == 18

    window = reports[dates.dt.year.between(2005, 2026)]
    counts = {
        r["report_status_code"]: int(r["reports"])
        for r in table("report_status_counts", recount)
    }
    assert counts == window.BOREHOLE_STAT_CD.value_counts().to_dict()
    assert counts["COM"] == 5173


@needs_data
def test_raw_hand_counts(recount):
    v = json.loads((recount / "verification.json").read_text())
    assert v["hand_counts"]["approvals_2025_03"] == HAND_APPROVALS_2025_03
    assert v["hand_counts"]["reports_2025_q1"] == HAND_REPORTS_2025_Q1
