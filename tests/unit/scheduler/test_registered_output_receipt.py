"""Registered BSEE readback contracts; all dataset writes here are synthetic."""

import importlib.util
import json
import signal
import socket
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts/validation/verify_scheduler_output_run.py"


@pytest.fixture
def verifier(monkeypatch):
    spec = importlib.util.spec_from_file_location("output_receipt", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    from worldenergydata.scheduler.jobs.bsee_refresh import BseeRefreshJob

    def synthetic_write(self, scraper, name, info, output_dir):
        # Two literal observations per catalog entry: five times two = ten.
        pd.DataFrame({"synthetic": ["first", "second"]}).to_parquet(
            output_dir / info["output_file"], index=False
        )
        return 2

    def forbid_network(*args, **kwargs):
        raise AssertionError("Offline receipt tests cannot open connections")

    monkeypatch.setattr(BseeRefreshJob, "_process_dataset", synthetic_write)
    monkeypatch.setattr(socket.socket, "connect", forbid_network)
    return module


def output_root(root):
    return root / "data/modules/bsee"


def snapshot(root):
    return next((output_root(root) / "runs").iterdir())


def test_registered_relocation_and_report_readback(verifier, tmp_path, monkeypatch):
    monkeypatch.setenv("WORLDENERGYDATA_DATA_DIR", str(tmp_path / "unused"))
    monkeypatch.setenv("WED_DATA_ROOT", str(tmp_path / "legacy"))
    original_cwd = Path.cwd()
    root = tmp_path / "execution"
    receipt = verifier.execute_run(REPO, root)
    assert receipt["verification"] == "VERIFIED"
    assert receipt["result"]["records_updated"] == 10
    assert receipt["routing"] == {
        "branch": "data-prefixed relative-path relocation",
        "configured": "data/modules/bsee",
        "override": "WORLDENERGYDATA_DATA_DIR",
        "expected": "RUN_ROOT/data/modules/bsee",
        "actual": "RUN_ROOT/data/modules/bsee",
        "working_directory": "RUN_ROOT/cwd",
    }
    catalog = yaml.safe_load((REPO / "config/bsee.yml").read_text())
    assert set(receipt["datasets"]) == set(catalog["scheduler_datasets"])
    assert all(item["rows"] == 2 for item in receipt["datasets"].values())
    assert len(receipt["payload_sha256"]) == 6  # Five Parquets and metadata.
    assert "_metadata.json" in receipt["payload_sha256"]
    assert receipt["manifests_match"] is True
    runtime = yaml.safe_load((root / "scheduler.yml").read_text())
    assert len(runtime["jobs"]) == 1
    assert runtime["jobs"][0]["output_dir"] == "data/modules/bsee"
    assert runtime["jobs"][0]["catalog_path"] == str(REPO / "config/bsee.yml")
    assert runtime["monitoring"]["retry_max"] == 1
    assert runtime["monitoring"]["retry_backoff_seconds"] == 0
    assert set(runtime["monitoring"]) == {
        "retry_max",
        "retry_backoff_seconds",
        "log_dir",
        "status_file",
    }
    assert Path.cwd() == original_cwd
    assert not (tmp_path / "legacy").exists()
    assert not (tmp_path / "unused").exists()
    reports = tmp_path / "reports"
    verifier.save_reports(receipt, reports)
    saved = json.loads((reports / "issue-271-output-readback.json").read_text())
    assert saved == receipt
    html = (reports / "issue-271-output-readback.html").read_text()
    assert "Revision history" in html
    assert "VERIFIED" in html
    assert str(root) not in html
    assert str(REPO) not in json.dumps(receipt)
    assert json.loads((root / "receipt.json").read_text()) == receipt


def tamper_manifest(path, defect):
    data = json.loads(path.read_text())
    key, value = {
        "wrong_job": ("job_name", "other_refresh"),
        "wrong_rows": ("records_updated", 11),
        "wrong_time": ("start_time", "1971-01-01T00:00:00+00:00"),
        "manifest_error": ("error_msg", "synthetic partial"),
        "wrong_status": ("status", "failure"),
    }[defect]
    data[key] = value
    path.write_text(json.dumps(data))


@pytest.mark.parametrize(
    "defect",
    [
        "missing_live",
        "missing_snapshot",
        "changed_live",
        "changed_snapshot",
        "missing_live_manifest",
        "missing_snapshot_manifest",
        "wrong_job",
        "wrong_rows",
        "wrong_time",
        "manifest_error",
        "wrong_status",
        "row_sum",
        "empty_parquet",
        "extra_snapshot",
        "nested_history",
        "external_symlink",
        "metadata_mismatch",
        "runtime_configuration",
    ],
)
def test_incomplete_readback_never_verifies(verifier, tmp_path, monkeypatch, defect):
    root = tmp_path / "execution"
    real_run = verifier.cmd_run_job

    def run_and_tamper(*args, **kwargs):
        result = real_run(*args, **kwargs)
        live, retained = output_root(root), snapshot(root)
        payload = next(live.glob("*.parquet")).name
        if defect.startswith("missing_"):
            parent = retained if "snapshot" in defect else live
            name = "manifest.json" if "manifest" in defect else payload
            (parent / name).unlink()
        elif defect in {"changed_live", "changed_snapshot", "metadata_mismatch"}:
            parent = live if defect == "changed_live" else retained
            name = "_metadata.json" if defect == "metadata_mismatch" else payload
            with (parent / name).open("ab") as stream:
                stream.write(b"tampered")
        elif defect in {
            "wrong_job",
            "wrong_rows",
            "wrong_time",
            "manifest_error",
            "wrong_status",
        }:
            tamper_manifest(retained / "manifest.json", defect)
        elif defect == "row_sum":
            result.records_updated = 11
        elif defect == "empty_parquet":
            pd.DataFrame({"synthetic": []}).to_parquet(live / payload)
        elif defect == "extra_snapshot":
            (live / "runs/extra").mkdir()
        elif defect == "nested_history":
            (retained / "runs").mkdir()
        elif defect == "external_symlink":
            outside = root / "outside"
            outside.write_text("synthetic outside bytes")
            (live / "redirect").symlink_to(outside)
        elif defect == "runtime_configuration":
            with (root / "scheduler.yml").open("a") as stream:
                stream.write("\n# changed execution input\n")
        return result

    monkeypatch.setattr(verifier, "cmd_run_job", run_and_tamper)
    receipt = verifier.execute_run(REPO, root)
    assert receipt["verification"] == "NOT_VERIFIED"
    assert receipt["classification"] == "readback"
    assert receipt["checks_failed"]


@pytest.mark.parametrize(
    "status,error",
    [
        ("failure", "transient"),
        ("skipped", None),
        ("success", "[partial:deterministic] synthetic"),
    ],
)
def test_native_failure_and_partial_are_not_full_success(
    verifier, tmp_path, monkeypatch, status, error
):
    real_run = verifier.cmd_run_job

    def unsuccessful(*args, **kwargs):
        result = real_run(*args, **kwargs)
        result.status, result.error_msg = status, error
        return result

    monkeypatch.setattr(verifier, "cmd_run_job", unsuccessful)
    receipt = verifier.execute_run(REPO, tmp_path / "execution")
    assert receipt["verification"] == "NOT_VERIFIED"
    assert receipt["classification"] == (
        "PARTIAL" if status == "success" else "native_result"
    )


def test_existing_execution_cannot_be_repeated(verifier, tmp_path):
    root = tmp_path / "execution"
    assert verifier.execute_run(REPO, root)["verification"] == "VERIFIED"
    before = (root / "receipt.json").read_bytes()
    with pytest.raises(FileExistsError):
        verifier.execute_run(REPO, root)
    assert (root / "receipt.json").read_bytes() == before


def test_elapsed_cap_escapes_adapter_retries(verifier, tmp_path, monkeypatch):
    from worldenergydata.scheduler.jobs.bsee_refresh import BseeRefreshJob

    calls = []

    def timed_out(*args):
        calls.append(True)
        raise verifier.ElapsedTimeCap()

    monkeypatch.setattr(BseeRefreshJob, "_process_dataset", timed_out)
    receipt = verifier.execute_run(REPO, tmp_path / "execution")
    assert calls == [True]
    assert receipt["verification"] == "NOT_VERIFIED"
    assert receipt["classification"] == "timeout"
    assert len(receipt["datasets"]) == 5


@pytest.mark.parametrize("failure", ["partial", "download", "filesystem"])
def test_failed_run_retains_dataset_evidence(verifier, tmp_path, monkeypatch, failure):
    from worldenergydata.bsee.data.refresh.payload import DatasetFailure, FailureClass
    from worldenergydata.scheduler.jobs.bsee_refresh import BseeRefreshJob

    write = BseeRefreshJob._process_dataset

    def selective(self, scraper, name, info, output):
        if failure == "partial" and name != "pipeline_location":
            return write(self, scraper, name, info, output)
        if failure == "filesystem":
            raise PermissionError("synthetic write denied")
        return DatasetFailure(
            name,
            (
                "expected zip, got html"
                if failure == "partial"
                else "download error: name resolution failed"
            ),
            FailureClass.DETERMINISTIC,
        )

    monkeypatch.setattr(BseeRefreshJob, "_process_dataset", selective)
    receipt = verifier.execute_run(REPO, tmp_path / "execution")
    assert receipt["verification"] == "NOT_VERIFIED"
    assert len(receipt["datasets"]) == 5
    written = [
        item
        for item in receipt["datasets"].values()
        if item["disposition"] == "written"
    ]
    assert len(written) == (4 if failure == "partial" else 0)
    assert all(item["rows"] == 2 and item["sha256"] for item in written)
    assert (
        receipt["failure_layer"]
        == {
            "partial": "payload_or_parsing",
            "download": "name_resolution",
            "filesystem": "filesystem",
        }[failure]
    )


def test_import_origin_mismatch_blocks_invocation(verifier, tmp_path, monkeypatch):
    import worldenergydata.scheduler.cli as cli

    monkeypatch.setattr(cli, "__file__", str(tmp_path / "competing/cli.py"))
    receipt = verifier.execute_run(REPO, tmp_path / "execution")
    assert receipt["verification"] == "NOT_VERIFIED"
    assert receipt["classification"] == "preflight"
    assert "import_origin" in receipt["checks_failed"]
    assert "result" not in receipt


def test_git_metadata_ignores_inherited_root_bindings(verifier, tmp_path, monkeypatch):
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        monkeypatch.setenv(key, str(tmp_path / "not-a-repository"))
    receipt = verifier.execute_run(REPO, tmp_path / "execution")
    assert receipt["verification"] == "VERIFIED"
    assert len(receipt["base_commit"]) == 40


def test_cli_cap_writes_unverified_reports_and_exits_nonzero(
    verifier, tmp_path, monkeypatch
):
    from worldenergydata.scheduler.jobs.bsee_refresh import BseeRefreshJob

    def capped(*args):
        signal.raise_signal(signal.SIGTERM)

    monkeypatch.setattr(BseeRefreshJob, "_process_dataset", capped)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--run-root",
            str(tmp_path / "execution"),
            "--reports-dir",
            str(tmp_path / "reports"),
        ],
    )
    previous = signal.getsignal(signal.SIGTERM)
    try:
        assert verifier.main() == 1
    finally:
        signal.signal(signal.SIGTERM, previous)
    receipt = json.loads(
        (tmp_path / "reports/issue-271-output-readback.json").read_text()
    )
    assert receipt["verification"] == "NOT_VERIFIED"
    assert receipt["classification"] == "timeout"


def test_mixed_native_failures_remain_retryable_in_public_receipt(
    verifier, tmp_path, monkeypatch
):
    from worldenergydata.bsee.data.refresh.payload import DatasetFailure, FailureClass
    from worldenergydata.scheduler.jobs.bsee_refresh import BseeRefreshJob

    write = BseeRefreshJob._process_dataset

    def mixed(self, scraper, name, info, output):
        if name == "pipeline_location":
            return DatasetFailure(
                name, "expected zip, got html", FailureClass.DETERMINISTIC
            )
        if name == "deepqual":
            return DatasetFailure(name, "download failed", FailureClass.TRANSIENT)
        return write(self, scraper, name, info, output)

    monkeypatch.setattr(BseeRefreshJob, "_process_dataset", mixed)
    receipt = verifier.execute_run(REPO, tmp_path / "execution")
    assert receipt["verification"] == "NOT_VERIFIED"
    assert receipt["result"]["retryable"] is True
    assert receipt["native_error_class"] == "mixed_or_transient"
