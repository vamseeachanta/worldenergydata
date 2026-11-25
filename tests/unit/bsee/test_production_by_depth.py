"""Independent readback of the published BSEE production tables and input pins."""

import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pytest

EXAMPLE = Path(__file__).resolve().parents[3] / "examples/bsee/production_by_depth"
OUTPUT = EXAMPLE / "output"
BANDS = {"<100 m", "100–<500 m", "500–<1,500 m", "≥1,500 m"}


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def select(rows, filters):
    return [row for row in rows if all(row[k] == str(v) for k, v in filters.items())]


def check_headlines(folder):
    numbers = json.loads((folder / "numbers.json").read_text(encoding="utf-8"))
    tables = {path.name: read_rows(path) for path in folder.glob("*.csv")}
    coverage = numbers["coverage_source"]
    assert coverage["operation"] == "max(month)"
    months = select(tables[coverage["table"]], coverage["filter"])
    last_month = max(row["month"] for row in months)
    assert numbers["coverage_through"] == last_month == "2026-09"
    headlines = numbers["headlines"]
    assert Counter(h["operation"] for h in headlines.values()) == {
        "row": 221,
        "mean": 15,
        "ratio": 6,
        "sum": 5,
    }

    for key, spec in headlines.items():
        table = tables[spec["table"]]
        rows = select(table, spec["filter"])
        operation = spec["operation"]
        if operation == "sum":
            # The full period has one annual observation per band per year.
            assert sorted(int(r["year"]) for r in rows) == list(range(2005, 2027)), key
        elif operation == "mean":
            year = spec["filter"]["year"]
            end = int(last_month[-2:]) if year == 2026 else 12
            assert sorted(r["month"] for r in rows) == [
                f"{year}-{m:02d}" for m in range(1, end + 1)
            ], key
        else:
            assert len(rows) == 1, key

        if operation == "ratio":
            denominator = select(table, spec["denominator_filter"])
            assert len(denominator) == 1, key

        fields = spec["fields"]
        assert set(fields) == set(spec["values"]), key
        for field in fields:
            # CSV numeric cells and JSON use the same decimal representation.
            values = [json.loads(r[field]) if r[field] else None for r in rows]
            if operation == "sum":
                value = sum(values)
            elif operation == "mean":
                value = sum(values) / len(values)
            elif operation == "ratio":
                value = values[0] / json.loads(denominator[0][field])
            else:
                value = values[0]
            assert value == spec["values"][field], f"{key} {field}"


def test_all_headlines_match_csvs():
    check_headlines(OUTPUT)


def test_changed_csv_cell_breaks_headline(tmp_path):
    shutil.copy(OUTPUT / "numbers.json", tmp_path)
    for path in OUTPUT.glob("*.csv"):
        shutil.copy(path, tmp_path)
    path = tmp_path / "annual_wells.csv"
    rows = read_rows(path)
    (row,) = select(rows, {"year": 2005, "band": "<100 m"})
    row["oil_bbl"] = str(int(row["oil_bbl"]) + 1)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(AssertionError, match=r"under100/year/2005 oil_bbl"):
        check_headlines(tmp_path)


@pytest.mark.parametrize(
    "table,keys,fields",
    [
        (
            "monthly_production",
            ("month",),
            ("monthly_producing_wells", "oil_bbl", "gas_mcf"),
        ),
        ("annual_wells", ("year",), ("producing_wells", "oil_bbl", "gas_mcf")),
        (
            "completion_lag",
            ("population",),
            ("wells", "pre_completion_wells", "same_month_wells"),
        ),
        ("decline", ("completion_type", "age_month"), ("baseline_wells", "wells")),
        (
            "interventions",
            ("measure", "age_year"),
            (
                "eligible_wells",
                "event_wells",
                "completion_observed_wells",
                "pre_origin_event_wells",
            ),
        ),
        (
            "article_summary",
            (),
            (
                "distinct_producing_wells",
                "producing_well_months",
                "cohort_completions",
                "ever_produced_wells",
                "produced_in_or_after_c_month_wells",
                "supported_starts",
                "war_by_cutoff_wells",
                "permit_by_cutoff_wells",
            ),
        ),
    ],
)
def test_depth_bands_conserve_additive_fields(table, keys, fields):
    groups = defaultdict(list)
    for row in read_rows(OUTPUT / f"{table}.csv"):
        groups[tuple(row[k] for k in keys)].append(row)
    assert groups
    for group, rows in groups.items():
        assert Counter(row["band"] for row in rows) == Counter(BANDS | {"All"}), group
        (pooled,) = select(rows, {"band": "All"})
        for field in fields:
            total = sum(int(r[field]) for r in rows if r["band"] != "All")
            assert int(pooled[field]) == total, (group, field)


