"""Check the plotted permit populations and standing well exposure."""

import csv
import sys
from pathlib import Path

import pandas as pd
import pytest

EXAMPLE = Path(__file__).resolve().parents[3] / "examples/bsee/completions_by_depth"
sys.path.insert(0, str(EXAMPLE))
import count_completions as cc  # noqa: E402


def read_plot(out, name):
    with (out / f"{name}.csv").open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_permit_populations_and_pooled_exposure(tmp_path):
    shallow, middle = cc.BANDS[:2]
    approvals = [
        dict(year=2025, band=shallow, kind=cc.KINDS[0], sn="A"),
        dict(year=2025, band=shallow, kind=cc.KINDS[1], sn="B"),
        dict(year=2026, band=shallow, kind=cc.KINDS[1], sn="C"),
        dict(year=2004, band=shallow, kind=cc.KINDS[1], sn="D"),
    ]
    subcodes = {
        "A": {"INITCOMP", "PERF"},
        "B": {"PERF", "REPERF"},
        "C": {"REPERF"},
        "D": {"PERF"},
    }
    # The C6 classified Gulf permit table includes ordinary workovers in
    # the same group as recompletions. Its new hole group includes plugbacks.
    classified = pd.DataFrame(
        [
            ("COMP", 2026, middle, cc.ci.GROUPS[0]),
            ("WORKOVER", 2026, shallow, cc.ci.GROUPS[0]),
            ("COMP", 2026, shallow, cc.ci.GROUPS[6]),
            ("COMP", 2026, shallow, cc.SHARED_GROUP),
            ("COMP", 2004, middle, cc.ci.GROUPS[0]),
        ],
        columns=["APM_OP_CD", "year", "band", "group"],
    )
    years = range(2005, 2027)
    stock = pd.DataFrame(
        [
            dict(
                year=year,
                band=band,
                standing_wells=(
                    {2025: 2, 2026: 8}.get(year, 0) if band == shallow else 0
                ),
            )
            for year in years
            for band in cc.BANDS
        ]
    )
    cc.write_trend_tables(tmp_path, years, approvals, subcodes, classified, stock)
    by_kind = {}
    for row in read_plot(tmp_path, "01_approvals_by_period"):
        by_kind[row["group"]] = by_kind.get(row["group"], 0) + int(row["count"])
    assert by_kind == {"Initial completion": 1, "Other completion work": 2}

    work = read_plot(tmp_path, "02_recompletion_by_period")
    assert len(work) == 60
    assert [
        (r["group"], r["band"], int(r["count"]), float(r["value"]))
        for r in sorted(work, key=lambda r: r["group"])
        if int(r["count"])
    ] == [
        ("Modify Perforations", "Under 100 m", 1, 0.5),
        ("Recompletion", "100 to 500 m", 1, 0.5),
        ("Reperforation", "Under 100 m", 2, 1.0),
    ]
    rates = read_plot(tmp_path, "03_approvals_per_well")
    populated = next(r for r in rates if int(r["count"]))
    assert populated["period"] == "2025 to 2026 (partial)"
    assert (int(populated["count"]), int(populated["exposure"])) == (3, 10)
    assert float(populated["value"]) == pytest.approx(0.3)
    assert all(r["value"] == "" for r in rates if int(r["exposure"]) == 0)


def test_missing_depth_approval_cannot_disappear_from_the_four_bands(tmp_path):
    approvals = [dict(year=2025, band="no depth", kind=cc.KINDS[0], sn="A")]
    classified = pd.DataFrame(columns=["APM_OP_CD", "year", "band", "group"])
    stock = pd.DataFrame(columns=["year", "band", "standing_wells"])
    with pytest.raises(ValueError, match="depth"):
        cc.write_trend_tables(
            tmp_path, range(2005, 2027), approvals, {}, classified, stock
        )


def test_delivered_groups_and_denominators_match_the_archive_controls():
    out = EXAMPLE / "output"
    approvals = read_plot(out, "01_approvals_by_period")
    work = read_plot(out, "02_recompletion_by_period")
    rates = read_plot(out, "03_approvals_per_well")

    def totals(rows, key, field="count"):
        result = {}
        for row in rows:
            result[row[key]] = result.get(row[key], 0) + int(row[field])
        return result

    assert totals(approvals, "group") == {
        "Initial completion": 6841,
        "Other completion work": 1631,
    }
    assert totals(work, "group") == {
        "Recompletion": 9310,
        "Modify Perforations": 1020,
        "Reperforation": 381,
    }
    assert totals(rates, "band", "exposure") == {
        "Under 100 m": 205556,
        "100 to 500 m": 26408,
        "500 to 1,500 m": 13732,
        "1,500 m and deeper": 6977,
    }
    assert totals(approvals, "band") == totals(rates, "band")
