"""Verify the published lease cohorts and rebuild from pinned inputs when present."""

import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

import pytest

EXAMPLE = Path(__file__).resolve().parents[3] / "examples/bsee/exploration_leasing"
OUTPUT = EXAMPLE / "output"
FIGURE_TABLES = (
    "current_status",
    "exploration",
    "exploration_site_depth",
    "first_production",
    "issuance",
)
EXPECTED_FILES = {
    *(
        f"{table}.{suffix}"
        for table in FIGURE_TABLES
        for suffix in ("csv", "svg", "png")
    ),
    "coverage.csv",
    "lease_match_bounds.csv",
    "record_counts.csv",
    "checks.txt",
    "numbers.json",
}
BOUND_BANDS = {
    "Under 100 m": "<100 m",
    "100 to 500 m": "100–<500 m",
    "500 to 1,500 m": "500–<1,500 m",
    "1,500 m and deeper": "≥1,500 m",
    "All": "All bands",
}
BANDS = set(BOUND_BANDS.values()) | {"Unknown"}
VARIANTS = (
    "original rule",
    "a any type bottom",
    "b any type surface",
    "c bottom or surface",
    "d type E bottom or surface",
    "e any spud date",
)


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def group_rows(rows, keys):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    assert groups
    return groups


def check_headlines(folder):
    headlines = json.loads((folder / "numbers.json").read_bytes(), parse_float=Decimal)
    assert headlines
    tables = {path.name: read_rows(path) for path in folder.glob("*.csv")}
    for name, spec in headlines.items():
        matches = [
            row
            for row in tables[spec["table"]]
            if all(row[key] == value for key, value in spec["filter"].items())
        ]
        assert len(matches) == 1, name
        cell = matches[0][spec["column"]]
        expected = spec["value"]
        if isinstance(expected, (int, Decimal)):
            assert Decimal(cell) == expected, name
        elif expected is None:
            assert cell == "", name
        else:
            assert cell == expected, name


def test_headlines_match_unique_csv_rows():
    check_headlines(OUTPUT)


def test_published_output_inventory_and_checks():
    assert {path.name for path in OUTPUT.iterdir()} == EXPECTED_FILES
    assert all((OUTPUT / name).is_file() for name in EXPECTED_FILES)
    lines = (OUTPUT / "checks.txt").read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(set(lines)) == 17
    assert all(line.startswith("PASS  ") for line in lines)


def test_changed_csv_cell_fails_headline_check(tmp_path):
    shutil.copy(OUTPUT / "numbers.json", tmp_path)
    for path in OUTPUT.glob("*.csv"):
        shutil.copy(path, tmp_path)
    target = tmp_path / "issuance.csv"
    rows = read_rows(target)
    (pooled,) = [
        row
        for row in rows
        if row["issue_year"] == "All years" and row["depth_band"] == "All bands"
    ]
    pooled["leases"] = str(int(pooled["leases"]) + 1)
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(AssertionError, match="issued_total"):
        check_headlines(tmp_path)


def check_margin(rows, column, categories, pooled_value, fields):
    assert Counter(row[column] for row in rows) == Counter(categories)
    (pooled,) = [row for row in rows if row[column] == pooled_value]
    for field in fields:
        assert int(pooled[field]) == sum(
            int(row[field]) for row in rows if row[column] != pooled_value
        ), (pooled, field)


@pytest.mark.parametrize(
    "table,keys,fields,last_year",
    [
        ("issuance", ["issue_year"], ["leases"], 2026),
        (
            "current_status",
            ["issue_year", "status_code"],
            ["leases", "cohort_leases"],
            2026,
        ),
        (
            "exploration",
            ["issue_year"],
            [
                "leases",
                "explored_leases",
                "exploration_wells",
                "leases_with_any_e_bore",
                "explored_within_five_years",
                "timed_leases",
            ],
            2020,
        ),
        ("exploration_site_depth", [], ["timed_leases"], None),
        (
            "first_production",
            ["event"],
            [
                "leases",
                "observed_leases",
                "without_observed_event",
                "timed_leases",
                "pre_effective_leases",
                "term_leases",
                "over_term_leases",
            ],
            None,
        ),
    ],
)
def test_additive_margins(table, keys, fields, last_year):
    rows = read_rows(OUTPUT / f"{table}.csv")
    for group in group_rows(rows, keys).values():
        check_margin(group, "depth_band", BANDS, "All bands", fields)
    if last_year:
        years = {str(year) for year in range(2005, last_year + 1)} | {"All years"}
        year_keys = ["depth_band", *(key for key in keys if key != "issue_year")]
        for group in group_rows(rows, year_keys).values():
            check_margin(group, "issue_year", years, "All years", fields)


def test_record_counts_reconcile_with_drop_reasons():
    rows = read_rows(OUTPUT / "record_counts.csv")
    assert rows and len({row["stage"] for row in rows}) == len(rows)
    for row in rows:
        reasons = [
            int(value) for name, value in row.items() if name.startswith("drop__")
        ]
        assert reasons and min(reasons) >= 0, row
        assert int(row["rows_dropped"]) == sum(reasons), row
        assert int(row["rows_read"]) == int(row["rows_kept"]) + sum(reasons), row


