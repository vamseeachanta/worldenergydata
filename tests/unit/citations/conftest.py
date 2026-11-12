"""Hermetic wiki and resolver state for citation tests."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def reset_resolution_cache(monkeypatch):
    from worldenergydata.citations import resolver

    resolver._RESOLUTION_CACHE.clear()
    monkeypatch.delenv("LLM_WIKI_PATH", raising=False)
    monkeypatch.setattr(resolver, "_sibling_candidates", lambda: ())
    yield
    resolver._RESOLUTION_CACHE.clear()


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
