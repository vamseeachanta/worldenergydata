"""Offline contract tests for presence-only capability inventory."""

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[3] / "scripts/audit/check_capability_inventory.py"


def collector():
    spec = importlib.util.spec_from_file_location("capability_inventory", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def put(root, path, text=""):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path):
    inputs = {
        "README.md": "See `direct`.\n",
        "MODULE_INDEX.md": "`decoy`\n| Module | Purpose |\n|---|---|\n"
        "| `direct` | data |\n| `docs_only` | docs |\n| direct | duplicate |\n",
        "module-manifest.yaml": "modules:\n- id: split\n- id: direct\n",
        "data/catalog.yaml": "total_datasets: 999\nmodules:\n"
        "  direct: {datasets: []}\n  catalog_only: {datasets: [{name: sample}]}\n",
        "src/worldenergydata/direct/__init__.py": "raise RuntimeError('no import')\n",
        "src/worldenergydata/namespace/child.py": "",
        "src/worldenergydata/__pycache__/ignored.py": "",
        "src/worldenergydata/empty/readme.txt": "",
        "src/worldenergydata/engine.py": "",
        "packages/member/src/worldenergydata/split/__init__.py": "",
        "packages/member/src/worldenergydata/direct/shim.py": "",
        "tests/unit/direct/test_example.py": "",
        "tests/test_split.py": "",
        "docs/direct/guide.md": "",
    }
    for path, text in reversed(list(inputs.items())):
        put(tmp_path, path, text)
    return tmp_path


def test_exact_union_and_presence_not_readiness(repo):
    result = collector().build_inventory(repo)
    rows = {r["module"]: r for r in result["modules"]}
    assert list(rows) == ["catalog_only", "direct", "docs_only", "namespace", "split"]
    assert rows["direct"]["source_paths"] == [
        "packages/member/src/worldenergydata/direct",
        "src/worldenergydata/direct",
    ]
    assert rows["direct"]["catalog_status"] == "empty"
    assert rows["split"]["catalog_status"] == "absent"
    assert rows["catalog_only"]["catalog_status"] == "nonempty"
    assert rows["docs_only"]["source_paths"] == []
    assert rows["direct"]["index"] and rows["direct"]["manifest"]
    assert rows["direct"]["tests"] == ["tests/unit/direct/test_example.py"]
    assert rows["split"]["tests"] == ["tests/test_split.py"]
    assert rows["direct"]["docs"] == ["docs/direct/guide.md"]
    assert rows["direct"]["readme_mentions"] == ["README.md:1"]
    assert all(r["collectability"] == "not_evaluated" for r in rows.values())
    assert "duplicate_ownership:direct" in result["findings"]
    assert "unresolved_source:docs_only" in result["findings"]
    assert {e["reason"] for e in result["exclusions"]} >= {
        "non_production",
        "no_python",
        "support_file",
    }


def test_deterministic_cli_digests_and_only_explicit_write(repo, tmp_path, monkeypatch):
    module = collector()
    before = {
        p.relative_to(repo): p.read_bytes() for p in repo.rglob("*") if p.is_file()
    }
    output = tmp_path / "inventory.json"
    args = ["--project-root", str(repo), "--json-output", str(output)]
    assert module.main(args) == 0
    first = output.read_bytes()
    original = Path.iterdir
    monkeypatch.setattr(
        Path, "iterdir", lambda p: iter(sorted(original(p), reverse=True))
    )
    assert module.main(args) == 0
    assert output.read_bytes() == first
    result = json.loads(first)
    assert all(not Path(p).is_absolute() for p in result["inputs"])
    assert all(len(digest) == 64 for digest in result["inputs"].values())
    assert str(repo) not in first.decode()
    assert before == {
        p.relative_to(repo): p.read_bytes()
        for p in repo.rglob("*")
        if p.is_file() and p != output
    }
    put(repo, "README.md", "changed\n")
    assert module.build_inventory(repo)["inputs"] != result["inputs"]


@pytest.mark.parametrize(
    "path,text",
    [
        ("module-manifest.yaml", "modules: ["),
        ("module-manifest.yaml", "modules: wrong"),
        ("module-manifest.yaml", "!!python/object:unsafe {}"),
        ("module-manifest.yaml", "modules: [{id: direct}, {id: direct}]"),
        ("module-manifest.yaml", "modules: [{id: 42}]"),
        ("data/catalog.yaml", "modules: {direct: {datasets: wrong}}"),
        ("data/catalog.yaml", "modules: {direct: {}}"),
        ("data/catalog.yaml", "modules: {}\nmodules: {}\n"),
        ("MODULE_INDEX.md", None),
    ],
)
def test_invalid_required_inputs_fail_without_output(repo, capsys, path, text):
    if text is None:
        (repo / path).unlink()
    else:
        put(repo, path, text)
    output = repo / "result.json"
    assert (
        collector().main(["--project-root", str(repo), "--json-output", str(output)])
        == 1
    )
    diagnostic = capsys.readouterr().err
    assert path in diagnostic and len(diagnostic) < 200
    assert str(repo) not in diagnostic and not output.exists()


def test_symlinks_exclusions_unknown_evidence_and_no_aliases(repo, tmp_path):
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    put(outside, "hidden.py", "")
    (repo / "src/worldenergydata/escape").symlink_to(outside, target_is_directory=True)
    (repo / "src/worldenergydata/direct/link").symlink_to(
        outside, target_is_directory=True
    )
    put(repo, "MODULE_INDEX.md", "| Module |\n|---|\n| `split-name` |\n")
    result = collector().build_inventory(repo)
    rows = {r["module"]: r for r in result["modules"]}
    assert "escape" not in rows and "split-name" in rows and "split" in rows
    assert rows["namespace"]["source_paths"] == ["src/worldenergydata/namespace"]
    assert sum(e["reason"] == "symlink" for e in result["exclusions"]) == 2
    (repo / "tests").rename(repo / "uninspected-tests")
    assert collector().build_inventory(repo)["modules"][0]["tests"] is None
