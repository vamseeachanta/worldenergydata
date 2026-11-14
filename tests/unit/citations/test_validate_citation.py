"""Fail-closed metadata checks in both supported wiki layouts."""

from dataclasses import replace

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
