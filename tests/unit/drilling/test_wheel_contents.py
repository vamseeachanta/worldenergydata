"""Keep repository review evidence out of the runtime distribution."""

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


def test_wheel_excludes_review_evidence(tmp_path):
    """Build offline from a disposable copy and inspect actual wheel members."""
    source = Path(__file__).resolve().parents[3] / "packages/worldenergydata-drilling"
    package = tmp_path / "package"
    shutil.copytree(
        source,
        package,
        ignore=shutil.ignore_patterns("__pycache__", "*.egg-info", "build", "dist"),
    )
    environment = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        environment.pop(key, None)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from setuptools.build_meta import build_wheel; build_wheel('dist')",
        ],
        cwd=package,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    wheels = list((package / "dist").glob("*.whl"))
    assert len(wheels) == 1
    with zipfile.ZipFile(wheels[0]) as wheel:
        members = set(wheel.namelist())
    assert not any(name.endswith("/review-evidence.json") for name in members)
    assert "worldenergydata/drilling/docs/agent-pack.md" in members
    for module in (source / "src").rglob("*.py"):
        assert module.relative_to(source / "src").as_posix() in members
