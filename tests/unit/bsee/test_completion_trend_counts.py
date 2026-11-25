"""Check the plotted permit populations and standing well exposure."""

import csv
import json
import sys
import xml.etree.ElementTree as ET
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
    for row in read_plot(tmp_path, "appendix_01_approvals_by_period"):
        by_kind[row["group"]] = by_kind.get(row["group"], 0) + int(row["count"])
    assert by_kind == {"Initial completion": 1, "Other completion work": 2}

    work = read_plot(tmp_path, "appendix_02_recompletion_by_period")
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
    rates = read_plot(tmp_path, "appendix_03_approvals_per_well")
    populated = next(r for r in rates if int(r["completion_approvals"]))
    assert populated["period"] == "2025 to 2026 (partial)"
    assert int(populated["completion_approvals"]) == 3
    assert int(populated["january_well_years"]) == 10
    assert float(populated["approvals_per_january_well_year"]) == pytest.approx(0.3)
    assert all(
        r["approvals_per_january_well_year"] == ""
        for r in rates
        if int(r["january_well_years"]) == 0
    )


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
    approvals = read_plot(out, "appendix_01_approvals_by_period")
    work = read_plot(out, "appendix_02_recompletion_by_period")
    rates = read_plot(out, "appendix_03_approvals_per_well")

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
    assert totals(rates, "band", "january_well_years") == {
        "Under 100 m": 205556,
        "100 to 500 m": 26408,
        "500 to 1,500 m": 13732,
        "1,500 m and deeper": 6977,
    }
    assert totals(approvals, "band") == totals(rates, "band", "completion_approvals")


def test_work_shares_use_all_periods_and_only_the_same_approval_group():
    rows = read_plot(EXAMPLE / "output", "appendix_02_recompletion_by_period")
    for row in rows:
        group = [r for r in rows if r["group"] == row["group"]]
        total = sum(int(r["count"]) for r in group)
        band_count = sum(int(r["count"]) for r in group if r["band"] == row["band"])
        assert float(row["cell_share_of_group_percent"]) == round(
            100 * int(row["count"]) / total, 1
        )
        assert float(row["band_share_of_group_percent"]) == round(
            100 * band_count / total, 1
        )


def test_yearly_readings_quote_counts_and_moving_averages():
    out = EXAMPLE / "output"
    figures = json.loads((out / "figures.json").read_text())
    for f in figures:
        columns = {c["column"] for b in f["bullets"] for c in b["cells"]}
        assert {"value", "moving_average"} <= columns
    title = ET.parse(out / figures[2]["svg"]).findtext("{*}title").lower()
    assert "per january well year" in title


def test_annual_cells_recover_every_period_numerator_and_denominator():
    out = EXAMPLE / "output"
    for stem, columns in [
        ("01_approvals_by_period", ["count"]),
        ("02_recompletion_by_period", ["count"]),
        ("03_approvals_per_well", ["completion_approvals", "january_well_years"]),
        (
            "04_drilled_to_completed",
            ["wells_first_drilled", "with_initial_completion_approval"],
        ),
    ]:
        annual = read_plot(out, stem)
        for old in read_plot(out, "appendix_" + stem):
            first = int(old["period"][:4])
            rows = [
                r
                for r in annual
                if r["group"] == old["group"]
                and r["band"] == old["band"]
                and first <= int(r["year"]) < first + 5
            ]
            assert len(rows) == int(old.get("years", min(5, 2027 - first)))
            for col in columns:
                assert sum(int(r[col]) for r in rows) == int(old[col])
            for row in rows:
                if "wells_first_drilled" in columns:
                    numerator = 100 * int(row["with_initial_completion_approval"])
                    denominator = int(row["wells_first_drilled"])
                elif "january_well_years" in columns:
                    numerator = int(row["completion_approvals"])
                    denominator = int(row["january_well_years"])
                else:
                    numerator, denominator = int(row["count"]), 1
                if denominator:
                    assert float(row["value"]) == numerator / denominator
                else:
                    assert row["value"] == ""
