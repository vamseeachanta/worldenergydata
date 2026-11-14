"""Resolver precedence, layout detection, containment and log hygiene."""

import logging
from pathlib import Path

import pytest

from worldenergydata.citations import CitationResolutionError, resolver


def test_override_precedes_environment(wiki_root, tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_WIKI_PATH", str(tmp_path / "missing"))
    assert resolver.resolve_wiki_base(override=str(wiki_root)) == wiki_root.resolve()


def test_environment_precedes_sibling(wiki_root, monkeypatch):
    monkeypatch.setenv("LLM_WIKI_PATH", str(wiki_root))

    def unexpected_guess():
        pytest.fail("sibling discovery must not run for an explicit environment")

    monkeypatch.setattr(resolver, "_sibling_candidates", unexpected_guess)
    assert resolver.resolve_wiki_base() == wiki_root.resolve()


def test_sibling_guess(wiki_root, monkeypatch):
    monkeypatch.setattr(resolver, "_sibling_candidates", lambda: (wiki_root,))
    assert resolver.resolve_wiki_base() == wiki_root.resolve()


def test_sibling_candidates_are_bounded(tmp_path, monkeypatch):
    monkeypatch.undo()
    nested = tmp_path.joinpath(*["level"] * 12) / "resolver.py"
    monkeypatch.setattr(resolver, "__file__", str(nested))
    candidates = resolver._sibling_candidates()
    assert len(candidates) == 8
    assert candidates[0] == nested.parent / "llm-wiki"
    assert all(path.name == "llm-wiki" for path in candidates)


@pytest.mark.parametrize("source", ["override", "environment"])
@pytest.mark.parametrize("kind", ["missing", "empty", "file"])
def test_invalid_explicit_root_never_falls_back(
    source, kind, wiki_root, tmp_path, monkeypatch
):
    root = tmp_path / "invalid"
    if kind == "empty":
        root.mkdir()
    elif kind == "file":
        root.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(resolver, "_sibling_candidates", lambda: (wiki_root,))
    kwargs = {"override": root} if source == "override" else {}
    if source == "environment":
        monkeypatch.setenv("LLM_WIKI_PATH", str(root))
    with pytest.raises(CitationResolutionError):
        resolver.resolve_wiki_base(**kwargs)


def test_unconfigured_message():
    with pytest.raises(CitationResolutionError, match="LLM_WIKI_PATH") as caught:
        resolver.resolve_wiki_base()
    assert "resolver_unconfigured" in caught.value.reason
    assert "llm-wiki" in str(caught.value)


@pytest.mark.parametrize("overlay", [False, True])
def test_resolve_page_layout(citation, wiki_root, tmp_path, overlay):
    base = tmp_path / "clone"
    prefix = base / "knowledge" if overlay else base
    page = prefix / citation.wiki_path
    page.parent.mkdir(parents=True)
    page.write_text((wiki_root / citation.wiki_path).read_text(), encoding="utf-8")
    assert resolver.resolve_wiki_path(citation.wiki_path, override=base) == page


def test_missing_page_returns_canonical_path(wiki_root):
    assert (
        resolver.resolve_wiki_path("wikis/missing.md", override=wiki_root)
        == (wiki_root / "wikis/missing.md").resolve()
    )


def test_clone_symlink_escape_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    base = tmp_path / "clone"
    base.mkdir()
    (base / "wikis").symlink_to(outside, target_is_directory=True)
    with pytest.raises(CitationResolutionError):
        resolver.resolve_wiki_base(override=base)


def test_symlink_loop_rejected(tmp_path):
    loop = tmp_path / "loop"
    loop.symlink_to(loop)
    with pytest.raises(CitationResolutionError):
        resolver.resolve_wiki_base(override=loop)


def test_symlinked_base_is_canonical(wiki_root, tmp_path):
    alias = tmp_path / "alias"
    alias.symlink_to(wiki_root, target_is_directory=True)
    assert resolver.resolve_wiki_base(override=alias) == wiki_root.resolve()


def test_logs_redact_home_prefix(wiki_root, monkeypatch, caplog):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: wiki_root.parent))
    with caplog.at_level(logging.INFO, logger="worldenergydata.citations.resolver"):
        resolver.resolve_wiki_base(override=wiki_root)
    assert str(wiki_root.parent) not in caplog.text
    assert "~/fixtures" in caplog.text


def test_redaction_without_home(monkeypatch):
    def unavailable(cls):
        raise RuntimeError("home directory unavailable")

    monkeypatch.setattr(Path, "home", classmethod(unavailable))
    assert resolver._redact(Path("private") / "clone") == "[path removed]"


def test_quiet_logging(wiki_root, monkeypatch, caplog):
    monkeypatch.setenv("WORLDENERGYDATA_QUIET_RESOLVER", "1")
    with caplog.at_level(logging.INFO):
        resolver.resolve_wiki_base(override=wiki_root)
    assert not caplog.records
