"""Guard the optional LGPL dependency boundary for the planned adapter.

Expected metadata is the packaging contract in issue #1315: one opt-in extra,
available from either distribution, with no default dependency on metocean-api.
The release pin is sourced from PyPI's metocean-api 1.1.14 release (2026):
https://pypi.org/project/metocean-api/1.1.14/
No engineering equations, coefficients or acceptance tolerances are used.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest
from packaging.requirements import Requirement

try:
    import tomllib
except ModuleNotFoundError:  # Python versions before the stdlib TOML parser.
    import tomli as tomllib

REPO_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists()
)
MEMBER = "packages/worldenergydata-metocean/pyproject.toml"
MANIFESTS = ("pyproject.toml", MEMBER)


def _project(manifest):
    with (REPO_ROOT / manifest).open("rb") as stream:
        return tomllib.load(stream)["project"]


@pytest.mark.parametrize("manifest", MANIFESTS)
def test_default_dependencies_do_not_activate_metocean_api(manifest):
    """Independently inspect each requirement for direct or forwarded opt-in."""
    for dependency in _project(manifest)["dependencies"]:
        requirement = Requirement(dependency)
        assert requirement.name != "metocean-api"
        if requirement.name == "worldenergydata-metocean":
            assert "metocean-api" not in requirement.extras


@pytest.mark.parametrize(
    ("manifest", "expected"),
    [
        ("pyproject.toml", ["worldenergydata-metocean[metocean-api]"]),
        (MEMBER, ["metocean-api==1.1.14; python_version >= '3.11'"]),
    ],
)
def test_named_extra_is_available_from_either_distribution(manifest, expected):
    """Root forwards the extra; member pins the verified PyPI release above."""
    assert _project(manifest)["optional-dependencies"]["metocean-api"] == expected


@pytest.mark.parametrize("manifest", MANIFESTS)
def test_no_other_extra_activates_metocean_api(manifest):
    """The LGPL library must have exactly one opt-in route per distribution."""
    extras = _project(manifest).get("optional-dependencies", {})
    for extra, dependencies in extras.items():
        if extra == "metocean-api":
            continue
        for dependency in dependencies:
            requirement = Requirement(dependency)
            assert requirement.name != "metocean-api"
            if requirement.name == "worldenergydata-metocean":
                assert "metocean-api" not in requirement.extras


@pytest.mark.parametrize(
    ("python_version", "enabled"), [("3.10", False), ("3.11", True), ("3.12", True)]
)
def test_optional_library_only_activates_on_supported_python(python_version, enabled):
    requirement = Requirement(
        _project(MEMBER)["optional-dependencies"]["metocean-api"][0]
    )
    active = requirement.marker is None or requirement.marker.evaluate(
        {"python_version": python_version}
    )
    assert active is enabled


def _write_resolution_manifest(path, manifest):
    """Retain the submitted Python range and extra, omitting unrelated deps."""
    source = _project(manifest)
    project = {key: source[key] for key in ("name", "version", "requires-python")}
    project["dependencies"] = (
        ["worldenergydata-metocean"] if manifest == MANIFESTS[0] else []
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "[project]\n"
        + "\n".join(f"{key} = {json.dumps(value)}" for key, value in project.items())
        + "\n[project.optional-dependencies]\nmetocean-api = "
        + json.dumps(source["optional-dependencies"]["metocean-api"])
        + "\n",
        encoding="utf-8",
    )


def test_optional_dependency_resolves_for_supported_python_range(tmp_path):
    """Universal resolution must retain Python 3.10 even on newer interpreters.

    A local metadata-only wheel models the upstream release's Python >=3.11
    requirement (see the PyPI source above), without installing its large stack.
    Both real extra declarations are resolved together in an isolated workspace.
    """
    uv = shutil.which("uv")
    assert uv is not None, "uv is required for the workspace resolution regression"
    for manifest in MANIFESTS:
        _write_resolution_manifest(tmp_path / manifest, manifest)
    with (tmp_path / "pyproject.toml").open("a", encoding="utf-8") as stream:
        stream.write(
            '\n[tool.uv.workspace]\nmembers = ["packages/*"]\n'
            "[tool.uv.sources]\nworldenergydata-metocean = {workspace = true}\n"
            'metocean-api = {path = "metocean_api-1.1.14-py3-none-any.whl"}\n'
        )
    with ZipFile(tmp_path / "metocean_api-1.1.14-py3-none-any.whl", "w") as wheel:
        wheel.writestr(
            "metocean_api-1.1.14.dist-info/METADATA",
            "Metadata-Version: 2.3\nName: metocean-api\nVersion: 1.1.14\n"
            "Requires-Python: >=3.11\n",
        )
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        env.pop(key, None)
    result = subprocess.run(
        [uv, "lock", "--offline", "--python", sys.executable],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    with (tmp_path / "uv.lock").open("rb") as stream:
        locked = tomllib.load(stream)
    assert locked["requires-python"] == ">=3.10"
    assert any(package["name"] == "metocean-api" for package in locked["package"])


def test_core_import_without_optional_library():
    """A fresh interpreter without site packages imports the real core root.

    The child adds only the repository's root source tree. It checks that the
    optional library cannot be found before importing, so an installed copy in
    the parent process cannot conceal an accidental dependency.
    """
    script = """import importlib.util
import sys

sys.path.insert(0, sys.argv[1])
assert importlib.util.find_spec('metocean_api') is None
import worldenergydata
assert worldenergydata.__version__
assert 'metocean_api' not in sys.modules
"""
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c", script, str(REPO_ROOT / "src")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
