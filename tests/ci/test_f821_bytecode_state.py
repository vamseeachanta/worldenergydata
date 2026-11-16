"""Offline checks for isolated bytecode experiments on a fixed interpreter."""

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.ci import check_f821


@pytest.fixture
def experiment(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    (source / "sample.py").write_text("missing_name\n")
    monkeypatch.chdir(source)
    return source, tmp_path / "evidence", tmp_path / "bytecode"


def arguments(experiment, *extra):
    _, output, cache = experiment
    return [
        ".",
        "--runs",
        "3",
        "--timeout",
        "30",
        "--output",
        str(output),
        "--bytecode-root",
        str(cache),
        *extra,
    ]


def fake_process(monkeypatch, fail=False):
    calls = []

    def run(command, **kwargs):
        env = kwargs["env"]
        prefix = env.get("PYTHONPYCACHEPREFIX")
        cache = Path(prefix) if prefix else None
        empty = cache is not None and cache.is_dir() and not list(cache.iterdir())
        calls.append((command, kwargs, cache, empty))
        if cache:
            (cache / "compiled.pyc").write_bytes(b"fixture bytecode")
        if "--version" in command:
            return subprocess.CompletedProcess(command, 0, "fixture-version\n", "")
        if fail:
            return subprocess.CompletedProcess(command, 2, "partial", "tool failed")
        stdout = f"{command[-1]}:1:1:F821:undefined name 'scan_canary_missing'\n"
        stdout += "sample.py:1:1:F821:undefined name 'missing_name'\n"
        return subprocess.CompletedProcess(command, 1, stdout, "notice\n")

    monkeypatch.setattr(check_f821.subprocess, "run", run)
    return calls


def report(experiment):
    return json.loads((experiment[1] / "report.json").read_text())


@pytest.mark.parametrize("policy", ["cold-per-run", "warm-shared"])
@pytest.mark.parametrize("launcher", ["direct", "uv"])
def test_cache_policy_and_version_isolation(experiment, monkeypatch, policy, launcher):
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setenv("PYTHONPYCACHEPREFIX", "caller-cache")
    before = dict(os.environ)
    calls = fake_process(monkeypatch)
    assert (
        check_f821.main(
            arguments(
                experiment,
                "--bytecode-policy",
                policy,
                "--launcher",
                launcher,
            )
        )
        == 1
    )
    assert dict(os.environ) == before
    version, *measurements = calls
    assert version[2] not in [call[2] for call in measurements]
    assert version[3]
    assert all(call[2].is_relative_to(experiment[2]) for call in calls)
    assert all("PYTHONDONTWRITEBYTECODE" not in call[1]["env"] for call in calls)
    assert all(call[1]["env"]["RUFF_NUM_THREADS"] == "1" for call in calls)
    assert [call[3] for call in measurements] == (
        [True, True, True] if policy == "cold-per-run" else [True, False, False]
    )
    assert len({call[2] for call in measurements}) == (
        3 if policy == "cold-per-run" else 1
    )
    evidence = report(experiment)
    assert evidence["bytecode_policy"] == policy
    assert [run["cache_state"] for run in evidence["runs"]] == (
        ["cold"] * 3 if policy == "cold-per-run" else ["priming", "warm", "warm"]
    )
    assert evidence["version"]["bytecode_directory"] == str(version[2])
    assert [run["bytecode_directory"] for run in evidence["runs"]] == [
        str(call[2]) for call in measurements
    ]
    assert all(
        run["source_sha256"] == evidence["source_sha256"] for run in evidence["runs"]
    )
    assert evidence["source_after_sha256"] == evidence["source_sha256"]
    assert [run["count"] for run in evidence["runs"]] == [1, 1, 1]
    assert (experiment[1] / "run-1.stderr").read_text() == "notice\n"


@pytest.mark.parametrize("kind", ["empty", "nonempty", "inside", "escaped", "file"])
def test_invalid_roots_fail_before_subprocess(experiment, monkeypatch, capsys, kind):
    source, output, cache = experiment
    if kind in ("empty", "nonempty"):
        cache.mkdir()
        if kind == "nonempty":
            (cache / "retained").write_text("original")
    elif kind == "inside":
        cache = source / "cache"
    elif kind == "escaped":
        link = cache.parent / "link"
        link.symlink_to(source, target_is_directory=True)
        cache = link / "cache"
    else:
        cache.write_text("original")
    args = arguments(experiment, "--bytecode-policy", "cold-per-run")
    args[args.index("--bytecode-root") + 1] = str(cache)
    calls = fake_process(monkeypatch)
    with pytest.raises(SystemExit):
        check_f821.main(args)
    assert (
        "bytecode root must be outside scan targets"
        if kind in ("inside", "escaped")
        else "bytecode root already exists"
    ) in capsys.readouterr().err
    assert calls == []
    assert not output.exists()
    if kind == "nonempty":
        assert (cache / "retained").read_text() == "original"


@pytest.mark.parametrize("missing", ["root", "policy"])
def test_cache_options_require_each_other(experiment, monkeypatch, capsys, missing):
    args = arguments(experiment, "--bytecode-policy", "warm-shared")
    option = "--bytecode-root" if missing == "root" else "--bytecode-policy"
    index = args.index(option)
    del args[index : index + 2]
    calls = fake_process(monkeypatch)
    with pytest.raises(SystemExit):
        check_f821.main(args)
    assert (
        "provide --bytecode-root and --bytecode-policy together"
        in capsys.readouterr().err
    )
    assert calls == []
    assert not experiment[1].exists()


def test_linter_failure_preserves_partial_evidence(experiment, monkeypatch):
    fake_process(monkeypatch, fail=True)
    assert (
        check_f821.main(
            arguments(
                experiment,
                "--bytecode-policy",
                "cold-per-run",
            )
        )
        == 2
    )
    evidence = report(experiment)
    assert evidence["status"] == "ERROR"
    assert evidence["runs"][0]["returncode"] == 2
    assert evidence["runs"][0]["cache_state"] == "cold"
    assert (experiment[1] / "run-1.stdout").read_text() == "partial"
    assert (experiment[1] / "run-1.stderr").read_text() == "tool failed"


def test_legacy_invocation_inherits_bytecode_environment(experiment, monkeypatch):
    monkeypatch.delenv("PYTHONPYCACHEPREFIX", raising=False)
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    args = arguments(experiment)
    del args[args.index("--bytecode-root") :]
    calls = fake_process(monkeypatch)
    assert check_f821.main(args) == 1
    assert all(call[2] is None for call in calls)
    assert all(call[1]["env"]["PYTHONDONTWRITEBYTECODE"] == "1" for call in calls)
    assert "bytecode_policy" not in report(experiment)
    assert all("cache_state" not in run for run in report(experiment)["runs"])


def test_non_windows_launch_needs_no_windows_constant(experiment, monkeypatch):
    monkeypatch.setattr(
        check_f821, "os", SimpleNamespace(name="posix", environ=os.environ)
    )
    monkeypatch.delattr(subprocess, "CREATE_NO_WINDOW", raising=False)
    calls = fake_process(monkeypatch)
    assert (
        check_f821.main(
            arguments(
                experiment,
                "--bytecode-policy",
                "cold-per-run",
            )
        )
        == 1
    )
    assert all(call[1].get("creationflags", 0) == 0 for call in calls)
