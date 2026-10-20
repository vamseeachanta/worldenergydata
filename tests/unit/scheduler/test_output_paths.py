"""Output routing examples for issue #271; all payloads are synthetic.

Expected paths are hand concatenations of the configured root and source name.
No engineering coefficients or acceptance limits are used in these tests.
"""

import json
from datetime import datetime
from pathlib import Path

import pytest
import yaml
from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult
from worldenergydata.scheduler.scheduler import DataScheduler


class WritingJob(AbstractJob):
    name = "example_refresh"
    default_output_dir = Path("data/modules/example")

    def run(self, config):
        output_dir = Path(config["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "observations.csv").write_text("value\nfirst\n")
        now = datetime.now()
        return JobResult(self.name, now, now, "success", 1, None)


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.delenv("WORLDENERGYDATA_DATA_DIR", raising=False)
    monkeypatch.delenv("WED_DATA_ROOT", raising=False)
    return tmp_path


def make_scheduler(root, job, **settings):
    config_path = root / "config" / "scheduler" / "scheduler_config.yml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.safe_dump(
            {
                "jobs": [{"name": job.name, **settings}],
                "monitoring": {
                    "log_dir": str(root / "logs"),
                    "status_file": str(root / "status.json"),
                    "retry_max": 1,
                },
            }
        )
    )
    scheduler = DataScheduler(str(config_path))
    scheduler.register_job(job)
    return scheduler


@pytest.mark.parametrize(
    "name,source",
    [
        ("bsee_refresh", "bsee"),
        ("hse_refresh", "hse"),
        ("sodir_refresh", "sodir"),
        ("eia_us_refresh", "eia"),
        ("metocean_refresh", "metocean"),
        ("brazil_anp_refresh", "brazil_anp"),
        ("ukcs_refresh", "ukcs"),
        ("lng_terminals_refresh", "lng_terminals"),
        ("spain_cores_refresh", "spain_cores"),
    ],
)
def test_default_convention_for_every_registered_adapter(root, name, source):
    """Hand calculation: repository root / data / modules / source."""
    from worldenergydata.scheduler.cli import ALL_JOBS

    job = next(job for job in ALL_JOBS if job.name == name)
    assert job.resolve_output_dir({"_scheduler_repo_root": root}) == (
        root / "data" / "modules" / source
    )


@pytest.mark.parametrize("setting", [None, "data/modules/example", "custom/results"])
def test_payload_and_manifest_share_root_from_another_working_directory(
    root, monkeypatch, setting
):
    """Default and relative paths are joined to the config's repository root."""
    job = WritingJob()
    settings = {} if setting is None else {"output_dir": setting}
    scheduler = make_scheduler(root, job, **settings)
    elsewhere = root / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert scheduler.run_once(job.name).status == "success"
    expected = root / (setting or "data/modules/example")
    assert (expected / "observations.csv").read_text() == "value\nfirst\n"
    assert json.loads((expected / "manifest.json").read_text())["status"] == "success"
    assert not (elsewhere / "data").exists()
    assert "_scheduler_repo_root" not in scheduler._config.jobs[0]


@pytest.mark.parametrize("variable", ["WORLDENERGYDATA_DATA_DIR", "WED_DATA_ROOT"])
@pytest.mark.parametrize("setting", [None, "data/modules/example"])
def test_data_root_override_applies_to_defaults_and_checked_in_paths(
    root, monkeypatch, variable, setting
):
    """Hand calculation: external data root / modules / example."""
    external = root / "external-volume" / "data"
    monkeypatch.setenv(variable, str(external))
    settings = {} if setting is None else {"output_dir": setting}
    scheduler = make_scheduler(root, WritingJob(), **settings)
    assert scheduler.run_once("example_refresh").status == "success"
    assert (external / "modules" / "example" / "observations.csv").exists()
    assert not (root / "data").exists()


