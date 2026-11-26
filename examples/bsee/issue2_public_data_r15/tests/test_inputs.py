"""Offline input integrity and end-to-end producer checks."""

import csv
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
PIN_FILES = ["APDRawData.zip", "BoreholeRawData.zip", "eWellAPMRawData.zip", "wti-monthly.csv"]
sys.path.insert(0, str(ROOT.parent))
from issue2_public_data_r15.tests.input_fixtures import write_synthetic_archives


def test_source_receipts_match_all_four_pins():
    pins = json.loads((ROOT / "source-pins.json").read_text(encoding="utf-8"))
    with (ROOT / "data" / "sources.csv").open(encoding="utf-8", newline="") as stream:
        receipts = list(csv.DictReader(stream))
    assert sorted(row["file"] for row in pins) == sorted(PIN_FILES)
    assert sorted(receipts, key=lambda row: row["file"]) == sorted(pins, key=lambda row: row["file"])


def test_repository_wti_matches_committed_pin():
    pins = json.loads((ROOT / "source-pins.json").read_text(encoding="utf-8"))
    wti = ROOT.parents[2] / "data" / "wti-monthly.csv"
    expected = next(receipt["sha256"] for receipt in pins if receipt["file"] == wti.name)
    assert hashlib.sha256(wti.read_bytes()).hexdigest() == expected


@pytest.fixture
def cli_inputs(tmp_path):
    # Run the real script with its normal relative pin, WTI, baseline and output paths.
    bsee = tmp_path / "examples" / "bsee"
    for package in ("rawdata_fact_check", "issue2_public_data_r9", "issue2_public_data_r12", ROOT.name):
        dest = bsee / package
        dest.mkdir(parents=True)
        for path in (ROOT.parent / package).glob("*.py"):
            shutil.copyfile(path, dest / path.name)
    baseline = ROOT.parent / "issue2_public_data_r12"
    shutil.copytree(baseline / "data", bsee / baseline.name / "data")
    shutil.copyfile(baseline / "counting-rules.md", bsee / baseline.name / "counting-rules.md")

    archives = tmp_path / "archives"
    archives.mkdir()
    write_synthetic_archives(archives)
    (tmp_path / "data").mkdir()
    paths = {name: archives / name for name in PIN_FILES}
    paths["wti-monthly.csv"] = paths["wti-monthly.csv"].rename(tmp_path / "data" / "wti-monthly.csv")
    pins = [{"file": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for name, path in paths.items()]
    article = bsee / ROOT.name
    (article / "source-pins.json").write_text(json.dumps(pins), encoding="utf-8")
    return article, archives, paths


def run_cli(article, archives):
    return subprocess.run(
        [sys.executable, "-B", str(article / "derive_r15.py"), "--data-dir", str(archives)],
        cwd=article, capture_output=True, text=True, timeout=60,
    )


@pytest.mark.parametrize("name", PIN_FILES)
def test_cli_rejects_each_wrong_digest(cli_inputs, name):
    article, archives, paths = cli_inputs
    expected = hashlib.sha256(paths[name].read_bytes()).hexdigest()
    paths[name].write_bytes(b"wrong revision")
    actual = hashlib.sha256(b"wrong revision").hexdigest()
    output = article / "data"
    output.mkdir()
    (output / "table1.csv").write_bytes(b"prior output")

    result = run_cli(article, archives)

    assert result.returncode != 0
    assert f"{name}: expected SHA-256 {expected}, actual {actual}" in result.stderr
    assert {p.name: p.read_bytes() for p in output.iterdir()} == {"table1.csv": b"prior output"}


def test_cli_names_missing_input(cli_inputs):
    article, archives, paths = cli_inputs
    paths["eWellAPMRawData.zip"].unlink()
    result = run_cli(article, archives)
    assert result.returncode != 0
    assert "eWellAPMRawData.zip" in result.stderr
    assert not (article / "data").exists()


@pytest.mark.parametrize("use_links", [False, True], ids=["files", "symlinks"])
def test_synthetic_cli_partitions_all_three_archives(cli_inputs, use_links):
    article, archives, _ = cli_inputs
    if use_links:
        for path in sorted(archives.glob("*.zip")):
            target = path.rename(archives.parent / path.name)
            try:
                path.symlink_to(target)
            except OSError as exc:
                if getattr(exc, "winerror", None) == 1314:
                    pytest.skip("Windows account lacks symlink creation privilege")
                raise

    result = run_cli(article, archives)

    assert result.returncode == 0, result.stderr
    audit = pd.read_csv(article / "data" / "record-counts.csv")
    totals = audit.groupby(["source", "disposition"]).records.sum()
    assert totals.unstack()[["read", "kept", "excluded"]].to_dict("index") == {
        "APD": {"read": 2, "kept": 1, "excluded": 1},
        "Borehole": {"read": 3, "kept": 2, "excluded": 1},
        "APM": {"read": 2, "kept": 1, "excluded": 1},
    }
    excluded = audit[(audit.disposition == "excluded") & (audit.records != 0)]
    assert excluded.set_index(["source", "reason"]).records.to_dict() == {
        ("APD", "later_or_duplicate_permit"): 1,
        ("Borehole", "non_gulf"): 1,
        ("APM", "non_gulf"): 1,
    }
