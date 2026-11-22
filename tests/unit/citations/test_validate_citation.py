"""Fail-closed metadata checks in both supported wiki layouts."""

from dataclasses import replace
from pathlib import Path

import pytest

from worldenergydata.citations import CitationResolutionError, validate_citation

PUBLISHERS = {
    "boem-gom-royalty": "BOEM",
    "fdas-dev-system-depth-breakpoints": "WorldEnergyData",
    "wti-price-deck-sources": "EIA/FRED",
    "fdas-npv-methodology": "WorldEnergyData",
}


@pytest.mark.parametrize("code_id,publisher", PUBLISHERS.items())
@pytest.mark.parametrize("as_string", [False, True])
def test_fixture_pages(citation, wiki_root, code_id, publisher, as_string):
    cited = replace(
        citation,
        code_id=code_id,
        publisher=publisher,
        wiki_path=f"wikis/production-engineering/wiki/standards/{code_id}.md",
    )
    root = str(wiki_root) if as_string else wiki_root
    assert validate_citation(cited, repo_root=root) is None


def write_page(root, citation, text):
    page = root / citation.wiki_path
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(text, encoding="utf-8")
    return page


def test_overlay_layout(citation, wiki_root, tmp_path):
    text = (wiki_root / citation.wiki_path).read_text(encoding="utf-8")
    write_page(tmp_path / "knowledge", citation, text)
    validate_citation(citation, repo_root=tmp_path)


def test_missing_page_carries_code_id(citation, tmp_path):
    with pytest.raises(CitationResolutionError, match=citation.code_id) as caught:
        validate_citation(citation, repo_root=tmp_path)
    assert caught.value.reason == "page_missing"
    assert caught.value.wiki_path == citation.wiki_path


@pytest.mark.parametrize("field", ["code_id", "publisher", "revision"])
@pytest.mark.parametrize("mode", ["missing", "mismatch"])
def test_frontmatter_failures(citation, tmp_path, field, mode):
    fields = {
        key: getattr(citation, key) for key in ("code_id", "publisher", "revision")
    }
    if mode == "missing":
        fields.pop(field)
    else:
        fields[field] = "wrong"
    text = "---\n" + "".join(f'{key}: "{value}"\n' for key, value in fields.items())
    write_page(tmp_path, citation, text + "---\nBody\n")
    with pytest.raises(CitationResolutionError, match=f"frontmatter_{mode}:{field}"):
        validate_citation(citation, repo_root=tmp_path)


@pytest.mark.parametrize("text", ["No frontmatter\n", "---\nwrong: value\n---\n"])
def test_absent_frontmatter_fails_closed(citation, tmp_path, text):
    write_page(tmp_path, citation, text)
    with pytest.raises(CitationResolutionError, match="frontmatter_missing:code_id"):
        validate_citation(citation, repo_root=tmp_path)


def test_flat_frontmatter_ignores_comments_and_unrelated_lines(citation, tmp_path):
    write_page(
        tmp_path,
        citation,
        "---\n# revision: wrong\nnot a scalar\ncode_id: boem-gom-royalty\n"
        'publisher: "BOEM"\nrevision: "2026-07"\n---\n',
    )
    validate_citation(citation, repo_root=tmp_path)


def test_environment_resolution(citation, wiki_root, monkeypatch):
    monkeypatch.setenv("LLM_WIKI_PATH", str(wiki_root))
    validate_citation(citation)


def test_unconfigured_validator_carries_code_id(citation):
    with pytest.raises(CitationResolutionError, match=citation.code_id):
        validate_citation(citation)


IDENTITY = 'code_id: boem-gom-royalty\npublisher: "BOEM"\nrevision: "2026-07"\n'


def nested(text, indent="  "):
    return "".join(f"{indent}{line}\n" for line in text.splitlines())


def test_nested_identity_cannot_stand_in_for_top_level(citation, tmp_path):
    write_page(
        tmp_path,
        citation,
        "---\ncode_id: WRONG\npublisher: WRONG\nrevision: WRONG\nexample:\n"
        + nested(IDENTITY)
        + nested(IDENTITY, "\t")
        + "---\n",
    )
    with pytest.raises(CitationResolutionError, match="frontmatter_mismatch:code_id"):
        validate_citation(citation, repo_root=tmp_path)


