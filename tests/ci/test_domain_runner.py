"""Require the statistics backend in CI while keeping metocean-only installs optional."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER = REPO_ROOT / "scripts/ci/run_domain_tests.sh"


@pytest.mark.parametrize("inherited_requirement", [None, "1"])
@pytest.mark.parametrize("shard", ["unit-metocean", "unit-eia", "_always", ""])
def test_runner_installs_member_extra_only_for_metocean(
    tmp_path, shard, inherited_requirement
):
    log = tmp_path / "uv-calls.jsonl"
    uv = tmp_path / "uv"
    uv.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "with open(os.environ['UV_CALL_LOG'], 'a') as output:\n"
        "    output.write(json.dumps([sys.argv[1:], os.environ.get('WED_REQUIRE_METOCEAN_STATS')]) + '\\n')\n"
        "if sys.argv[1] == 'sync':\n"
        "    sys.exit(int(os.environ.get('SYNC_EXIT', '0')))\n"
    )
    uv.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "SHARD": shard,
        "UV_CALL_LOG": str(log),
    }
    env.pop("WED_REQUIRE_METOCEAN_STATS", None)
    if inherited_requirement is not None:
        env["WED_REQUIRE_METOCEAN_STATS"] = inherited_requirement
    arguments = ["tests/unit/metocean", "--deselect", "a test id", "-n", "2"]
    result = subprocess.run(["bash", str(RUNNER), *arguments], env=env)
    assert result.returncode == 0
    records = [json.loads(line) for line in log.read_text().splitlines()]
    calls = [record[0] for record in records]
    assert records[-1][1] == (
        "1" if shard == "unit-metocean" else inherited_requirement
    )
    assert calls[-1] == [
        "run",
        "--no-sync",
        "--with",
        "pytest-xdist",
        "pytest",
        *arguments,
    ]
    if shard == "unit-metocean":
        assert calls[:-1] == [
            [
                "sync",
                "--frozen",
                "--all-extras",
                "--package",
                "worldenergydata",
                "--package",
                "worldenergydata-metocean",
            ]
        ]
        log.unlink()
        failed = subprocess.run(
            ["bash", str(RUNNER), *arguments], env={**env, "SYNC_EXIT": "7"}
        )
        assert failed.returncode == 7
        assert len(log.read_text().splitlines()) == 1
    else:
        assert len(calls) == 1


def test_workflow_uses_domain_runner():
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text())
    assert workflow["jobs"]["domain-tests"]["with"]["test-runner"] == (
        "bash scripts/ci/run_domain_tests.sh"
    )


def test_bsee_enables_statistics_backend():
    manifest = tomllib.loads(
        (REPO_ROOT / "packages/worldenergydata-bsee/pyproject.toml").read_text()
    )
    assert "worldenergydata-metocean[statistics]" in manifest["project"]["dependencies"]


def test_full_matrix_requires_statistics_collection():
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text())
    assert (
        str(workflow["jobs"]["test"].get("env", {}).get("WED_REQUIRE_METOCEAN_STATS"))
        == "1"
    )


@pytest.mark.parametrize("required", [False, True])
def test_missing_backend_collection_fails_when_required(tmp_path, required):
    suite = tmp_path / "tests"
    target = suite / "unit/metocean/statistics"
    target.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / "tests/conftest.py", suite / "conftest.py")
    (tmp_path / "pytest.ini").write_text("[pytest]\n")
    (target / "test_backend.py").write_text("import metocean_stats\n")
    # Hide the backend even when the parent environment has it installed.
    script = """
import builtins
import importlib.util
import sys
import pytest
original_import = builtins.__import__
original_find_spec = importlib.util.find_spec
def hidden_import(name, *args, **kwargs):
    if name == 'metocean_stats' or name.startswith('metocean_stats.'):
        raise ModuleNotFoundError("No module named 'metocean_stats'")
    return original_import(name, *args, **kwargs)
def hidden_spec(name, *args, **kwargs):
    if name == 'metocean_stats':
        return None
    return original_find_spec(name, *args, **kwargs)
builtins.__import__ = hidden_import
importlib.util.find_spec = hidden_spec
sys.exit(pytest.main(['--collect-only', '-q', '-p', 'no:cacheprovider', 'tests']))
"""
    env = os.environ.copy()
    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_COMMON_DIR",
        "GIT_INDEX_FILE",
        "PYTEST_ADDOPTS",
        "WED_REQUIRE_METOCEAN_STATS",
    ):
        env.pop(key, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if required:
        env["WED_REQUIRE_METOCEAN_STATS"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    if required:
        assert result.returncode == 2, output
        assert "ModuleNotFoundError: No module named 'metocean_stats'" in output
        assert "test_backend.py" in output
    else:
        assert result.returncode == 5, output
        assert "no tests collected" in output