def test_status_shares_use_issue_year_and_depth_band_cohort():
    keys = ("issue_year", "depth_band")
    status = group_rows(read_rows(OUTPUT / "current_status.csv"), keys)
    issuance = group_rows(read_rows(OUTPUT / "issuance.csv"), keys)
    assert status.keys() == issuance.keys()
    codes = {row["status_code"] for rows in status.values() for row in rows}
    for cohort, rows in status.items():
        (issued,) = issuance[cohort]
        leases = int(issued["leases"])
        assert Counter(row["status_code"] for row in rows) == Counter(codes), cohort
        assert sum(int(row["leases"]) for row in rows) == leases, cohort
        for row in rows:
            assert int(row["cohort_leases"]) == leases, row
            if leases:
                expected = 100 * int(row["leases"]) / leases
                assert float(row["share_pct"]) == pytest.approx(
                    expected, abs=1e-12
                ), row
            else:
                assert row["share_pct"] == "", row
        if leases:
            assert sum(float(r["share_pct"]) for r in rows) == pytest.approx(
                100, abs=1e-12
            )


def test_lease_match_bounds_reconcile_with_exploration():
    rows = read_rows(OUTPUT / "lease_match_bounds.csv")
    exploration = group_rows(
        read_rows(OUTPUT / "exploration.csv"), ("issue_year", "depth_band")
    )
    cohorts = {"2005 to 2020": "All years", "2005": "2005"}
    groups = group_rows(rows, ("cohort", "band"))
    assert set(groups) == {(year, band) for year in cohorts for band in BOUND_BANDS}
    for (year, band), group in groups.items():
        (source,) = exploration[cohorts[year], BOUND_BANDS[band]]
        leases = int(source["leases"])
        assert Counter(r["variant"] for r in group) == Counter(VARIANTS)
        by_variant = {r["variant"]: int(r["matched_leases"]) for r in group}
        original, bottom, surface, either, exploratory, any_date = (
            by_variant[v] for v in VARIANTS
        )
        assert original == int(source["explored_leases"])
        any_e_bottom = int(source["leases_with_any_e_bore"])
        assert (
            0 <= original <= any_e_bottom <= exploratory <= either <= any_date <= leases
        )
        assert any_e_bottom <= bottom <= either
        assert 0 <= surface <= either <= bottom + surface
        for row in group:
            assert int(row["leases"]) == leases, row
            assert (
                row["share_pct"] == f"{100 * int(row['matched_leases']) / leases:.2f}"
            ), row
        if year == "2005 to 2020" and band == "All":
            assert (leases, original, exploratory, either, any_date) == (
                7126,
                432,
                477,
                546,
                587,
            )
    for group in group_rows(rows, ("cohort", "variant")).values():
        check_margin(
            group, "band", set(BOUND_BANDS), "All", ("leases", "matched_leases")
        )


def read_pins():
    return json.loads((EXAMPLE / "source_pins.json").read_bytes())["sources"]


def test_readme_matches_archive_pins():
    pins = read_pins()
    names = {
        "BoreholeRawData.zip",
        "lsetapefixed.zip",
        "ProductionRawData.zip",
        "LeaseOwnerRawData.zip",
    }
    assert Counter(p["name"] for p in pins) == Counter(names)
    expected = [(p["name"], p["url"], p["last_modified"], p["sha256"]) for p in pins]
    readme = (EXAMPLE / "README.md").read_text(encoding="utf-8")
    documented = re.findall(
        r"^\| \[([^\]]+\.zip)\]\((https://www\.data\.bsee\.gov/[^)]+)\) "
        r"\| ([^|]+?) \| `([0-9a-f]{64})` \|$",
        readme,
        re.MULTILINE,
    )
    assert sorted(documented) == sorted(expected)


def test_wrong_archive_reports_both_digests(tmp_path):
    pins = read_pins()
    content = b"synthetic file with incorrect digest\n"
    for pin in pins:
        (tmp_path / pin["name"]).write_bytes(content)
    output = tmp_path / "output"
    output.mkdir()
    previous = output / "checks.txt"
    previous.write_bytes(b"previous build\n")
    run = subprocess.run(
        [
            sys.executable,
            "-S",
            str(EXAMPLE / "derive.py"),
            "--data-dir",
            str(tmp_path),
            "--output-dir",
            str(output),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert run.returncode != 0
    message = run.stdout + run.stderr
    assert hashlib.sha256(content).hexdigest() in message, message
    assert any(p["name"] in message and p["sha256"] in message for p in pins), message
    assert list(output.iterdir()) == [previous]
    assert previous.read_bytes() == b"previous build\n"


@pytest.mark.skipif(
    not os.environ.get("BSEE_EXP_DATA_DIR"), reason="pinned archives were not supplied"
)
def test_regeneration_is_byte_identical(tmp_path, monkeypatch):
    archives = Path(os.environ["BSEE_EXP_DATA_DIR"]).resolve()
    monkeypatch.setenv("BSEE_EXP_DATA_DIR", str(archives))
    # Retain the UTF-8 table labels even when the process locale is ASCII.
    monkeypatch.setenv("LC_ALL", "C")
    monkeypatch.setenv("PYTHONUTF8", "0")
    monkeypatch.setenv("PYTHONCOERCECLOCALE", "0")
    for variable in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        monkeypatch.delenv(variable, raising=False)
    output = tmp_path / "output"
    subprocess.run(
        [
            "uv",
            "run",
            "--no-project",
            str(EXAMPLE / "derive.py"),
            "--output-dir",
            str(output),
        ],
        cwd=tmp_path,
        check=True,
    )
    assert {path.name for path in output.iterdir()} == EXPECTED_FILES
    for name in sorted(EXPECTED_FILES):
        assert (output / name).read_bytes() == (OUTPUT / name).read_bytes(), name
