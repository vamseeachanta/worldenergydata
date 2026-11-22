"""Literal full-mode and PR goldens, independent of the checkout's fast APIs."""

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
        file.write_text("", encoding="utf-8", newline="\n")
    return tmp_path


# Hand calculation: contracts is always-on. A module/package adds its unit home.
# Core selects top-level contracts + unit and the two sequential targets even
# when absent; the full matrix only emits directories present in this fixture.
# A rename selects its destination; the source is context only. Deletion selects its old path.
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
            "M config/repo_structure.yml -> selector route\n"
            "  scope=modules; targets=tests/contracts\n"
            "scope=modules\nxdist=tests/contracts\nseq=\n"
            "shards:\n  _always [xdist]: tests/contracts\n"
        ),
    ),
    (
        "D\tsrc/worldenergydata/alpha/removed.py\n",
        (
            "D src/worldenergydata/alpha/removed.py -> selector route\n"
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
            "R100 packages/worldenergydata-alpha/src/worldenergydata/alpha/api.py -> selector route (context only)\n"
            "  scope=modules; targets=tests/contracts tests/unit/alpha\n"
            "R100 packages/worldenergydata-beta/src/worldenergydata/beta/api.py -> selector route\n"
            "  scope=modules; targets=tests/contracts tests/unit/beta\n"
            "scope=modules\nxdist=tests/contracts tests/unit/beta\nseq=\n"
            "shards:\n  _always [xdist]: tests/contracts\n  unit-beta [xdist]: tests/unit/beta\n"
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
    assert (
        script.render(script.explain(script.parse_lines(diff), tree, mode="full"))
        == "mode=full\n" + expected
    )


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
        "base...head",
        "--",
    ]
    assert calls[0][1]["cwd"] == tree


def test_files_cli_and_missing_refs(tree, capsys):
    """Read-only file input exits successfully and argparse rejects incomplete ref pairs."""
    script = load()
    changes = tree / "changes.txt"
    changes.write_text("docs/guide.md\n", encoding="utf-8", newline="\n")
    assert (
        script.main(
            ["--root", str(tree), "--files-from", str(changes), "--mode", "full"]
        )
        == 0
    )
    assert capsys.readouterr().out == "mode=full\n" + GOLDENS[-1][1]
    with pytest.raises(SystemExit):
        script.main(["--root", str(tree), "--base", "base"])


def test_json_input_preserves_unusual_filenames(tree):
    """A JSON change list can represent tabs and newlines without ambiguous line splitting."""
    script = load()
    changes = [{"status": "M", "paths": ["docs/a\tb\nc.md"]}]
    assert script.parse_lines(json.dumps(changes), json_input=True) == changes
    rendered = script.render(script.explain(changes, tree, mode="full"))
    assert '"docs/a\\tb\\nc.md" -> ignored' in rendered


def test_mixed_core_and_module_show_individual_and_combined_rules(tree):
    """A module still explains its local route, while a sibling core edit dominates scope."""
    script = load()
    result = script.explain(
        script.parse_lines(
            "src/worldenergydata/engine.py\nsrc/worldenergydata/alpha/api.py"
        ),
        tree,
        mode="full",
    )
    assert [r["rule"] for r in result["paths"]] == ["core", "selector route"]
    assert result["selection"]["scope"] == "full"


def test_workflow_and_integration_rules(tree):
    """Registry is an always-on contract; integration is a sequential module route."""
    script = load()
    changes = script.parse_lines(
        "docs/registry/api.md\ntests/integration/modules/alpha/test_api.py"
    )
    assert [r["rule"] for r in script.explain(changes, tree, mode="full")["paths"]] == [
        "selector route",
        "selector route",
    ]


@pytest.mark.parametrize(
    "text,json_input",
    [
        ("R100\tonly-one-path", False),
        ("D\t", False),
        ("[]garbage", True),
        ('[{"status":"M","paths":[]}]', True),
    ],
)
def test_malformed_input_is_rejected(tree, text, json_input):
    """Malformed changes are rejected instead of silently explaining another diff."""
    with pytest.raises(ValueError):
        load().parse_lines(text, json_input=json_input)


def test_bracket_prefixed_name_is_not_json(tree):
    """A name-only path beginning with a bracket remains a literal path."""
    assert load().parse_lines("[draft]/notes.md\n") == [
        {"status": "M", "paths": ["[draft]/notes.md"]}
    ]


def test_json_cli_requires_explicit_flag(tree, capsys):
    """The flag selects JSON; the same unflagged content remains a literal path."""
    script = load()
    path = tree / "changes.txt"
    path.write_text(
        '[{"status":"D","paths":["docs/guide.md"]}]', encoding="utf-8", newline="\n"
    )
    assert (
        script.main(
            ["--root", str(tree), "--files-from", str(path), "--json", "--mode", "full"]
        )
        == 0
    )
    assert "D docs/guide.md -> ignored" in capsys.readouterr().out
    assert (
        script.main(["--root", str(tree), "--files-from", str(path), "--mode", "full"])
        == 0
    )
    assert 'M [{"status"' in capsys.readouterr().out
    with pytest.raises(SystemExit) as error:
        script.main(["--root", str(tree), "--json"])
    assert error.value.code == 2


@pytest.fixture
def fast_selector():
    """Hand-enumerated public API fixture; PR behavior runs even on older trees."""
    from types import SimpleNamespace

    routes = {
        "scripts/ci/check.py": ("full", "tests/ci", "ci"),
        "src/worldenergydata/engine.py": ("full", None, None),
        "tests/repo_structure/test_layout.py": (
            "modules",
            "tests/repo_structure",
            "repo_structure",
        ),
        "tests/modules/field_development/test_catalog_evidence.py": (
            "modules",
            "tests/modules/field_development/test_catalog_evidence.py",
            "modules-field_development-test_catalog_evidence.py",
        ),
    }

    def select(changed, root):
        return {"scope": routes[changed[0]][0], "xdist": [], "seq": []}

    def select_fast(changed, root):
        target = routes[changed[0]][1]
        return {
            "scope": "modules",
            "xdist": ["tests/contracts"] + ([target] if target else []),
            "seq": [],
        }

    def to_matrix(changed, root, *, fast=False):
        assert fast is True
        _, target, name = routes[changed[0]]
        shards = [{"name": "_always", "mode": "xdist", "targets": "tests/contracts"}]
        if target:
            shards.append({"name": name, "mode": "xdist", "targets": target})
        return {"include": shards}

    return SimpleNamespace(select=select, select_fast=select_fast, to_matrix=to_matrix)


@pytest.mark.parametrize(
    "path,expected",
    [
        (
            "scripts/ci/check.py",
            (
                "mode=pr\nM scripts/ci/check.py -> core (fast gate)\n"
                "  scope=modules; targets=tests/contracts tests/ci\n"
                "scope=modules\nxdist=tests/contracts tests/ci\nseq=\nshards:\n"
                "  _always [xdist]: tests/contracts\n  ci [xdist]: tests/ci\n"
            ),
        ),
        (
            "src/worldenergydata/engine.py",
            (
                "mode=pr\nM src/worldenergydata/engine.py -> core (fast gate)\n"
                "  scope=modules; targets=tests/contracts\n"
                "scope=modules\nxdist=tests/contracts\nseq=\nshards:\n"
                "  _always [xdist]: tests/contracts\n"
            ),
        ),
        (
            "tests/repo_structure/test_layout.py",
            (
                "mode=pr\nM tests/repo_structure/test_layout.py -> selector route\n"
                "  scope=modules; targets=tests/contracts tests/repo_structure\n"
                "scope=modules\nxdist=tests/contracts tests/repo_structure\nseq=\nshards:\n"
                "  _always [xdist]: tests/contracts\n  repo_structure [xdist]: tests/repo_structure\n"
            ),
        ),
        (
            "tests/modules/field_development/test_catalog_evidence.py",
            (
                "mode=pr\nM tests/modules/field_development/test_catalog_evidence.py -> selector route\n"
                "  scope=modules; targets=tests/contracts tests/modules/field_development/test_catalog_evidence.py\n"
                "scope=modules\nxdist=tests/contracts tests/modules/field_development/test_catalog_evidence.py\nseq=\nshards:\n"
                "  _always [xdist]: tests/contracts\n"
                "  modules-field_development-test_catalog_evidence.py [xdist]: tests/modules/field_development/test_catalog_evidence.py\n"
            ),
        ),
    ],
)
def test_pr_goldens(tree, path, expected, fast_selector, monkeypatch):
    """All four fast-mode explanations execute, regardless of selector revision."""
    script = load()
    if not callable(getattr(script._selector(), "select_fast", None)):
        monkeypatch.setattr(script, "_selector", lambda: fast_selector)
    for name in (
        "tests/ci/test_check.py",
        "tests/repo_structure/test_layout.py",
        "tests/modules/field_development/test_catalog_evidence.py",
    ):
        file = tree / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("", encoding="utf-8", newline="\n")
    changes = [{"status": "M", "paths": [path]}]
    assert script.render(script.explain(changes, tree)) == expected


def test_unsupported_fast_api_fails_closed(tree, monkeypatch):
    """An old selector cannot silently stand in for PR fast selection."""
    script = load()
    selector = script._selector()
    monkeypatch.delattr(selector, "select_fast", raising=False)
    monkeypatch.setattr(script, "_selector", lambda: selector)
    with pytest.raises(ValueError, match="PR mode requires.*fast"):
        script.explain([{"status": "M", "paths": ["docs/guide.md"]}], tree)


def test_unsupported_fast_matrix_fails_closed(tree, monkeypatch):
    """Both fast APIs must be available before reporting PR selection."""
    script = load()
    selector = script._selector()
    monkeypatch.setattr(selector, "select_fast", selector.select, raising=False)
    monkeypatch.setattr(selector, "to_matrix", lambda changed, root: {})
    monkeypatch.setattr(script, "_selector", lambda: selector)
    with pytest.raises(ValueError, match="PR mode requires.*fast"):
        script.explain([{"status": "M", "paths": ["docs/guide.md"]}], tree)


def test_malformed_cli_input_reports_usage_error(tree, capsys):
    """Bad line input exits through argparse rather than leaking a traceback."""
    path = tree / "changes.txt"
    path.write_text("R100\tonly-one-path\n", encoding="utf-8", newline="\n")
    with pytest.raises(SystemExit) as error:
        load().main(["--root", str(tree), "--files-from", str(path), "--mode", "full"])
    assert error.value.code == 2
    assert "wrong path count" in capsys.readouterr().err


def test_unavailable_input_reports_usage_error(tree, capsys):
    """Missing files exit through argparse without exposing a traceback."""
    with pytest.raises(SystemExit) as error:
        load().main(["--files-from", str(tree / "absent.txt"), "--mode", "full"])
    assert error.value.code == 2
    assert "input or Git executable unavailable" in capsys.readouterr().err


def test_git_failure_retains_its_reason(tree, capsys, monkeypatch):
    """A failed ref query retains Git's captured diagnostic."""
    import subprocess

    script = load()

    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(
            128, ["git", "diff"], stderr="revision is unavailable"
        )

    monkeypatch.setattr(script.subprocess, "run", fail)
    with pytest.raises(SystemExit) as error:
        script.main(["--root", str(tree), "--base", "absent", "--head", "HEAD"])
    assert error.value.code == 2
    assert "revision is unavailable" in capsys.readouterr().err
