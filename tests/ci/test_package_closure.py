"""Static dependency examples with expected closure calculated by hand."""

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name, REPO / f"scripts/ci/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def member(root, name, text, leaf="api.py"):
    file = root / f"packages/worldenergydata-{name}/src/worldenergydata/{name}/{leaf}"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding="utf-8")
    return file.relative_to(root).as_posix()


def test_three_package_chain(tmp_path):
    """alpha imports beta; beta imports gamma: gamma has beta, then alpha as dependents."""
    member(tmp_path, "alpha", "import worldenergydata.beta.api\n")
    member(tmp_path, "beta", "from worldenergydata import gamma\n")
    member(tmp_path, "gamma", "raise RuntimeError('must never execute')\n")
    closure = load("package_closure")
    graph = closure.scan(tmp_path)
    assert graph["imports"] == {
        "worldenergydata-alpha": ["worldenergydata-beta"],
        "worldenergydata-beta": ["worldenergydata-gamma"],
        "worldenergydata-gamma": [],
    }
    assert closure.dependents("worldenergydata-gamma", graph["imports"]) == [
        "worldenergydata-alpha",
        "worldenergydata-beta",
    ]
    assert closure.report(graph)["packages"]["worldenergydata-gamma"] == {
        "direct": ["worldenergydata-beta"],
        "transitive": ["worldenergydata-alpha", "worldenergydata-beta"],
    }


def test_relative_cycle_and_optional_imports(tmp_path):
    """alpha's relative self-import adds no edge; alpha <-> beta includes each other once."""
    member(
        tmp_path,
        "alpha",
        "from . import helper\nif False:\n    import worldenergydata.beta.api\n",
    )
    member(tmp_path, "alpha", "", "helper.py")
    member(tmp_path, "beta", "from worldenergydata.alpha import api\n")
    closure = load("package_closure")
    graph = closure.scan(tmp_path)
    assert closure.dependents("worldenergydata-alpha", graph["imports"]) == [
        "worldenergydata-beta"
    ]
    assert graph["imports"]["worldenergydata-alpha"] == ["worldenergydata-beta"]
    assert graph["not_evaluated"] == []


def test_parent_relative_imports_in_init_and_source(tmp_path):
    """By hand: both ..beta imports resolve to worldenergydata.beta; external json has no edge."""
    member(tmp_path, "alpha", "from ..beta import api\nimport json\n")
    member(tmp_path, "alpha", "from ..beta.api import value\n", "__init__.py")
    member(tmp_path, "beta", "value = None\n")
    graph = load("package_closure").scan(tmp_path)
    assert graph["imports"] == {
        "worldenergydata-alpha": ["worldenergydata-beta"],
        "worldenergydata-beta": [],
    }


def test_selector_gap_diagnostic_has_hand_calculated_targets(tmp_path):
    """Beta changes require alpha's home, while alpha changes have no reverse importer."""
    member(tmp_path, "alpha", "import worldenergydata.beta.api\n")
    changed = member(tmp_path, "beta", "")
    for name in ("alpha", "beta"):
        path = tmp_path / f"tests/unit/{name}/test_api.py"
        path.parent.mkdir(parents=True)
        path.write_text("", encoding="utf-8")
    closure = load("package_closure")
    selector = load("audit_selector_reach").load_selector()
    assert closure.selector_gaps(tmp_path, closure.scan(tmp_path), selector) == [
        {
            "path": changed,
            "missing_targets": ["tests/unit/alpha"],
            "dependents_without_test_home": [],
        }
    ]


def test_parse_errors_are_reported_without_source_text(tmp_path):
    """Malformed code makes the inventory incomplete, rather than disappearing as a leaf."""
    path = member(tmp_path, "alpha", "def broken(\n")
    graph = load("package_closure").scan(tmp_path)
    assert graph["not_evaluated"] == [
        {"path": path, "line": 1, "reason": "SyntaxError"}
    ]


def test_unknown_package_rejected(tmp_path):
    """An absent distribution is a caller error; it is not an import-free member."""
    member(tmp_path, "alpha", "")
    closure = load("package_closure")
    with pytest.raises(KeyError):
        closure.dependents("missing", closure.scan(tmp_path)["imports"])


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="selector gap: gamma source selects gamma tests but omits importing beta and alpha tests",
)
def test_selector_includes_importing_packages(tmp_path):
    """By hand gamma <- beta <- alpha requires all three homes, or full scope."""
    member(tmp_path, "alpha", "import worldenergydata.beta.api\n")
    member(tmp_path, "beta", "import worldenergydata.gamma.api\n")
    changed = member(tmp_path, "gamma", "")
    for name in ("alpha", "beta", "gamma"):
        path = tmp_path / f"tests/unit/{name}/test_api.py"
        path.parent.mkdir(parents=True)
        path.write_text("", encoding="utf-8")
    closure = load("package_closure")
    audit = load("audit_selector_reach")
    selected = audit.load_selector().select([changed], tmp_path)
    graph = closure.scan(tmp_path)
    dependents = closure.dependents("worldenergydata-gamma", graph["imports"])
    required = [f"tests/unit/{p.removeprefix('worldenergydata-')}" for p in dependents]
    assert selected["scope"] == "full" or set(required) <= set(
        selected["xdist"] + selected["seq"]
    )


def test_current_tree_dependency_inventory(tmp_path):
    """Mirror actual import edges in a temporary map and expose every selector gap."""
    closure = load("package_closure")
    real = closure.scan(REPO)
    # A fixture map keeps this regression isolated from application execution.
    for package, providers in real["imports"].items():
        name = package.removeprefix("worldenergydata-")
        text = "".join(
            f"import worldenergydata.{p.removeprefix('worldenergydata-')}\n"
            for p in providers
        )
        member(tmp_path, name, text)
    report = closure.report(real)
    assert set(report["packages"]) == set(closure.scan(tmp_path)["imports"])
    assert not real["not_evaluated"]


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="selector gap: current workspace source diffs omit reverse-import dependent test homes",
)
def test_current_selector_dependency_closure(tmp_path):
    """Every syntactic reverse importer needs a test home covered by the selected targets."""
    import json

    closure = load("package_closure")
    snapshot = tmp_path / "import-map.json"
    snapshot.write_text(json.dumps(closure.scan(REPO)), encoding="utf-8")
    graph = json.loads(snapshot.read_text(encoding="utf-8"))
    selector = load("audit_selector_reach").load_selector()
    assert closure.selector_gaps(REPO, graph, selector) == []


def test_closure_cli(tmp_path, capsys):
    """The two-member edge yields alpha as beta's direct and transitive dependent."""
    import json

    member(tmp_path, "alpha", "import worldenergydata.beta\n")
    member(tmp_path, "beta", "")
    closure = load("package_closure")
    assert closure.main(["--root", str(tmp_path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["packages"]["worldenergydata-beta"]["transitive"] == [
        "worldenergydata-alpha"
    ]
