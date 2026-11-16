"""Hermetic wiki and resolver state for citation tests."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def hermetic_resolver(monkeypatch):
    from worldenergydata.citations import resolver

    monkeypatch.delenv("LLM_WIKI_PATH", raising=False)
    monkeypatch.setattr(resolver, "_sibling_candidates", lambda: ())


@pytest.fixture
def wiki_root():
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def citation():
    from worldenergydata.citations import Citation

    return Citation(
        code_id="boem-gom-royalty",
        publisher="BOEM",
        revision="2026-07",
        section="Royalty terms",
        wiki_path="wikis/production-engineering/wiki/standards/boem-gom-royalty.md",
    )
