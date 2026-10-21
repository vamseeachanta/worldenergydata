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
from packaging.requirements import Requirement

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10; tomli is a pytest dependency.
    import tomli as tomllib

MEMBER = Path(__file__).resolve().parents[3] / "packages/worldenergydata-drilling"
PACK = "worldenergydata/drilling/docs/agent-pack.md"


def test_build_requirement_supports_recursive_package_data():
    """Recursive package-data globs require setuptools 62.3 or newer."""
    config = tomllib.loads((MEMBER / "pyproject.toml").read_text(encoding="utf-8"))
    (requirement,) = (
        Requirement(value)
        for value in config["build-system"]["requires"]
        if Requirement(value).name == "setuptools"
    )
    assert "62.3.0" in requirement.specifier
    for unsupported in ("61.0", "61.9", "62.0", "62.2.0"):
        assert unsupported not in requirement.specifier


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


def test_wheel_ships_exact_non_python_members(drilling_wheel):
    """Data additions require an explicit update to the distribution contract."""
    with ZipFile(drilling_wheel) as archive:
        data = {
            name
            for name in archive.namelist()
            if name.startswith("worldenergydata/drilling/")
            and not name.endswith((".py", "/"))
        }
        assert data == {PACK}
        for name in data:
            assert archive.read(name) == (MEMBER / "src" / name).read_bytes()
