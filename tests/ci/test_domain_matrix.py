"""Portable selector examples, with expected shards derived by hand from routes.

These are routing/set examples, with no engineering coefficients or limits.
The output protocol comes from the reusable workflow called by ci.yml.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ci"))


@pytest.fixture
def engine():
    import domain_matrix

    return domain_matrix


@pytest.fixture
def rules(engine):
    return engine.SelectionRules(
        always_xdist=("checks/unit/core",),
        core_exact=frozenset({"pyproject.toml"}),
        core_prefixes=("automation/",),
        module_patterns=(r"^lib/sample/([^/]+)/", r"^checks/unit/([^/]+)/"),
        integration_patterns=(r"^checks/integration/modules/([^/]+)/",),
        contract_routes={"config/layout.json": "checks/test_layout.py"},
        workflow_prefixes=("examples/workflows/",),
        tests_root="checks",
    )


@pytest.fixture
def tree(tmp_path):
    for name in (
        "checks/unit/core/test_core.py",
        "checks/unit/alpha/test_alpha.py",
        "checks/unit/beta/beta_test.py",
        "checks/unit/helpers/support.py",
        "checks/contracts/test_contract.py",
        "checks/integration/modules/alpha/test_api.py",
        "checks/performance/test_speed.py",
        "checks/test_layout.py",
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    return tmp_path


def test_portable_module_routes_and_contracts(engine, rules, tree):
    """Hand routing: core always, alpha+beta once each, layout exact, API seq."""
    result = engine.to_matrix(
        [
            "lib/sample/beta/api.py",
            "lib/sample/alpha/api.py",
            "checks/unit/alpha/test_alpha.py",
            "config/layout.json",
            "checks/integration/modules/alpha/test_api.py",
        ],
        tree,
        rules,
    )
    assert result == {
        "scope": "modules",
        "include": [
            {"name": "_always", "targets": "checks/unit/core", "mode": "xdist"},
            {"name": "unit-alpha", "targets": "checks/unit/alpha", "mode": "xdist"},
            {"name": "unit-beta", "targets": "checks/unit/beta", "mode": "xdist"},
            {
                "name": "test_layout.py",
                "targets": "checks/test_layout.py",
                "mode": "xdist",
            },
            {
                "name": "seq-alpha",
                "targets": "checks/integration/modules/alpha",
                "mode": "seq",
            },
        ],
    }


@pytest.mark.parametrize("path", ["pyproject.toml", "automation/selector.py"])
def test_full_tree_uses_configured_test_root(engine, rules, tree, path):
    """Hand enumeration: three unit domains, contracts, root file, API and perf.

    Helpers contain no pytest file and therefore contribute no shard.
    """
    result = engine.to_matrix([path], tree, rules)
    assert result["scope"] == "full"
    assert result["include"] == [
        {"name": "unit-alpha", "targets": "checks/unit/alpha", "mode": "xdist"},
        {"name": "unit-beta", "targets": "checks/unit/beta", "mode": "xdist"},
        {"name": "unit-core", "targets": "checks/unit/core", "mode": "xdist"},
        {"name": "contracts", "targets": "checks/contracts", "mode": "xdist"},
        {"name": "_root", "targets": "checks/test_layout.py", "mode": "xdist"},
        {"name": "integration", "targets": "checks/integration", "mode": "seq"},
        {"name": "performance", "targets": "checks/performance", "mode": "seq"},
    ]


@pytest.mark.parametrize("changed", [[], ["README.md"], ["docs/guide.md"]])
def test_docs_and_empty_diff_keep_always_shard(engine, rules, tree, changed):
    """No route matches; the sole output is the explicitly configured core."""
    assert engine.to_matrix(changed, tree, rules) == {
        "scope": "skip",
        "include": [
            {"name": "_always", "targets": "checks/unit/core", "mode": "xdist"}
        ],
    }


def test_registry_change_is_relevant_without_duplicate_shards(engine, rules, tree):
    """The registry prefix selects always; an explicit core route dedupes it."""
    result = engine.to_matrix(
        ["examples/workflows/registry.json", "lib/sample/core/config.py"], tree, rules
    )
    assert result["scope"] == "modules"
    assert result["include"] == [
        {"name": "_always", "targets": "checks/unit/core", "mode": "xdist"}
    ]


def test_empty_matrix_fails_instead_of_emitting_invalid_workflow(
    engine, rules, tmp_path
):
    """No existing always target means no runnable matrix; adoption must fail."""
    with pytest.raises(ValueError, match="no test shards"):
        engine.to_matrix(["README.md"], tmp_path, rules)


@pytest.mark.parametrize("mode", ["file", "stdin", "positional"])
def test_repository_cli_preserves_workflow_protocol(tmp_path, mode):
    """A docs diff has only the existing always shard, independent of CLI input."""
    command = [
        sys.executable,
        str(ROOT / "scripts/ci/select_test_targets.py"),
        "--emit-matrix",
    ]
    if mode == "file":
        changed = tmp_path / "changed.txt"
        changed.write_text("\nREADME.md\n\n", encoding="utf-8")
        command += ["--files-from", str(changed)]
    elif mode == "stdin":
        command += ["--files-from", "-"]
    else:
        command += ["README.md"]
    result = subprocess.run(
        command, input="README.md\n", capture_output=True, text=True, check=True
    )
    scope, matrix = result.stdout.splitlines()
    assert scope == "scope=skip"
    assert matrix.startswith("matrix=")
    assert json.loads(matrix.removeprefix("matrix=")) == {
        "include": [
            {
                "name": "_always",
                "targets": "tests/unit/core tests/unit/common tests/contracts "
                "tests/workflows tests/governance tests/integration/reporting",
                "mode": "xdist",
            }
        ]
    }


def test_portable_cli_reports_empty_matrix(engine, rules, tmp_path, capsys):
    with pytest.raises(SystemExit):
        engine.main(rules, tmp_path, ["--emit-matrix", "README.md"])
    assert "no test shards" in capsys.readouterr().err


@pytest.fixture
def adopted_template(tmp_path):
    """Copy only the documented engine and adapter into an unrelated tree."""
    ci = tmp_path / "scripts/ci"
    ci.mkdir(parents=True)
    shutil.copyfile(ROOT / "scripts/ci/domain_matrix.py", ci / "domain_matrix.py")
    shutil.copyfile(
        ROOT / "docs/ci/templates/select_test_targets.py", ci / "select_test_targets.py"
    )
    for target in (
        "tests/contracts/test_smoke.py",
        "tests/unit/alpha/test_alpha.py",
        "tests/unit/beta/test_beta.py",
        "tests/integration/modules/alpha/test_api.py",
    ):
        path = tmp_path / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    return ci / "select_test_targets.py"


@pytest.mark.parametrize(
    "changed,scope,shards",
    [
        ("README.md", "skip", {"_always"}),
        ("src/sample/alpha/api.py", "modules", {"_always", "unit-alpha"}),
        ("tests/unit/beta/test_beta.py", "modules", {"_always", "unit-beta"}),
        ("config/schema.json", "modules", {"_always"}),
        (
            "tests/integration/modules/alpha/test_api.py",
            "modules",
            {"_always", "seq-alpha"},
        ),
        (
            "pyproject.toml",
            "full",
            {"unit-alpha", "unit-beta", "contracts", "integration"},
        ),
        (
            "src/sample/common/config.py",
            "full",
            {"unit-alpha", "unit-beta", "contracts", "integration"},
        ),
    ],
)
def test_template_works_without_repository_imports(
    adopted_template, tmp_path, changed, scope, shards
):
    """Hand selection: docs -> smoke; module -> smoke+domain; shared -> all.

    The template has alpha/beta unit suites, contracts and integration only.
    Running outside the copied repository also checks its default root logic.
    """
    result = subprocess.run(
        [sys.executable, str(adopted_template), "--emit-matrix", "--files-from", "-"],
        input=changed + "\n",
        cwd=tmp_path.parent,
        capture_output=True,
        text=True,
        check=True,
    )
    scope_line, matrix_line = result.stdout.splitlines()
    assert scope_line == f"scope={scope}"
    matrix = json.loads(matrix_line.removeprefix("matrix="))
    assert {shard["name"] for shard in matrix["include"]} == shards
    assert all(set(shard) == {"name", "targets", "mode"} for shard in matrix["include"])


def test_flat_cli_and_root_override(adopted_template, tree):
    """The explicit alternate root wins over the adapter's root; no tests/ exists."""
    result = subprocess.run(
        [
            sys.executable,
            str(adopted_template),
            "--root",
            str(tree / "checks"),
            "README.md",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.splitlines() == [
        "scope=skip",
        "xdist_targets=",
        "seq_targets=",
    ]
