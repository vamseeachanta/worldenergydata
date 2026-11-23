"""Keep the system overview's inline local links and source map usable."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
OVERVIEW = REPO_ROOT / ".ai/system-overview/README.md"
INLINE_LINK = re.compile(r"(?<!!)\[[^\]\n]+\]\(([^\s)]+)\)")
ENTRY_POINTS = (
    "src/worldenergydata",
    "packages",
    "src/worldenergydata/cli/main.py",
    "packages/worldenergydata-bsee/src/worldenergydata/bsee",
    "packages/worldenergydata-eia/src/worldenergydata/eia",
)


def _local_targets(document: Path, root: Path) -> set[Path]:
    """Resolve this document's inline links; reject missing or escaping targets."""
    targets = set()
    for destination in INLINE_LINK.findall(document.read_text(encoding="utf-8")):
        url = urlsplit(destination)
        if url.scheme or url.netloc:
            continue
        target = (document.parent / unquote(url.path)).resolve()
        assert target.is_relative_to(root.resolve()), "link escapes repository"
        assert target.exists(), f"missing local target: {destination}"
        targets.add(target)
    assert targets, "overview must contain local links"
    return targets


def test_overview_local_links_resolve():
    _local_targets(OVERVIEW, REPO_ROOT)


@pytest.mark.parametrize("entry_point", ENTRY_POINTS)
def test_overview_declares_existing_source_entry_points(entry_point):
    targets = _local_targets(OVERVIEW, REPO_ROOT)
    assert (REPO_ROOT / entry_point).resolve() in targets


def test_overview_python_requirement_matches_package():
    configuration = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    requirement = re.search(r'^requires-python = "([^"]+)"', configuration, re.M)
    assert requirement is not None
    assert f"Python `{requirement.group(1)}`" in OVERVIEW.read_text(encoding="utf-8")


def test_local_link_checker_accepts_file_and_directory(tmp_path):
    (tmp_path / "a file.md").write_text("# Example\n", encoding="utf-8")
    (tmp_path / "source").mkdir()
    document = tmp_path / "README.md"
    document.write_text(
        "[file](a%20file.md#example)\n[directory](source/)\n"
        "[external](https://example.org/missing.md)\n",
        encoding="utf-8",
    )
    assert _local_targets(document, tmp_path) == {
        tmp_path / "a file.md",
        tmp_path / "source",
    }


@pytest.mark.parametrize(
    ("body", "error"),
    [
        ("[broken](missing.md)", "missing local target"),
        ("[outside](../outside.md)", "link escapes repository"),
        ("No links here.", "overview must contain local links"),
    ],
)
def test_local_link_checker_rejects_invalid_document(tmp_path, body, error):
    document = tmp_path / "README.md"
    document.write_text(body, encoding="utf-8")
    with pytest.raises(AssertionError, match=error):
        _local_targets(document, tmp_path)
