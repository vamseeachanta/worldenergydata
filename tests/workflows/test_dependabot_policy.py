"""Dependency batches and domain gates for issue #481.

Expected groups are policy examples, not calculated dependency versions.
Matching follows GitHub's Dependabot options reference, sections ``groups``,
``patterns and exclude-patterns``, ``update-types`` and ``rebase-strategy``:
https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference
Retrieved 2026-10-19. No engineering constants or acceptance limits apply.
"""

import importlib.util
from fnmatch import fnmatchcase
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def updates():
    config = yaml.safe_load((ROOT / ".github/dependabot.yml").read_text())
    return {item["package-ecosystem"]: item for item in config["updates"]}


def _group(update, dependency, kind, applies_to="version-updates"):
    """Apply the documented first matching group rule to a synthetic update."""
    for name, rule in update["groups"].items():
        if rule.get("applies-to", "version-updates") != applies_to:
            continue
        if kind not in rule.get("update-types", ("major", "minor", "patch")):
            continue
        if any(fnmatchcase(dependency, p) for p in rule.get("exclude-patterns", [])):
            continue
        if any(fnmatchcase(dependency, p) for p in rule["patterns"]):
            return name
    return None


@pytest.mark.parametrize("ecosystem", ["pip", "github-actions"])
def test_automatic_rebase_is_explicit(updates, ecosystem):
    """GitHub documents auto as the default; keep the intended policy explicit."""
    assert updates[ecosystem]["rebase-strategy"] == "auto"


@pytest.mark.parametrize("kind", ["minor", "patch"])
@pytest.mark.parametrize(
    "dependencies,expected",
    [
        (("pydantic", "pydantic-settings"), "validation"),
        (("sphinx", "sphinx-rtd-theme", "mkdocs", "mkdocstrings"), "documentation"),
        (
            ("pytest", "pytest-cov", "flake8", "isort", "types-PyYAML"),
            "dev-dependencies",
        ),
        (("pandas", "numpy", "plotly"), "data-science"),
        (("scrapy", "selenium", "beautifulsoup4"), "web-scraping"),
    ],
)
def test_related_updates_share_their_batch(updates, dependencies, expected, kind):
    """Hand evaluation: every listed name matches its named group's pattern.

    Both admitted update kinds therefore yield that same batch; unrelated
    families retain different batch names. These are illustrative names from
    pyproject.toml, not forecasts of available package releases.
    """
    for dependency in dependencies:
        assert _group(updates["pip"], dependency, kind) == expected


@pytest.mark.parametrize("dependency", ["pydantic", "sphinx", "pandas", "flake8"])
def test_python_major_updates_remain_individual(updates, dependency):
    """No Python group admits major updates, so first-match yields no batch."""
    assert _group(updates["pip"], dependency, "major") is None


def test_python_groups_do_not_change_security_update_policy(updates):
    """Groups default to version updates; security updates remain independent."""
    for rule in updates["pip"]["groups"].values():
        assert rule.get("applies-to", "version-updates") == "version-updates"
        assert set(rule["update-types"]) == {"minor", "patch"}
    assert _group(updates["pip"], "pydantic", "patch", "security-updates") is None
    assert _group(updates["pip"], "unrelated-library", "patch") is None
    # Batching must not suppress updates or widen the manifest search scope.
    assert "ignore" not in updates["pip"]
    assert "allow" not in updates["pip"]
    assert updates["pip"]["directory"] == "/"


def test_action_updates_keep_the_existing_batch(updates):
    """The separate action ecosystem retains its existing all-update batch."""
    for kind in ("major", "minor", "patch"):
        assert _group(updates["github-actions"], "actions/checkout", kind) == "actions"


@pytest.fixture(scope="module")
def selector():
    spec = importlib.util.spec_from_file_location(
        "dependency_policy_selector", ROOT / "scripts/ci/select_test_targets.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "path,domain",
    [
        ("src/worldenergydata/eia/client.py", "eia"),
        ("packages/worldenergydata-eia/src/worldenergydata/eia/client.py", "eia"),
        ("packages/worldenergydata-bsee/src/worldenergydata/hse/client.py", "hse"),
        ("tests/unit/eia/test_client.py", "eia"),
    ],
)
def test_domain_changes_select_only_their_domain_and_shared_contracts(
    selector, path, domain
):
    """Issue #481 policy: one touched domain plus the mandatory shared shard.

    The expected set is written out from the path's domain and the existing
    selector contract; the implementation does not supply the expected value.
    """
    matrix = selector.to_matrix([path], ROOT)
    assert matrix["scope"] == "modules"
    assert {shard["name"] for shard in matrix["include"]} == {
        "_always",
        f"unit-{domain}",
    }


@pytest.mark.parametrize("path", ["pyproject.toml", "uv.lock"])
def test_shared_dependency_changes_keep_the_full_gate(selector, path):
    """Shared dependency manifests affect every domain, per issue #481."""
    assert selector.to_matrix([path], ROOT)["scope"] == "full"


def test_dependency_policy_tests_are_always_selected(selector):
    """The policy guard runs even when the dependency config is the only edit."""
    matrix = selector.to_matrix([".github/dependabot.yml"], ROOT)
    always = next(shard for shard in matrix["include"] if shard["name"] == "_always")
    assert "tests/workflows" in always["targets"].split()
