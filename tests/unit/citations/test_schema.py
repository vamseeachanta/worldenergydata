"""Structural compatibility and path guards for citation sidecars."""

from dataclasses import FrozenInstanceError, asdict, replace

import pytest

from worldenergydata.citations import (
    Citation,
    CitationValidationError,
    CitedValue,
)


def test_frozen_sidecar_preserves_value(citation):
    cited = CitedValue(0.125, citation, "dimensionless")
    assert cited.value == 0.125
    assert asdict(cited)["citation"]["source_sibling"] == "generic"
    assert citation.source_project is None
    with pytest.raises(FrozenInstanceError):
        citation.revision = "changed"
    with pytest.raises(FrozenInstanceError):
        cited.value = 1.0


@pytest.mark.parametrize(
    "field",
    ["code_id", "publisher", "revision", "section", "wiki_path", "source_sibling"],
)
@pytest.mark.parametrize("invalid", ["", "  ", None, 42])
def test_required_strings(citation, field, invalid):
    with pytest.raises(CitationValidationError, match=field):
        replace(citation, **{field: invalid})


@pytest.mark.parametrize("invalid", ["", "  ", 42])
def test_optional_source_project_validation(citation, invalid):
    with pytest.raises(CitationValidationError, match="source_project"):
        replace(citation, source_project=invalid)


def test_routing_fields_round_trip(citation):
    routed = replace(citation, source_sibling="reference", source_project="sample")
    assert Citation(**asdict(routed)) == routed


@pytest.mark.parametrize(
    "path",
    [
        "/wikis/page.md",
        "knowledge/wikis/page.md",
        "sources/page.md",
        "wikis/../page.md",
        "wikis//page.md",
        "wikis/page.md/",
        "wikis/domain\\page.md",
    ],
)
def test_wiki_path_guards(citation, path):
    with pytest.raises(CitationValidationError):
        replace(citation, wiki_path=path)