def test_absolute_override_wins_over_data_root(root, monkeypatch):
    external = root / "external-volume" / "chosen"
    monkeypatch.setenv("WORLDENERGYDATA_DATA_DIR", str(root / "unused"))
    scheduler = make_scheduler(root, WritingJob(), output_dir=str(external))
    scheduler.run_once("example_refresh")
    assert (external / "observations.csv").exists()
    assert not (root / "unused").exists()


@pytest.mark.parametrize("value", [None, "", "   ", False, 12, []])
def test_invalid_output_dir_rejected_before_execution(root, value):
    with pytest.raises(ValueError, match="output_dir"):
        make_scheduler(root, WritingJob(), output_dir=value)


def test_success_preserves_timestamped_payloads_without_recursive_archives(root):
    """Two runs retain independent copies; the first payload cannot change."""
    scheduler = make_scheduler(root, WritingJob())
    scheduler.run_once("example_refresh")
    output_dir = root / "data" / "modules" / "example"
    first = next((output_dir / "runs").iterdir())
    assert first.name.endswith("Z")
    assert (first / "observations.csv").read_text() == "value\nfirst\n"
    (output_dir / "observations.csv").write_text("changed\n")
    assert (first / "observations.csv").read_text() == "value\nfirst\n"
    scheduler.run_once("example_refresh")
    snapshots = list((output_dir / "runs").iterdir())
    assert len(snapshots) == 2  # Hand count: one snapshot per successful run.
    assert all(not (snapshot / "runs").exists() for snapshot in snapshots)
    assert all((snapshot / "manifest.json").exists() for snapshot in snapshots)


@pytest.mark.parametrize("status", ["skipped", "failure"])
def test_unsuccessful_run_creates_no_snapshot(root, monkeypatch, status):
    job = WritingJob()
    now = datetime.now()
    monkeypatch.setattr(
        job,
        "run",
        lambda config: JobResult(job.name, now, now, status, 0, None, retryable=False),
    )
    scheduler = make_scheduler(root, job)
    assert scheduler.run_once(job.name).status == status
    assert not (root / "data").exists()


def test_snapshot_io_failure_does_not_publish_success(root, monkeypatch):
    from worldenergydata.scheduler import output

    def fail_copy(*args, **kwargs):
        raise OSError("synthetic disk failure")

    monkeypatch.setattr(output.shutil, "copy2", fail_copy)
    scheduler = make_scheduler(root, WritingJob())
    assert scheduler.run_once("example_refresh").status == "failure"
    assert not (root / "data/modules/example/manifest.json").exists()


def test_current_directory_path_is_valid(root):
    assert (
        WritingJob().resolve_output_dir(
            {"output_dir": ".", "_scheduler_repo_root": root}
        )
        == root
    )


def test_current_directory_with_data_root_override(root, monkeypatch):
    monkeypatch.setenv("WORLDENERGYDATA_DATA_DIR", str(root / "unused"))
    assert (
        WritingJob().resolve_output_dir(
            {"output_dir": ".", "_scheduler_repo_root": root}
        )
        == root
    )


def test_new_data_root_name_takes_precedence(root, monkeypatch):
    monkeypatch.setenv("WORLDENERGYDATA_DATA_DIR", str(root / "chosen"))
    monkeypatch.setenv("WED_DATA_ROOT", str(root / "legacy"))
    assert WritingJob().resolve_output_dir({"_scheduler_repo_root": root}) == (
        root / "chosen/modules/example"
    )


def test_refresh_metadata_does_not_count_historical_runs(root):
    """One live file plus one historical copy still means one current file."""
    from worldenergydata.scheduler.jobs.base import write_refresh_metadata

    (root / "observations.csv").write_text("value\nfirst\n")
    history = root / "runs" / "earlier"
    history.mkdir(parents=True)
    (history / "observations.csv").write_text("value\nold\n")
    write_refresh_metadata("example", root, 1)
    metadata = json.loads((root / "_metadata.json").read_text())
    assert metadata["file_count"] == 1  # Hand count of the live file above.
    assert metadata["total_size_bytes"] == len(b"value\nfirst\n")


