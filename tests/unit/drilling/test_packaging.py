"""Wheel boundary from the drilling README and member pyproject.toml.

The oracle is exact archive membership and byte equality with the checked-in
pack, not an engineering calculation. No numeric tolerance is needed.
"""

import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

MEMBER = Path(__file__).resolve().parents[3] / "packages/worldenergydata-drilling"
PACK = "worldenergydata/drilling/docs/agent-pack.md"


@pytest.fixture(scope="module")
def drilling_wheel(tmp_path_factory):
    """Build the real member in scratch so build metadata stays out of source."""
    staging = tmp_path_factory.mktemp("drilling-wheel")
    for name in ("pyproject.toml", "README.md"):
        shutil.copy2(MEMBER / name, staging / name)
    shutil.copytree(MEMBER / "src", staging / "src")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from setuptools.build_meta import build_wheel; build_wheel('dist')",
        ],
        cwd=staging,
        capture_output=True,
        text=True,
        check=False,
    )
    (staging / "build.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    assert result.returncode == 0, "Wheel build failed; see scratch build.log"
    (wheel,) = (staging / "dist").glob("*.whl")
    return wheel


def test_wheel_ships_exact_knowledge_pack(drilling_wheel):
    """README boundary: the distributed draft must equal the reviewed source."""
    with ZipFile(drilling_wheel) as archive:
        assert archive.read(PACK) == (MEMBER / "src" / PACK).read_bytes()


def test_wheel_owns_only_drilling_namespace(drilling_wheel):
    """Member pyproject contract: drilling code, no namespace root or siblings."""
    with ZipFile(drilling_wheel) as archive:
        code = {name for name in archive.namelist() if name.endswith(".py")}
    assert "worldenergydata/drilling/__init__.py" in code
    assert "worldenergydata/drilling/batch_economics/economics.py" in code
    assert all(name.startswith("worldenergydata/drilling/") for name in code)
