"""Five literal golden diffs, enumerated from the fixture topology by hand."""

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def load():
    spec = importlib.util.spec_from_file_location(
        "explain_selection", REPO / "scripts/ci/explain_selection.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def tree(tmp_path):
    for path in (
        "tests/unit/alpha/test_a.py",
        "tests/unit/beta/test_b.py",
        "tests/contracts/test_c.py",
    ):
        file = tmp_path / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("", encoding="utf-8")
    return tmp_path


# Hand calculation: contracts is always-on. A module/package adds its unit home.
# Core selects top-level contracts + unit and the two sequential targets even
# when absent; the full matrix only emits directories present in this fixture.
# A rename contributes both endpoints; deletion contributes its old path.
GOLDENS = [
    (
        "M\tsrc/worldenergydata/engine.py\n",
        (
            "M src/worldenergydata/engine.py -> core\n"
            "  scope=full; targets=tests/contracts tests/unit tests/integration tests/performance\n"
            "scope=full\nxdist=tests/contracts tests/unit\nseq=tests/integration tests/performance\n"
            "shards:\n  unit-alpha [xdist]: tests/unit/alpha\n"
            "  unit-beta [xdist]: tests/unit/beta\n  contracts [xdist]: tests/contracts\n"
        ),
    ),
    (
        "config/repo_structure.yml\n",
        (
            "M config/repo_structure.yml -> contract route\n"
            "  scope=modules; targets=tests/contracts\n"
            "scope=modules\nxdist=tests/contracts\nseq=\n"
            "shards:\n  _always [xdist]: tests/contracts\n"
        ),
    ),
    (
        "D\tsrc/worldenergydata/alpha/removed.py\n",
        (
            "D src/worldenergydata/alpha/removed.py -> module\n"
            "  scope=modules; targets=tests/contracts tests/unit/alpha\n"
            "scope=modules\nxdist=tests/contracts tests/unit/alpha\nseq=\n"
            "shards:\n  _always [xdist]: tests/contracts\n  unit-alpha [xdist]: tests/unit/alpha\n"
        ),
    ),
    (
        (
            "R100\tpackages/worldenergydata-alpha/src/worldenergydata/alpha/api.py\t"
            "packages/worldenergydata-beta/src/worldenergydata/beta/api.py\n"
        ),
        (
            "R100 packages/worldenergydata-alpha/src/worldenergydata/alpha/api.py -> package\n"
            "  scope=modules; targets=tests/contracts tests/unit/alpha\n"
            "R100 packages/worldenergydata-beta/src/worldenergydata/beta/api.py -> package\n"
            "  scope=modules; targets=tests/contracts tests/unit/beta\n"
            "scope=modules\nxdist=tests/contracts tests/unit/alpha tests/unit/beta\nseq=\n"
            "shards:\n  _always [xdist]: tests/contracts\n  unit-alpha [xdist]: tests/unit/alpha\n"
            "  unit-beta [xdist]: tests/unit/beta\n"
        ),
    ),
    (
        "docs/guide.md\n",
        (
            "M docs/guide.md -> ignored\n  scope=skip; targets=tests/contracts\n"
            "scope=skip\nxdist=tests/contracts\nseq=\n"
            "shards:\n  _always [xdist]: tests/contracts\n"
        ),
    ),
]


@pytest.mark.parametrize("diff,expected", GOLDENS)
def test_golden_diffs(tree, diff, expected):
    """Expected output is literal: no expected value is calculated by the selector."""
    script = load()
    assert script.render(script.explain(script.parse_lines(diff), tree)) == expected


def test_git_rename_and_deletion_protocol(tree, monkeypatch):
    """Git -z output places status and paths in separate tokens; both rename ends survive."""
    from types import SimpleNamespace

    script = load()
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(stdout="R100\0old name.py\0new name.py\0D\0gone.py\0")

    monkeypatch.setattr(script.subprocess, "run", run)
    assert script.git_changes(tree, "base", "head") == [
        {"status": "R100", "paths": ["old name.py", "new name.py"]},
        {"status": "D", "paths": ["gone.py"]},
    ]
    assert calls[0][0] == [
        "git",
        "diff",
        "--name-status",
        "-z",
        "--find-renames",
        "--end-of-options",
        "base",
        "head",
        "--",
    ]
    assert calls[0][1]["cwd"] == tree


def test_files_cli_and_missing_refs(tree, capsys):
    """Read-only file input exits successfully and argparse rejects incomplete ref pairs."""
    script = load()
    changes = tree / "changes.txt"
    changes.write_text("docs/guide.md\n", encoding="utf-8")
    assert script.main(["--root", str(tree), "--files-from", str(changes)]) == 0
    assert capsys.readouterr().out == GOLDENS[-1][1]
    with pytest.raises(SystemExit):
        script.main(["--root", str(tree), "--base", "base"])


def test_json_input_preserves_unusual_filenames(tree):
    """A JSON change list can represent tabs and newlines without ambiguous line splitting."""
    script = load()
    changes = [{"status": "M", "paths": ["docs/a\tb\nc.md"]}]
    assert script.parse_lines(json.dumps(changes)) == changes
    rendered = script.render(script.explain(changes, tree))
    assert '"docs/a\\tb\\nc.md" -> ignored' in rendered


def test_mixed_core_and_module_show_individual_and_combined_rules(tree):
    """A module still explains its local route, while a sibling core edit dominates scope."""
    script = load()
    result = script.explain(
        script.parse_lines(
            "src/worldenergydata/engine.py\nsrc/worldenergydata/alpha/api.py"
        ),
        tree,
    )
    assert [r["rule"] for r in result["paths"]] == ["core", "module"]
    assert result["selection"]["scope"] == "full"


def test_workflow_and_integration_rules(tree):
    """Registry is an always-on contract; integration is a sequential module route."""
    script = load()
    changes = script.parse_lines(
        "docs/registry/api.md\ntests/integration/modules/alpha/test_api.py"
    )
    assert [r["rule"] for r in script.explain(changes, tree)["paths"]] == [
        "contract route",
        "module",
    ]


@pytest.mark.parametrize(
    "text", ["R100\tonly-one-path", "D\t", "[]garbage", '[{"status":"M","paths":[]}]']
)
def test_malformed_input_is_rejected(tree, text):
    """Malformed changes are rejected instead of silently explaining another diff."""
    with pytest.raises(ValueError):
        load().parse_lines(text)
