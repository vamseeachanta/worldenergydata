"""Keep optional statistics dependencies confined to the metocean CI shard."""

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER = REPO_ROOT / "scripts/ci/run_domain_tests.sh"


@pytest.mark.parametrize("shard", ["unit-metocean", "unit-eia", "_always", ""])
def test_runner_installs_member_extra_only_for_metocean(tmp_path, shard):
    log = tmp_path / "uv-calls.jsonl"
    uv = tmp_path / "uv"
    uv.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "with open(os.environ['UV_CALL_LOG'], 'a') as output:\n"
        "    output.write(json.dumps(sys.argv[1:]) + '\\n')\n"
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
    arguments = ["tests/unit/metocean", "--deselect", "a test id", "-n", "2"]
    result = subprocess.run(["bash", str(RUNNER), *arguments], env=env)
    assert result.returncode == 0
    calls = [json.loads(line) for line in log.read_text().splitlines()]
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
