"""Guard the optional LGPL dependency boundary for the planned adapter.

Expected metadata is the packaging contract in issue #1315: one opt-in extra,
available from either distribution, with no default dependency on metocean-api.
The release pin is sourced from PyPI's metocean-api 1.1.14 release (2026):
https://pypi.org/project/metocean-api/1.1.14/
No engineering equations, coefficients or acceptance tolerances are used.
"""

import subprocess
import sys
from pathlib import Path

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
        (MEMBER, ["metocean-api==1.1.14"]),
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
