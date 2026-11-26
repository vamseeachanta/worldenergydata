"""Checks for the EXP annual effective-year series."""

import csv
import hashlib
import os
import re
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

EXAMPLE = Path(__file__).resolve().parents[3] / "examples/bsee/exploration_leasing"
TOTAL = "All water depths"


def saved_rows():
    with (EXAMPLE / "output/yearly/annual_trends.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        return list(csv.DictReader(stream))


@pytest.mark.parametrize(
    "year,expected", [(2005, 603), (2010, 449), (2025, 0), (2026, 215)]
)
def test_published_annual_counts_against_disjoint_lsetape_status_counts(year, expected):
    # Closed-form count: sum mutually exclusive statuses for the named effective
    # year, independently of the issuance table and yearly-series calculation.
    with (EXAMPLE / "output/current_status.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        counts = [
            int(r["leases"])
            for r in csv.DictReader(stream)
            if r["issue_year"] == str(year) and r["depth_band"] == "All bands"
        ]
    assert len(counts) == 9
    assert sum(counts) == expected
    (row,) = [
        r
        for r in saved_rows()
        if r["metric"] == "effective_leases"
        and r["band"] == TOTAL
        and r["year"] == str(year)
    ]
    assert float(row["value"]) == expected


def test_source_tape_count_by_fixed_width_fields():
    if not os.environ.get("BSEE_EXP_DATA_DIR"):
        pytest.skip("set BSEE_EXP_DATA_DIR for independent raw-tape count")
    tape = Path(os.environ["BSEE_EXP_DATA_DIR"]) / "lsetapefixed.zip"
    assert hashlib.sha256(tape.read_bytes()).hexdigest() == (
        "46e11a22d1314fe838f31093358f2dbf435d3c5460635d224b4718db77a91c08"
    )
    ids = defaultdict(set)
    # BSEE LSETAPE positions 1..7, 51..58, 161..163. Direct byte slices
    # avoid reusing the pandas study parser, joins, or annual aggregator.
    with ZipFile(tape) as archive, archive.open("LSETAPE.DAT") as stream:
        for row in stream:
            lease, year, area = row[:7].strip(), row[50:54], row[160:163]
            if area in {b"CGM", b"EGM", b"WGM"} and re.fullmatch(rb"G?\d{5,6}", lease):
                ids[year].add(lease)
    plotted = {
        r["year"]: float(r["value"])
        for r in saved_rows()
        if r["metric"] == "effective_leases" and r["band"] == TOTAL
    }
    for year in ("2005", "2010", "2025", "2026"):
        assert plotted[year] == len(ids[year.encode()])


def test_five_complete_calendar_values_and_partial_year():
    rows = {
        int(r["year"]): r
        for r in saved_rows()
        if r["metric"] == "effective_leases" and r["band"] == TOTAL
    }
    assert all(rows[y]["moving_average"] == "" for y in range(2005, 2009))
    for y in range(2009, 2026):
        assert float(rows[y]["moving_average"]) == pytest.approx(
            sum(float(rows[i]["value"]) for i in range(y - 4, y + 1)) / 5
        )
    assert float(rows[2025]["value"]) == 0
    assert rows[2026]["partial"] == "1" and rows[2026]["moving_average"] == ""


def test_qualifying_windows_and_pooled_medians(monkeypatch):
    monkeypatch.syspath_prepend(str(EXAMPLE))
    from lease_yearly import annual_series

    frame = pd.DataFrame(
        {
            "lease_id": list("ABCDE"),
            "issue_year": [2005] * 4 + [2026],
            "depth_band": ["Under 100 m"] * 3 + ["100 to 500 m"] * 2,
            "status_code": ["PROD", "EXPIR", "RELINQ", "PROD", "PRIMRY"],
            "effective_date": pd.to_datetime(["2005-01-01"] * 4 + ["2026-01-01"]),
            "exploration_spud": pd.to_datetime(
                ["2005-01-01", "2010-01-01", "2010-01-02", None, None]
            ),
            "first_oil_month": pd.to_datetime(
                ["2005-01-01", "2009-12-01", "2010-01-01", "2004-12-01", None]
            ),
        }
    )
    annual = annual_series(frame, frame.loc[frame.issue_year.eq(2005)])
    rows = annual.set_index(["metric", "band", "year"]).to_dict("index")

    def total(metric):
        return float(rows[metric, TOTAL, 2005]["value"])

    assert total("spud_share_observed") == 75
    assert total("spud_share_5y") == 50
    assert total("spud_years_5y") == pytest.approx(913 / 365.25)
    assert total("crude_share_5y") == 50
    assert total("crude_years_5y") == pytest.approx(29.5 / 12)
    assert pd.isna(rows["crude_years_5y", "100 to 500 m", 2005]["value"])
    assert pd.isna(rows["spud_share_observed", TOTAL, 2006]["value"])
    assert pd.isna(rows["spud_share_observed", TOTAL, 2009]["moving_average"])
    assert ("crude_share_5y", TOTAL, 2026) not in rows


def test_retained_tables_leave_unresolved_values_unavailable(monkeypatch):
    monkeypatch.syspath_prepend(str(EXAMPLE))
    from retained_yearly import retained_series

    annual = retained_series(EXAMPLE / "output").set_index(["metric", "band", "year"])
    missing = annual.loc[("spud_years_5y", TOTAL, 2005)]
    assert missing.availability == "unavailable" and pd.isna(missing.value)
    assert missing.events == 61
    unavailable_crude = annual.loc[("crude_share_5y", TOTAL, 2005)]
    assert unavailable_crude.availability == "unavailable" and pd.isna(
        unavailable_crude.events
    )
    assert pd.isna(annual.loc[("crude_share_5y", TOTAL, 2020), "moving_average"])
    assert annual.loc[("crude_years_5y", TOTAL, 2020), "value"] == pytest.approx(
        58 / 12
    )
    zero = annual.loc[("crude_share_5y", "1,500 m and deeper", 2005)]
    assert zero.events == zero.value == 0 and zero.availability == "verified"


@pytest.mark.parametrize(
    "days,k",
    [
        ([100, 500, 800, 1600, 1900, 2200, 2650], 4),
        ([100, 500, 800, 1600, 2200], 4),
        ([645, 2019, 3300], 1),
    ],
)
def test_exact_recovery_from_quartile_order_statistics(days, k, monkeypatch):
    monkeypatch.syspath_prepend(str(EXAMPLE))
    from retained_yearly import restricted_median_days

    sample = pd.Series(days)
    p25, median = sample.quantile([0.25, 0.5])
    assert restricted_median_days(len(days), k, p25, median) == sample.iloc[:k].median()


def test_retained_build_preserves_existing_output(monkeypatch):
    monkeypatch.syspath_prepend(str(EXAMPLE))
    from retained_yearly import build_retained

    with pytest.raises(FileExistsError, match="fresh"):
        build_retained(EXAMPLE / "output")
