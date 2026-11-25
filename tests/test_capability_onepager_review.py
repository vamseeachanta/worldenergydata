"""Regression cases from the capability metadata review of PR 1438."""

import html
import os
import subprocess
from pathlib import Path

import pytest

from tests.test_capability_onepagers import load_builder


@pytest.mark.parametrize("empty_field", ["Price", "cost"])
@pytest.mark.parametrize("blank", ["", " ", "\n", "\r\n", "\u00a0", "\u2003"])
@pytest.mark.parametrize("entrypoint", ["single", "batch"])
def test_empty_economic_field_cannot_consume_next_marker(
    empty_field, blank, entrypoint, tmp_path, monkeypatch
):
    """Each field needs its own value; failed builds preserve retained output."""
    mod = load_builder()
    other_field = "cost" if empty_field == "Price" else "Price"
    spec = dict(
        mod.SPECS[0],
        id="economics-empty",
        title="Empty economic assumptions",
        std=(
            "Public source · data as of: not recorded · "
            f"{empty_field}:{blank}{other_field}: recorded assumptions"
        ),
    )
    out = tmp_path / "output"
    out.mkdir()
    sentinel = out / "sec-economics.html"
    sentinel.write_bytes(b"previous reviewed output\n")
    if entrypoint == "single":
        with pytest.raises(ValueError, match="economics basis"):
            mod.build_onepager(spec, out)
    else:
        monkeypatch.setattr(mod, "SPECS", [dict(mod.SPECS[0]), spec])
        monkeypatch.setattr(mod, "_OUT", out)
        monkeypatch.setattr(mod, "_REPO", tmp_path)
        with pytest.raises(SystemExit) as error:
            mod.main([])
        assert error.value.code == 2
    assert list(out.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b"previous reviewed output\n"


@pytest.mark.parametrize("labels", [("Price", "cost"), ("cost", "Price")])
@pytest.mark.parametrize("separator", ["; ", " · ", "\n"])
def test_economic_fields_preserve_separate_multiline_values(
    labels, separator, tmp_path
):
    """Either order and wrapped values remain valid without changing basis text."""
    mod = load_builder()
    basis = (
        "Public source · data as of: not recorded · "
        f"{labels[0]}:\n recorded first assumptions{separator}"
        f"{labels[1]}:\n recorded second assumptions"
    )
    output = mod.build_onepager(dict(mod.SPECS[0], std=basis), tmp_path)
    assert basis in html.unescape(output.read_text(encoding="utf-8"))


@pytest.mark.parametrize("source", ["\u00a0", "\u2003", "\t\u00a0 · \u2003\n"])
def test_unicode_whitespace_source_is_rejected_before_writing(source, tmp_path):
    """A source requires a name rather than Unicode whitespace or separators."""
    mod = load_builder()
    spec = dict(mod.SPECS[0], id="sample", std=f"{source} · data as of: not recorded")
    out = tmp_path / "output"
    with pytest.raises(ValueError, match="source and explicit data cut-off"):
        mod.build_onepager(spec, out)
    assert not out.exists()


def test_retained_html_stays_lf_in_autocrlf_checkout(tmp_path):
    """All retained bytes survive a Git checkout configured to produce CRLF."""
    root = Path(__file__).resolve().parents[1]
    fixture = tmp_path / "checkout"
    fixture.mkdir()
    # Fixture Git commands must never bind to the caller's repository or index.
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=fixture, env=env, check=True, capture_output=True
        )

    git("init", "--quiet")
    git("config", "core.autocrlf", "true")
    (fixture / ".gitattributes").write_bytes((root / ".gitattributes").read_bytes())
    relative = Path("reports/capabilities/pdf")
    destination = fixture / relative
    destination.mkdir(parents=True)
    expected = {
        page.name: page.read_bytes() for page in (root / relative).glob("*.html")
    }
    assert len(expected) == 26
    for name, content in expected.items():
        assert b"\r\n" not in content, name
        (destination / name).write_bytes(content)
    git("add", ".gitattributes", relative.as_posix())
    for name in expected:
        (destination / name).unlink()
    git("checkout-index", "--force", "--all")
    assert {
        page.name: page.read_bytes() for page in destination.glob("*.html")
    } == expected
