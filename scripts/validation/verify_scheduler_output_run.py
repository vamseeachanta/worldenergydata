"""Verify one registered BSEE run, retaining runtime data outside the checkout.

Run with --run-root NEW_DIRECTORY --reports-dir REPORT_DIRECTORY. An external
90-minute timeout is required for live execution. Existing roots are refused;
their receipt and products are read back rather than downloaded again.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import logging
import os
import re
import signal
import subprocess
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path

import pandas as pd
import yaml

from worldenergydata.scheduler.cli import cmd_run_job
from worldenergydata.scheduler.jobs.bsee_refresh import validate_dataset_catalog
from worldenergydata.scheduler.output import resolve_output_dir

JOB = "bsee_refresh"
RELATIVE_OUTPUT = "data/modules/bsee"
SCHEDULER = "packages/worldenergydata-scheduler/src/worldenergydata/scheduler"
CODE_PATHS = [
    f"{SCHEDULER}/{name}"
    for name in (
        "cli.py",
        "scheduler.py",
        "output.py",
        "config.py",
        "monitor.py",
        "alerting.py",
        "status_enricher.py",
        "staleness.py",
        "jobs/base.py",
        "jobs/bsee_refresh.py",
    )
] + [
    "packages/worldenergydata-bsee/src/worldenergydata/bsee/data/scrapers/bsee_web.py",
    "packages/worldenergydata-bsee/src/worldenergydata/bsee/data/refresh/payload.py",
    "scripts/validation/verify_scheduler_output_run.py",
    "config/scheduler/scheduler_config.yml",
    "config/bsee.yml",
]


class ReadbackError(ValueError):
    """A named acceptance criterion was not established."""


class ElapsedTimeCap(BaseException):
    """Escape adapter Exception handlers when the external cap expires."""


def require(condition, criterion):
    if not condition:
        raise ReadbackError(criterion)


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def relocated(root):
    """Temporarily isolate process-global routing for this single invocation."""
    cwd = Path.cwd()
    previous = {
        key: os.environ.get(key)
        for key in ("WORLDENERGYDATA_DATA_DIR", "WED_DATA_ROOT")
    }
    try:
        os.environ["WORLDENERGYDATA_DATA_DIR"] = str(root / "data")
        os.environ.pop("WED_DATA_ROOT", None)
        (root / "cwd").mkdir()
        os.chdir(root / "cwd")
        yield
    finally:
        os.chdir(cwd)
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def payload_files(directory, live=False):
    require(directory.is_dir() and not directory.is_symlink(), "payload_directory")
    paths = {}
    for child in directory.iterdir():
        require(not child.is_symlink(), "payload_symlink")
        if live and child.name == "runs":
            require(not child.is_symlink(), "history_symlink")
            continue
        candidates = [child, *child.rglob("*")] if child.is_dir() else [child]
        for path in candidates:
            require(not path.is_symlink(), "payload_symlink")
            relative = path.relative_to(directory).as_posix()
            require("runs" not in Path(relative).parts, "nested_history")
            if path.is_file() and relative != "manifest.json":
                paths[relative] = path
    return paths


def readback(output, datasets, result, before, receipt):
    snapshots = set((output / "runs").iterdir()) - before
    require(len(snapshots) == 1, "one_new_snapshot")
    retained = snapshots.pop()
    require(
        bool(re.fullmatch(r"\d{8}T\d{6}\.\d{6}-[0-9a-f]{32}Z", retained.name)),
        "timestamped_snapshot",
    )
    live_files, saved_files = payload_files(output, live=True), payload_files(retained)
    require(live_files.keys() == saved_files.keys(), "same_payload_file_set")
    expected_files = {entry["output_file"] for entry in datasets.values()} | {
        "_metadata.json"
    }
    require(live_files.keys() == expected_files, "catalog_payload_file_set")
    hashes = {name: digest(path) for name, path in live_files.items()}
    require(
        hashes == {name: digest(path) for name, path in saved_files.items()},
        "retained_payload_digests",
    )
    receipt["payload_sha256"] = hashes
    total = 0
    for name, entry in datasets.items():
        filename = entry["output_file"]
        require(filename in live_files, "all_catalog_products")
        frame = pd.read_parquet(live_files[filename])
        rows = len(frame)
        require(rows > 0, "positive_dataset_rows")
        total += rows
        receipt["datasets"][name].update(rows=rows, sha256=digest(live_files[filename]))
    require(total == result.records_updated, "summed_rows_equal_native_result")
    expected = {
        "job_name": JOB,
        "status": "success",
        "records_updated": total,
        "start_time": result.start_time.astimezone(timezone.utc).isoformat(),
        "end_time": result.end_time.astimezone(timezone.utc).isoformat(),
        "last_success_ts": result.end_time.astimezone(timezone.utc).isoformat(),
        "refresh_interval_days": 7,
        "error_msg": None,
    }
    for directory in (output, retained):
        path = directory / "manifest.json"
        require(path.is_file(), "native_manifest_readback")
        manifest = json.loads(path.read_text(encoding="utf-8"))
        require(manifest == expected, "native_manifest_readback")
    receipt.update(
        manifests_match=True,
        snapshot=f"RUN_ROOT/{retained.relative_to(output.parents[2]).as_posix()}",
    )


def runtime_config(repo, root):
    shipped = yaml.safe_load(
        (repo / "config/scheduler/scheduler_config.yml").read_text(encoding="utf-8")
    )
    entries = [job for job in shipped["jobs"] if job["name"] == JOB]
    require(len(entries) == 1, "one_shipped_bsee_entry")
    entry = dict(entries[0])
    require(
        entry["output_dir"] == RELATIVE_OUTPUT and entry["enabled"],
        "shipped_relative_destination",
    )
    entry["catalog_path"] = str(repo / "config/bsee.yml")
    config = {
        "jobs": [entry],
        "monitoring": {
            "retry_max": 1,
            "retry_backoff_seconds": 0,
            "log_dir": str(root / "logs"),
            "status_file": str(root / "status.json"),
        },
    }
    path = root / "scheduler.yml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path, config


def prepare_inputs(repo, root, receipt):
    receipt["code_sha256"] = {name: digest(repo / name) for name in CODE_PATHS}
    for name in CODE_PATHS:
        if name.startswith("packages/") and name.endswith(".py"):
            module_name = name.split("/src/", 1)[1][:-3].replace("/", ".")
            module = import_module(module_name)
            require(Path(module.__file__).resolve() == repo / name, "import_origin")
            require(
                digest(Path(module.__file__)) == receipt["code_sha256"][name],
                "import_digest",
            )
    environment = dict(os.environ)
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        environment.pop(key, None)
    receipt["base_commit"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, env=environment, text=True
    ).strip()
    datasets = yaml.safe_load((repo / "config/bsee.yml").read_text(encoding="utf-8"))[
        "scheduler_datasets"
    ]
    validate_dataset_catalog(datasets)
    require(len(datasets) == 5, "complete_five_entry_catalog")
    config_path, config = runtime_config(repo, root)
    public_config = yaml.safe_load(
        yaml.safe_dump(config)
        .replace(str(repo), "REPO_ROOT")
        .replace(str(root), "RUN_ROOT")
    )
    receipt["runtime_configuration"] = public_config
    receipt["runtime_configuration_sha256"] = digest(config_path)
    return datasets, config_path, config


def invoke_registered(root, config_path, config, receipt):
    with relocated(root):
        output = resolve_output_dir(JOB, config["jobs"][0])
        require(output == root / RELATIVE_OUTPUT, "exact_relocated_destination")
        receipt["routing"] = {
            "branch": "data-prefixed relative-path relocation",
            "configured": RELATIVE_OUTPUT,
            "override": "WORLDENERGYDATA_DATA_DIR",
            "expected": "RUN_ROOT/data/modules/bsee",
            "actual": f"RUN_ROOT/{output.relative_to(root).as_posix()}",
            "working_directory": "RUN_ROOT/cwd",
        }
        before = (
            set((output / "runs").iterdir()) if (output / "runs").exists() else set()
        )
        return cmd_run_job(JOB, config_path=str(config_path)), before


def failure_layer(error):
    """Classify only observed signatures; unknown connection causes stay unknown."""
    if isinstance(error, (ElapsedTimeCap, TimeoutError)):
        return "timeout"
    text = str(error).lower()
    signatures = {
        "name_resolution": ("name resolution", "nameresolutionerror", "getaddrinfo"),
        "http_access_rejection": ("401 client error", "403 client error"),
        "filesystem": ("permission", "write denied", "read-only file", "no space left"),
        "payload_or_parsing": (
            "expected zip",
            "extraction",
            "primary_member",
            "parsed to 0 rows",
        ),
        "download_unclassified": ("download", "connection", "httpsconnectionpool"),
    }
    for layer, markers in signatures.items():
        if any(marker in text for marker in markers):
            return layer
    return (
        "filesystem" if isinstance(error, OSError) else "unclassified_application_error"
    )


def observe_datasets(output, datasets):
    observations = {}
    for name, entry in datasets.items():
        path = output / entry["output_file"]
        item = {
            "file": entry["output_file"],
            "source_url": entry["url"],
            "disposition": "absent",
            "rows": None,
            "sha256": None,
        }
        try:
            require(not path.is_symlink(), "dataset_symlink")
            if path.exists():
                item.update(
                    rows=len(pd.read_parquet(path)),
                    sha256=digest(path),
                    disposition="written",
                )
        except Exception as exc:
            item.update(disposition="unreadable", error_class=type(exc).__name__)
        observations[name] = item
    return observations


def record_native(root, result, receipt):
    native = asdict(result)
    (root / "native-result.json").write_text(
        json.dumps(native, default=str, indent=2) + "\n", encoding="utf-8"
    )
    receipt["result"] = {
        **native,
        "start_time": result.start_time.astimezone(timezone.utc).isoformat(),
        "end_time": result.end_time.astimezone(timezone.utc).isoformat(),
        "error_msg": (
            "Native diagnostic retained with runtime artifacts"
            if result.error_msg
            else None
        ),
    }
    if result.error_msg:
        receipt["failure_layer"] = failure_layer(result.error_msg)
        if result.error_msg.startswith("[partial:deterministic]"):
            receipt["native_error_class"] = "deterministic_partial"
        else:
            receipt["native_error_class"] = (
                "mixed_or_transient" if result.retryable else "deterministic"
            )


def new_receipt(root):
    receipt = {
        "schema": "scheduler-output-readback/1",
        "criteria_version": 1,
        "external_cap_required_minutes": 90,
        "verification": "NOT_VERIFIED",
        "classification": "preflight",
        "source_id": "bsee-data-center",
        "owner": "worldenergydata",
        "started_utc": utc_now(),
        "datasets": {},
        "checks_failed": [],
        "retention": (
            "Runtime products and logs retained outside Git; "
            "no backup or publication established."
        ),
        "limits": (
            "One registered BSEE observation; no live coverage claim for other "
            "adapters or engineering input qualification."
        ),
    }
    (root / "started.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    return receipt


def verify_native(result):
    require(
        result.status == "success" and not result.error_msg and result.job_name == JOB,
        "full_native_success",
    )
    require(
        result.records_updated > 0 and result.end_time >= result.start_time,
        "positive_native_result_and_ordered_times",
    )


def persist_runtime_receipt(root, receipt):
    receipt["ended_utc"] = utc_now()
    (root / "receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    require(
        json.loads((root / "receipt.json").read_text(encoding="utf-8")) == receipt,
        "saved_runtime_receipt",
    )
    return receipt


def execute_run(repo, run_root):
    """Invoke the real registry once; any incomplete criterion stays unverified."""
    repo, root = repo.resolve(), run_root.resolve()
    require(not root.is_relative_to(repo), "runtime_root_outside_checkout")
    root.mkdir(parents=True, exist_ok=False)
    receipt = new_receipt(root)
    stage, datasets = "preflight", {}
    output = root / RELATIVE_OUTPUT
    try:
        datasets, config_path, config = prepare_inputs(repo, root, receipt)
        stage = "execution"
        result, before = invoke_registered(root, config_path, config, receipt)
        record_native(root, result, receipt)
        receipt["datasets"] = observe_datasets(output, datasets)
        stage = (
            "PARTIAL"
            if result.status == "success" and result.error_msg
            else "native_result"
        )
        verify_native(result)
        stage = "readback"
        readback(output, datasets, result, before, receipt)
        require(
            digest(config_path) == receipt["runtime_configuration_sha256"],
            "unchanged_runtime_configuration",
        )
        require(
            receipt["code_sha256"]
            == {name: digest(repo / name) for name in CODE_PATHS},
            "unchanged_execution_inputs",
        )
        receipt.update(verification="VERIFIED", classification="full_catalog_readback")
    except (Exception, ElapsedTimeCap) as exc:
        receipt["classification"] = (
            "timeout" if isinstance(exc, ElapsedTimeCap) else stage
        )
        receipt.setdefault("failure_layer", failure_layer(exc))
        receipt["checks_failed"].append(
            str(exc) if isinstance(exc, ReadbackError) else type(exc).__name__
        )
        receipt["datasets"] = observe_datasets(output, datasets)
    return persist_runtime_receipt(root, receipt)


def save_reports(receipt, directory):
    directory.mkdir(parents=True, exist_ok=True)
    text = json.dumps(receipt, indent=2) + "\n"
    json_path = directory / "issue-271-output-readback.json"
    html_path = directory / "issue-271-output-readback.html"
    if any(path.exists() or path.is_symlink() for path in (json_path, html_path)):
        raise FileExistsError(
            "Public reports already exist; use a new reports directory"
        )
    with json_path.open("x", encoding="utf-8") as stream:
        stream.write(text)
    page = f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><title>Scheduler output readback</title>
<body><h1>Scheduler output readback</h1><p>{html.escape(receipt['verification'])}:
one registered BSEE run against the full five-entry catalog.</p>
<h2>Revision history</h2><table><tr>
<th>Revision</th><th>Date (UTC)</th><th>Change and reason</th></tr>
<tr><td>1</td><td>{receipt['started_utc'][:10]}</td>
<td>Record observed routing and readback against explicit full-run criteria.</td></tr></table>
<p>Table 1. Revision history.</p><h2>Evidence and limitations</h2>
<pre id="receipt">{html.escape(text)}</pre></body></html>
"""
    with html_path.open("x", encoding="utf-8") as stream:
        stream.write(page)
    require(
        json.loads(json_path.read_text(encoding="utf-8")) == receipt,
        "saved_public_json",
    )
    saved = (
        html_path.read_text(encoding="utf-8")
        .split('<pre id="receipt">', 1)[1]
        .split("</pre>", 1)[0]
    )
    require(json.loads(html.unescape(saved)) == receipt, "saved_public_html")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--reports-dir", type=Path, required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    def timeout_received(signum, frame):
        raise ElapsedTimeCap()

    signal.signal(signal.SIGTERM, timeout_received)
    receipt = execute_run(Path(__file__).resolve().parents[2], args.run_root)
    save_reports(receipt, args.reports_dir)
    print(receipt["verification"], receipt["classification"])
    return 0 if receipt["verification"] == "VERIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
