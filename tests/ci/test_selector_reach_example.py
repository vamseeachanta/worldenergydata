"""The committed worked example must be reproducible from a disposable tree."""

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def load():
    spec = importlib.util.spec_from_file_location(
        "generate_selector_reach_example",
        REPO / "scripts/ci/generate_selector_reach_example.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_example_matches_committed_document(tmp_path):
    """By hand: three unit files reachable, loose orphan; gamma's dependents are alpha,beta."""
    rendered = load().generate(tmp_path)
    assert rendered == (REPO / "docs/ci/selector-reach-example.md").read_text(
        encoding="utf-8"
    )
    assert "tests/loose/test_orphan.py | orphan" in rendered
    assert (
        "worldenergydata-gamma | worldenergydata-beta | worldenergydata-alpha, worldenergydata-beta"
        in rendered
    )
    assert "D src/worldenergydata/alpha/removed.py -> module" in rendered
    assert (
        "R100 packages/worldenergydata-beta/src/worldenergydata/beta/api.py -> package"
        in rendered
    )


def test_generator_does_not_overwrite_different_input(tmp_path):
    """A populated fixture path is preserved instead of silently destroying user input."""
    destination = tmp_path / "tests/loose/test_orphan.py"
    destination.parent.mkdir(parents=True)
    destination.write_text("preserve", encoding="utf-8")
    with pytest.raises(ValueError, match="existing example input differs"):
        load().generate(tmp_path)
    assert destination.read_text(encoding="utf-8") == "preserve"


def test_generator_cli_is_repeatable(tmp_path, capsys):
    """Reusing identical fixture inputs produces byte-identical output."""
    generator = load()
    assert generator.main(["--example-root", str(tmp_path)]) == 0
    first = capsys.readouterr().out
    assert generator.main(["--example-root", str(tmp_path)]) == 0
    assert capsys.readouterr().out == first