def test_nested_identity_alone_is_missing(citation, tmp_path):
    write_page(tmp_path, citation, "---\nexample:\n" + nested(IDENTITY) + "---\n")
    with pytest.raises(CitationResolutionError, match="frontmatter_missing:code_id"):
        validate_citation(citation, repo_root=tmp_path)


@pytest.mark.parametrize("field", ["code_id", "publisher", "revision"])
@pytest.mark.parametrize("wrong_first", [True, False])
def test_duplicate_identity_field_rejected(citation, tmp_path, field, wrong_first):
    right = f"{field}: {getattr(citation, field)}\n"
    extra = f"{field}: WRONG\n" if wrong_first else right
    text = "---\n" + extra + IDENTITY + "---\n"
    write_page(tmp_path, citation, text)
    with pytest.raises(
        CitationResolutionError, match=f"frontmatter_duplicate:{field}"
    ) as caught:
        validate_citation(citation, repo_root=tmp_path)
    assert caught.value.code_id == citation.code_id


def outside_page(tmp_path, citation):
    """A valid page that lives outside the wiki root."""
    return write_page(tmp_path / "outside", citation, "---\n" + IDENTITY + "---\n")


def mixed_layout_root(tmp_path, citation):
    """Contained overlay layout plus an escaping standalone wikis/ symlink."""
    root = tmp_path / "root"
    write_page(root / "knowledge", citation, "---\n" + IDENTITY + "---\n")
    outside_page(tmp_path, citation)
    (root / "wikis").symlink_to(tmp_path / "outside" / "wikis", True)
    return root


def page_symlink_root(tmp_path, citation):
    """A contained wikis/ folder whose cited page is a symlink to outside."""
    root = tmp_path / "root"
    page = root / citation.wiki_path
    page.parent.mkdir(parents=True)
    page.symlink_to(outside_page(tmp_path, citation))
    return root


@pytest.mark.parametrize("build", [mixed_layout_root, page_symlink_root])
@pytest.mark.parametrize("route", ["repo_root", "resolver"])
def test_selected_page_must_stay_inside_root(
    citation, tmp_path, monkeypatch, build, route
):
    root = build(tmp_path, citation)
    kwargs = {"repo_root": root}
    if route == "resolver":
        monkeypatch.setenv("LLM_WIKI_PATH", str(root))
        kwargs = {}
    with pytest.raises(CitationResolutionError, match="page_outside_root") as caught:
        validate_citation(citation, **kwargs)
    assert caught.value.code_id == citation.code_id


def test_contained_page_symlink_is_accepted(citation, tmp_path):
    real = write_page(tmp_path / "real", citation, "---\n" + IDENTITY + "---\n")
    page = tmp_path / citation.wiki_path
    page.parent.mkdir(parents=True)
    page.symlink_to(real)
    validate_citation(citation, repo_root=tmp_path)


def test_invalid_encoding_carries_code_id(citation, tmp_path):
    page = write_page(tmp_path, citation, "")
    page.write_bytes(b"---\ncode_id: \xff\xfe\n---\n")
    with pytest.raises(CitationResolutionError, match=citation.code_id) as caught:
        validate_citation(citation, repo_root=tmp_path)
    assert caught.value.reason == "page_unreadable:UnicodeDecodeError"
    assert isinstance(caught.value.__cause__, UnicodeDecodeError)


@pytest.mark.parametrize(
    "error", [PermissionError, FileNotFoundError, IsADirectoryError]
)
def test_read_failure_carries_code_id(citation, tmp_path, monkeypatch, error):
    """Unreadable, or removed between the existence check and the read."""
    write_page(tmp_path, citation, "---\n" + IDENTITY + "---\n")

    def fail(self, *args, **kwargs):
        raise error(13, "denied", str(self))

    monkeypatch.setattr(Path, "read_text", fail)
    monkeypatch.setattr(Path, "read_bytes", fail)
    with pytest.raises(CitationResolutionError, match=citation.code_id) as caught:
        validate_citation(citation, repo_root=tmp_path)
    assert caught.value.reason == f"page_unreadable:{error.__name__}"
    assert str(tmp_path) not in str(caught.value)
    assert isinstance(caught.value.__cause__, error)
