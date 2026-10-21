"""Regression checks for retained snapshot semantics and portable criteria."""

import csv
import hashlib
import json
import os
import runpy
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[4]
DIRECTORY = ROOT / "data/modules/pipeline/screening"


def test_committed_sample_preserves_unknown_counts_without_station():
    rows = list(csv.DictReader((DIRECTORY / "sample.csv").open()))
    missing = [row for row in rows if not row["station_id"]]
    assert missing
    for row in missing:
        for field in ("retained_observations", "complete_annual_maxima"):
            assert row[field] == "", (row["segment_id"], field)
            assert row[field + "_source"] == "UNKNOWN:no_station_within_limit"


def test_committed_usgs_terms_use_release_landing_page():
    manifest = json.loads((DIRECTORY / "manifest.json").read_text())
    sources = json.loads((DIRECTORY / "sources.json").read_text())
    for entries in (manifest["inputs"], sources):
        usgs = [
            entry for entry in entries if entry["source_id"] == "usgs-layer-register"
        ]
        assert usgs
        assert all(
            entry["terms_of_use"]["url"] == "https://pubs.usgs.gov/ds/2006/146/"
            for entry in usgs
        )


def test_main_ndbc_archive_parser_is_available():
    from worldenergydata.metocean.clients.ndbc_client import NDBCClient

    body = b"#YYYY MM DD hh mm WVHT DPD\n2022 01 01 00 00 1.5 6\n"
    digest = hashlib.sha256(body).hexdigest()
    rows = NDBCClient.parse_standard_archive("42001", body, digest)
    assert [row["value"] for row in rows] == [1.5, 6.0]
    assert [row["variable"] for row in rows] == ["wave_height_m", "wave_period_s"]
    assert all(row["raw_sha256"] == digest for row in rows)


def test_criteria_mismatch_names_path_and_reconciliation(tmp_path):
    build = runpy.run_path(str(ROOT / "scripts/bsee/build_pipeline_screening.py"))
    record = tmp_path / "criteria.json"
    saved = build["_criteria"](record)
    path = "packages/worldenergydata-metocean/src/worldenergydata/metocean/clients/ndbc_client.py"
    saved["code_sha256"][path] = "0" * 64
    record.write_text(json.dumps(saved))
    with pytest.raises(ValueError) as error:
        build["_criteria"](record)
    assert path in str(error.value)
    assert "reconcile" in str(error.value).lower()


def test_screening_digest_inputs_and_artifacts_keep_lf_on_checkout(tmp_path):
    """Exercise Git's checkout conversion, including all hashed shared modules."""
    manifest = json.loads((DIRECTORY / "manifest.json").read_text())
    paths = set(manifest["criteria"]["code_sha256"])
    paths.update(
        "data/modules/pipeline/screening/" + name
        for name in ("schema.yaml", "defaults.yaml", "revision.json", "manifest.json")
    )
    paths.update(
        "data/modules/pipeline/screening/" + entry["path"]
        for entry in manifest["artifacts"]
    )
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }

    def git(*args):
        subprocess.run(
            ["git", "-c", "core.autocrlf=true", *args],
            cwd=tmp_path,
            env=env,
            check=True,
            capture_output=True,
        )

    git("init")
    (tmp_path / ".gitattributes").write_bytes((ROOT / ".gitattributes").read_bytes())
    expected = {}
    for path in sorted(paths):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        expected[path] = (ROOT / path).read_bytes()
        target.write_bytes(expected[path])
    git("add", ".")
    for path in paths:
        (tmp_path / path).unlink()
    git("checkout-index", "--all")
    for path, content in expected.items():
        assert (tmp_path / path).read_bytes() == content, path
