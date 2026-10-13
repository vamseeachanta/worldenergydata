"""Offline end-to-end source digest and generated snapshot checks."""

import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def run_cli(raw, output, registry=None):
    env = dict(os.environ)
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        env.pop(key, None)
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/bsee/fetch_borehole_status.py"),
            "--raw-dir",
            str(raw),
            "--output-dir",
            str(output),
            "--registry",
            str(registry or ROOT / "tests/fixtures/bsee/borehole_status/registry.yml"),
            "--reuse-manifest",
        ],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def prepare_source(raw):
    raw.mkdir()
    path = raw / "5010delimit.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "5010.txt",
            (ROOT / "tests/fixtures/bsee/borehole_status/5010_sample.txt").read_bytes(),
        )
    manifest = json.loads(
        (ROOT / "tests/fixtures/bsee/borehole_status/source_manifest.json").read_text()
    )
    for record in manifest["files"]:
        source = raw / record["file"]
        if record["file"] != "5010delimit.zip":
            source.write_bytes(b"offline mock documentation")
        record["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
        record["size_bytes"] = source.stat().st_size
    (raw / "source_manifest.json").write_text(json.dumps(manifest))
    return path


def test_offline_cli_snapshot_and_digest_rejection(tmp_path):
    raw, output = tmp_path / "raw", tmp_path / "curated"
    source = prepare_source(raw)
    result = run_cli(raw, output)
    assert result.returncode == 0, result.stderr
    summary = json.loads((output / "summary.json").read_text())
    assert summary["joined_boreholes"] == 4
    assert summary["source_boreholes"] == 5
    assert summary["source_retrieved_at_utc"]
    manifest = json.loads((output / "extract_manifest.json").read_text())
    assert (
        manifest["registry_sha256"]
        == hashlib.sha256(
            (ROOT / "tests/fixtures/bsee/borehole_status/registry.yml").read_bytes()
        ).hexdigest()
    )
    for record in manifest["outputs"]:
        path = (
            raw if record["storage"] == "external_raw_directory" else output
        ) / record["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
    source.write_bytes(b"tampered")
    failed = run_cli(raw, tmp_path / "rejected")
    assert failed.returncode != 0
    assert "digest" in failed.stderr.lower()
    assert not (tmp_path / "rejected").exists()


def test_verified_reuse_preserves_retained_unmatched(tmp_path):
    raw = tmp_path / "raw"
    prepare_source(raw)
    first = run_cli(raw, tmp_path / "first")
    assert first.returncode == 0, first.stderr
    retained = (raw / "unmatched.csv").read_bytes()
    second = run_cli(raw, tmp_path / "second")
    assert second.returncode == 0, second.stderr
    assert (raw / "unmatched.csv").read_bytes() == retained


def test_successful_download_provenance_survives_later_timeout(tmp_path, monkeypatch):
    import runpy

    functions = runpy.run_path(str(ROOT / "scripts/bsee/fetch_borehole_status.py"))
    obtain = functions["obtain_source"]
    calls = []

    def fetch(url, destination):
        calls.append(url)
        if len(calls) == 2:
            raise TimeoutError("source timed out")
        destination.write_bytes(b"retained")
        return {"file": destination.name, "source_url": url}

    monkeypatch.setitem(obtain.__globals__, "fetch_file", fetch)
    import pytest

    with pytest.raises(TimeoutError):
        obtain(tmp_path / "raw", False, sleep=lambda _: None)
    manifest = json.loads((tmp_path / "raw/source_manifest.json").read_text())
    assert len(manifest["files"]) == 1
    assert manifest["failure"]["type"] == "TimeoutError"


def test_incomplete_or_failed_provenance_cannot_be_reused(tmp_path):
    raw = tmp_path / "raw"
    prepare_source(raw)
    path = raw / "source_manifest.json"
    manifest = json.loads(path.read_text())
    manifest["failure"] = {"type": "HTTPError"}
    path.write_text(json.dumps(manifest))
    failed = run_cli(raw, tmp_path / "failed")
    assert failed.returncode != 0
    assert "incomplete" in failed.stderr.lower()
    del manifest["failure"]
    manifest["files"] = manifest["files"][:1]
    path.write_text(json.dumps(manifest))
    missing = run_cli(raw, tmp_path / "missing")
    assert missing.returncode != 0
    assert "incomplete" in missing.stderr.lower()
    assert not (tmp_path / "failed").exists()
    assert not (tmp_path / "missing").exists()


def test_registry_manifest_paths_and_small_unmatched_summary(tmp_path):
    raw = tmp_path / "raw"
    prepare_source(raw)
    inside = ROOT / "tests/fixtures/bsee/borehole_status/registry.yml"
    outside = tmp_path / "custom.yml"
    outside.write_bytes(inside.read_bytes())
    for registry, expected in [
        (inside, "tests/fixtures/bsee/borehole_status/registry.yml"),
        (outside, "custom.yml"),
    ]:
        output = tmp_path / registry.stem
        result = run_cli(raw, output, registry)
        assert result.returncode == 0, result.stderr
        manifest = json.loads((output / "extract_manifest.json").read_text())
        assert manifest["registry"] == expected
        summary = json.loads((output / "unmatched_summary.json").read_text())
        assert summary["borehole_counts"] == {"lease_not_in_registry": 1}
        assert summary["distinct_lease_counts"] == {"lease_not_in_registry": 1}
        assert summary["sample"][0]["bottom_lease"] == "S00538"
        assert (raw / "unmatched_by_lease.json").exists()
        assert not (output / "unmatched_by_lease.json").exists()
        assert not (output / "snapshot.html").exists()
        assert not (output / "data_dictionary.html").exists()


def test_fetch_pauses_only_between_requests(tmp_path, monkeypatch):
    import runpy

    functions = runpy.run_path(str(ROOT / "scripts/bsee/fetch_borehole_status.py"))
    obtain = functions["obtain_source"]
    events = []

    def fetch(url, destination):
        events.append(destination.name)
        return {"file": destination.name}

    monkeypatch.setitem(obtain.__globals__, "fetch_file", fetch)
    monkeypatch.setitem(obtain.__globals__, "verify_provenance", lambda *_: None)
    obtain(tmp_path / "raw", False, request_delay=0.25, sleep=events.append)
    assert events == [
        "5010delimit.zip",
        0.25,
        "borehole_layout.html",
        0.25,
        "borehole_codes.html",
        0.25,
        "disclaimer.html",
    ]


def test_unmatched_sample_order_and_reason_counts():
    import runpy

    functions = runpy.run_path(str(ROOT / "scripts/bsee/fetch_borehole_status.py"))
    groups = [
        {"reason": "unknown", "bottom_lease": f"G{i:05}", "borehole_count": 2}
        for i in range(25)
    ]
    summary = functions["unmatched_summary"](groups)
    assert summary["borehole_counts"] == {"unknown": 50}
    assert summary["distinct_lease_counts"] == {"unknown": 25}
    assert [r["bottom_lease"] for r in summary["sample"]] == [
        f"G{i:05}" for i in range(20)
    ]
