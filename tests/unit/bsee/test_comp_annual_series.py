"""Annual COMP figures are checked against distinct BSEE permit keys."""

import csv
import hashlib
import io
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile

import pytest

EXAMPLE = Path(__file__).resolve().parents[3] / "examples/bsee/completions_by_depth"
TOTAL = "All water depths"
# Independent count of SN_APM in the pinned ZIPs, rechecked by the raw test below.
MEASURED = {2006: (547, 110, 576), 2025: (309, 22, 145), 2026: (209, 20, 145)}


def cells():
    with (EXAMPLE / "output/yearly/annual_trends.csv").open(newline="") as stream:
        return {
            (r["metric"], r["band"], int(r["year"])): r for r in csv.DictReader(stream)
        }


@pytest.mark.parametrize("year,expected", MEASURED.items())
def test_measured_gulf_approval_years(year, expected):
    rows = cells()
    for metric, n in zip(("initial", "other"), expected[:2]):
        row = rows[metric, TOTAL, year]
        assert int(row["events"]) == float(row["value"]) == n
    assert (
        sum(
            int(r["events"])
            for (m, b, y), r in rows.items()
            if (m, y) == ("recompletion", year) and b != TOTAL
        )
        == expected[2]
    )


def test_calendar_window_blanks_zero_and_partial():
    all_rows = cells()
    blanks = 0
    zeros = 0
    for (metric, band, year), row in all_rows.items():
        partial = year == 2026
        assert int(row["partial"]) == partial
        values = [
            all_rows.get((metric, band, y), {}).get("value")
            for y in range(year - 4, year + 1)
        ]
        if row["value"] == "":
            assert row["availability"] == "unavailable"
            assert int(row["denominator"]) == 0
            blanks += 1
        elif float(row["value"]) == 0:
            zeros += 1
        if partial or not all(v not in (None, "") for v in values):
            assert row["moving_average"] == ""
        else:
            assert float(row["moving_average"]) == pytest.approx(
                sum(map(float, values)) / 5
            )
    assert blanks and zeros


def test_raw_gulf_permit_counts():
    path = os.environ.get("BSEE_SERIES_BASIS_DIR")
    if not path:
        pytest.skip("set BSEE_SERIES_BASIS_DIR to verify the original BSEE ZIPs")
    data_dir = Path(path)
    pins = json.loads((EXAMPLE / "series_basis.json").read_text())
    for f in pins["files"]:
        source = (data_dir / f["name"]).read_bytes()
        assert len(source) == f["bytes"]
        assert hashlib.sha256(source).hexdigest() == f["sha256"]

    def records(archive, name):
        with ZipFile(data_dir / archive) as z:
            (member,) = [p for p in z.namelist() if Path(p).name == name + ".txt"]
            with (
                z.open(member) as raw,
                io.TextIOWrapper(raw, "latin1", newline="") as stream,
            ):
                yield from csv.DictReader(stream)

    by_bore, by_well = defaultdict(set), defaultdict(set)
    for row in records("BoreholeRawData.zip", "mv_boreholes_all"):
        api, region = row["API_WELL_NUMBER"].strip(), row["REGION_CODE"].strip()
        by_bore[api].add(region)
        by_well[api[:10]].add(region)

    apm = "eWellAPMRawData.zip"
    selected = {}
    for row in records(apm, "mv_apm_main"):
        if row["APM_OP_CD"].strip() != "COMP":
            continue
        year = re.match(r"\d+/\d+/(\d{4})", row["ACC_STATUS_DATE"].strip())
        if not year or int(year[1]) not in MEASURED:
            continue
        api = row["API_WELL_NUMBER"].strip()
        region = next(
            (next(iter(v)) for v in (by_bore[api], by_well[api[:10]]) if len(v) == 1),
            "G" if row["SURF_LEASE_NUM"].strip().startswith("G") else "unknown",
        )
        if region == "G":
            key = row["SN_APM"].strip()
            assert selected.setdefault(key, int(year[1])) == int(year[1])

    codes = defaultdict(set)
    for row in records(apm, "mv_apm_suboperations"):
        key = row["SN_APM_FK"].strip()
        if key in selected:
            codes[key].add(row["APM_SUBOP_CD"].strip())

    # For these years no eligible Gulf COMP narrative even contains a literal
    # candidate for a current new hole, before considering negation or deferral.
    hole = re.compile(
        r"\bdrill(?:ing)?\s+(?:a\s+)?(?:new\s+)?(?:sidetrack|bypass)\b"
        r"|\bAPM for (?:Bypass|Sidetrack)\b|\binadvertently sidetrack\b"
        r"|\bAPM.*?in lieu of.*?\bto sidetrack\b",
        re.I | re.S,
    )
    for row in records(apm, "mv_apm_main_prop"):
        key = row["SN_APM"].strip()
        if key in selected and "PLUGBACK" not in codes[key]:
            assert not hole.search(row["APM_OP_DESC"] or "")

    counts = Counter()
    for key, year in selected.items():
        flags = codes[key]
        if "PLUGBACK" not in flags:
            metric = (
                "recompletion"
                if "ZONE" in flags
                else "initial" if "INITCOMP" in flags else "other"
            )
            counts[year, metric] += 1
    for year, expected in MEASURED.items():
        assert (
            tuple(counts[year, m] for m in ("initial", "other", "recompletion"))
            == expected
        )


def test_all_depth_shares_pool_distinct_wells_and_recompletion_totals():
    rows = cells()
    for year, expected in MEASURED.items():
        assert int(rows["recompletion", TOTAL, year]["events"]) == expected[2]
    for metric, numerator, denominator in (
        ("exploratory_share", 15, 34),
        ("development_share", 9, 9),
    ):
        r = rows[metric, TOTAL, 2025]
        assert (int(r["events"]), int(r["denominator"])) == (numerator, denominator)
        assert float(r["value"]) == pytest.approx(100 * numerator / denominator)


def test_all_band_observations_match_previous_annual_tables():
    rows = cells()
    old = {
        "01_approvals_by_period": {
            "Initial completion": "initial",
            "Other completion work": "other",
        },
        "02_recompletion_by_period": {
            "Recompletion": "recompletion",
            "Modify Perforations": "modify_perforations",
            "Reperforation": "reperforation",
        },
        "03_approvals_per_well": {"": "approvals_per_well"},
        "04_drilled_to_completed": {
            "Exploratory wells": "exploratory_share",
            "Development wells": "development_share",
        },
    }
    seen = set()
    for stem, metrics in old.items():
        with (EXAMPLE / "output" / f"{stem}.csv").open(newline="") as stream:
            for old_row in csv.DictReader(stream):
                key = (metrics[old_row["group"]], old_row["band"], int(old_row["year"]))
                assert key not in seen
                seen.add(key)
                for field in ("value", "moving_average"):
                    prior = old_row[field]
                    current = rows[key][field]
                    assert (float(current) if current else None) == (
                        float(prior) if prior else None
                    )
    assert seen == {key for key in rows if key[1] != TOTAL}