def test_record_counts_conserve_rows_and_reported_volumes():
    stages = defaultdict(list)
    for row in read_rows(OUTPUT / "record_counts.csv"):
        stages[row["stage"]].append(row)
    assert len(stages) == 39
    for stage, rows in stages.items():
        by_reason = {(row["disposition"], row["reason"]) for row in rows}
        assert len(by_reason) == len(rows), stage
        (source,) = select(rows, {"disposition": "read"})
        (kept,) = select(rows, {"disposition": "kept"})
        dropped = select(rows, {"disposition": "dropped"})
        assert 2 + len(dropped) == len(rows), stage
        for field in ("rows", "oil_bbl", "gas_mcf"):
            if not source[field]:
                assert all(row[field] == "" for row in rows), (stage, field)
                continue
            accounted = sum(json.loads(row[field]) for row in [kept, *dropped])
            assert accounted == json.loads(source[field]), (stage, field)


def load_pins():
    return json.loads((EXAMPLE / "source_pins.json").read_text(encoding="utf-8"))[
        "sources"
    ]


def test_readme_matches_source_pins():
    pins = load_pins()
    names = [pin["name"] for pin in pins]
    assert len(names) == len(set(names))
    required = {
        "BoreholeRawData.zip",
        "eWellAPMRawData.zip",
        "eWellEORRawData.zip",
        "eWellWARRawData.zip",
        "LeaseOwnerRawData.zip",
        "ProductionRawData.zip",
        "lsetapefixed.zip",
        "ogoradelimit.zip",
        *(f"ogora{year}delimit.zip" for year in range(2005, 2026)),
    }
    assert set(names) == required
    expected = [(p["name"], p["url"], p["last_modified"], p["sha256"]) for p in pins]
    readme = (EXAMPLE / "README.md").read_text(encoding="utf-8")
    documented = re.findall(
        r"^\| \[([^\]]+\.zip)\]\((https://[^)]+)\) \| ([^|]+?) \| `([0-9a-f]{64})` \|",
        readme,
        re.MULTILINE,
    )
    assert sorted(documented) == sorted(expected)


def test_wrong_zip_fails_with_expected_and_actual_digests(tmp_path):
    pin = load_pins()[0]
    archive = tmp_path / pin["name"]
    content = b"synthetic archive with the wrong digest\n"
    archive.write_bytes(content)
    output = tmp_path / "output"
    output.mkdir()
    previous = output / "checks.txt"
    previous.write_bytes(b"previous build\n")
    result = subprocess.run(
        [
            sys.executable,
            str(EXAMPLE / "derive.py"),
            "--data-dir",
            str(tmp_path),
            "--output-dir",
            str(output),
        ],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.returncode != 0
    diagnostic = result.stdout + result.stderr
    for detail in (archive.name, pin["sha256"], hashlib.sha256(content).hexdigest()):
        assert detail in diagnostic, diagnostic
    assert list(output.iterdir()) == [previous]
    assert previous.read_bytes() == b"previous build\n"


@pytest.mark.skipif(
    not os.environ.get("BSEE_PROD_DATA_DIR"),
    reason="the pinned BSEE archives were not supplied",
)
def test_regeneration_is_byte_identical(tmp_path, monkeypatch):
    output = tmp_path / "output"
    data_dir = Path(os.environ["BSEE_PROD_DATA_DIR"]).resolve()
    monkeypatch.setenv("BSEE_PROD_DATA_DIR", str(data_dir))
    for variable in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        monkeypatch.delenv(variable, raising=False)
    subprocess.run(
        ["uv", "run", str(EXAMPLE / "derive.py"), "--output-dir", str(output)],
        check=True,
        cwd=tmp_path,
    )
    expected = {file.name for file in OUTPUT.iterdir()}
    assert {file.name for file in output.iterdir()} == expected
    for name in sorted(expected):
        assert (output / name).read_bytes() == (OUTPUT / name).read_bytes(), name