@pytest.mark.parametrize("nested", [False, True])
def test_snapshot_rejects_symlink_payloads(root, nested):
    from worldenergydata.scheduler.output import snapshot_outputs

    payload = root / "payload"
    payload.mkdir()
    parent = payload / "nested" if nested else payload
    parent.mkdir(exist_ok=True)
    outside = root / "outside.csv"
    outside.write_text("private\n")
    (parent / "link.csv").symlink_to(outside)
    with pytest.raises(ValueError, match="symlink"):
        snapshot_outputs(payload)


def test_snapshot_rejects_redirected_history_directory(root):
    from worldenergydata.scheduler.output import snapshot_outputs

    payload = root / "payload"
    payload.mkdir()
    external = root / "outside"
    external.mkdir()
    (payload / "runs").symlink_to(external, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        snapshot_outputs(payload)
    assert not list(external.iterdir())


def test_spain_metadata_excludes_run_copies(root):
    """One live CSV plus a historical copy gives file_count = one."""
    from worldenergydata.scheduler.jobs.spain_cores_refresh import SpainCoresRefreshJob

    (root / "live.csv").write_text("value\nfirst\n")
    earlier = root / "runs" / "earlier"
    earlier.mkdir(parents=True)
    (earlier / "old.csv").write_text("value\nold\n")
    SpainCoresRefreshJob._write_refresh_metadata(root, 1)
    metadata = json.loads((root / "_metadata.json").read_text())
    assert metadata["files"] == ["live.csv"]


def test_metocean_archive_obeys_output_dir(root, monkeypatch):
    from worldenergydata.metocean import update
    from worldenergydata.scheduler.jobs.metocean_refresh import MetoceanRefreshJob

    calls = []

    def update_archive(config, output_dir):
        calls.append(output_dir)
        return {"failures": [], "records_updated": 0}

    monkeypatch.setattr(update, "update_archive", update_archive)
    result = MetoceanRefreshJob().run(
        {
            "archive": {"stations": []},
            "data_root": str(root / "legacy"),
            "output_dir": "data/modules/metocean",
            "_scheduler_repo_root": root,
        }
    )
    assert result.status == "success"
    assert calls == [root / "data/modules/metocean"]


def test_standalone_config_anchors_relative_outputs_at_its_directory(root):
    """Standalone config parent / relative output; no fixed-depth traversal."""
    config = root / "scheduler.yml"
    config.write_text(
        yaml.safe_dump(
            {
                "jobs": [{"name": "example_refresh", "output_dir": "results"}],
                "monitoring": {
                    "log_dir": str(root / "logs"),
                    "status_file": str(root / "status.json"),
                },
            }
        )
    )
    scheduler = DataScheduler(str(config))
    scheduler.register_job(WritingJob())
    assert scheduler.run_once("example_refresh").status == "success"
    assert (root / "results/observations.csv").exists()


def test_shipped_config_declares_destinations_for_all_jobs():
    from worldenergydata.scheduler.cli import ALL_JOBS
    from worldenergydata.scheduler.config import load_config, validate_config

    repo_root = Path(__file__).resolve().parents[3]
    config = load_config(str(repo_root / "config/scheduler/scheduler_config.yml"))
    validate_config(config)
    assert {job["name"] for job in config.jobs} == {job.name for job in ALL_JOBS}
    assert all(job["output_dir"] for job in config.jobs)


def test_worked_example_answer(root):
    """Hand count: the literal observations first and second give two rows."""
    import runpy

    repo_root = Path(__file__).resolve().parents[3]
    example = runpy.run_path(
        str(repo_root / "examples/scheduler/output_dir_example.py")
    )
    assert example["run_example"](root) == {
        "status": "success",
        "records_updated": 2,
        "snapshot_matches_live": True,
    }
