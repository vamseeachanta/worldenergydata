"""Fail-closed royalty provenance; every rate below is a synthetic input.

The example fraction is 1/8, not a claim about any lease or regulation.
The citation shape follows the calculation-output citation contract (v1, 2026).
"""

from dataclasses import replace

import pytest

from worldenergydata.fdas.core.citations import (
    Citation,
    CitationResolutionError,
    CitedRoyalty,
)


@pytest.fixture
def cited_royalty(tmp_path):
    page = tmp_path / "wikis/engineering/standards/royalty.md"
    page.parent.mkdir(parents=True)
    page.write_text(
        "---\ncode_id: SYNTHETIC-ROYALTY\npublisher: Synthetic example\n"
        'revision: "1"\nsource_sibling: generic\nroyalty_rate: 0.125\n'
        "---\nSynthetic assumption: one eighth of gross revenue.\n",
        encoding="utf-8",
    )
    citation = Citation(
        code_id="SYNTHETIC-ROYALTY",
        publisher="Synthetic example",
        revision="1",
        section="Worked example",
        wiki_path="wikis/engineering/standards/royalty.md",
    )
    return CitedRoyalty(rate=1 / 8, citation=citation)


def test_resolves_rate_and_metadata(cited_royalty, tmp_path):
    cited_royalty.validate(tmp_path)


@pytest.mark.parametrize(
    "field", ["code_id", "publisher", "revision", "source_sibling"]
)
def test_mismatched_frontmatter_fails(cited_royalty, tmp_path, field):
    changed = replace(cited_royalty.citation, **{field: "different"})
    with pytest.raises(CitationResolutionError, match=changed.code_id):
        replace(cited_royalty, citation=changed).validate(tmp_path)


def test_missing_page_fails(cited_royalty, tmp_path):
    with pytest.raises(CitationResolutionError, match="SYNTHETIC-ROYALTY"):
        cited_royalty.validate(tmp_path / "absent")


@pytest.mark.parametrize(
    "content",
    ["No frontmatter", "---\n[invalid\n---\n", "---\n- list\n---\n"],
)
def test_bad_frontmatter_fails(cited_royalty, tmp_path, content):
    (tmp_path / cited_royalty.citation.wiki_path).write_text(content, encoding="utf-8")
    with pytest.raises(CitationResolutionError, match="SYNTHETIC-ROYALTY"):
        cited_royalty.validate(tmp_path)


@pytest.mark.parametrize("rate", [-0.1, 1.1, float("nan"), float("inf"), True, "0.125"])
def test_invalid_fraction_rejected(cited_royalty, rate):
    # Fractions are dimensionless: the admissible interval is [0, 1].
    with pytest.raises(ValueError, match="rate"):
        replace(cited_royalty, rate=rate)


def test_rate_must_match_page(cited_royalty, tmp_path):
    # Synthetic alternative fraction: 1/4 differs from the page's 1/8.
    with pytest.raises(CitationResolutionError, match="royalty_rate"):
        replace(cited_royalty, rate=1 / 4).validate(tmp_path)


@pytest.mark.parametrize(
    "path",
    [
        "../royalty.md",
        "wikis/../royalty.md",
        "wikis/engineering/sources/royalty.md",
        "wikis//royalty.md",
        "wikis/./royalty.md",
        "wikis\\royalty.md",
    ],
)
def test_forbidden_paths(cited_royalty, path):
    with pytest.raises(ValueError, match="wiki_path"):
        replace(cited_royalty.citation, wiki_path=path)


def test_symlink_escape_rejected(cited_royalty, tmp_path):
    root = tmp_path / "isolated"
    root.mkdir()
    (root / "wikis").symlink_to(tmp_path / "wikis", target_is_directory=True)
    with pytest.raises(CitationResolutionError, match="outside_root"):
        cited_royalty.validate(root)


def test_symlink_to_source_page_rejected(cited_royalty, tmp_path):
    source = tmp_path / "wikis/engineering/sources/royalty.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        (tmp_path / cited_royalty.citation.wiki_path).read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    link = "wikis/engineering/standards/link.md"
    (tmp_path / link).symlink_to(source)
    citation = replace(cited_royalty.citation, wiki_path=link)
    with pytest.raises(CitationResolutionError, match="source_page"):
        replace(cited_royalty, citation=citation).validate(tmp_path)


@pytest.mark.parametrize("field", ["code_id", "publisher", "revision", "section"])
def test_required_citation_fields(cited_royalty, field):
    with pytest.raises(ValueError, match=field):
        replace(cited_royalty.citation, **{field: " "})


@pytest.mark.parametrize(
    "content",
    [
        "---\ncode_id: first\ncode_id: second\n---\n",
        "---\n? [compound, key]\n: value\n---\n",
        "---\ncode_id: missing_end\n",
    ],
)
def test_ambiguous_frontmatter_fails(cited_royalty, tmp_path, content):
    (tmp_path / cited_royalty.citation.wiki_path).write_text(content, encoding="utf-8")
    with pytest.raises(CitationResolutionError, match="SYNTHETIC-ROYALTY"):
        cited_royalty.validate(tmp_path)


@pytest.mark.parametrize("rate", [0, 1])
def test_explicit_boundary_fractions(cited_royalty, tmp_path, rate):
    # Zero is no levy; one is all gross revenue, by the definition of fraction.
    page = tmp_path / cited_royalty.citation.wiki_path
    page.write_text(
        page.read_text(encoding="utf-8").replace(
            "royalty_rate: 0.125", f"royalty_rate: {rate}"
        ),
        encoding="utf-8",
    )
    replace(cited_royalty, rate=rate).validate(tmp_path)


@pytest.mark.parametrize("value", ["true", '"0.125"', ".nan", ".inf", "null"])
def test_invalid_evidence_fraction(cited_royalty, tmp_path, value):
    page = tmp_path / cited_royalty.citation.wiki_path
    page.write_text(
        page.read_text(encoding="utf-8").replace(
            "royalty_rate: 0.125", f"royalty_rate: {value}"
        ),
        encoding="utf-8",
    )
    with pytest.raises(CitationResolutionError, match="royalty_rate"):
        cited_royalty.validate(tmp_path)
