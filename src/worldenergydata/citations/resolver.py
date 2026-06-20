"""Wiki base-path resolver for the calc-citation-contract (worldenergydata#361).

Mirrors the digitalmodel pilot resolver. Implements a precedence chain:
  1. explicit override kwarg
  2. LLM_WIKI_PATH env var
  3. bounded parent walk from __file__ (cap=8) for workspace-hub overlay
  4. known local-clone fallbacks
  5. fail-closed with an actionable message

Handles both layouts:
  - standalone llm-wiki clone:  <base>/wikis/<domain>/...
  - workspace-hub overlay:      <base>/knowledge/wikis/<domain>/...

Canonical citation ``wiki_path`` form is ``wikis/<domain>/...`` (no
``knowledge/`` prefix). Parent walk is hard-capped to avoid an infinite loop.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from worldenergydata.citations.schema import CitationResolutionError

WIKI_REPO_URL = "https://github.com/vamseeachanta/llm-wiki"
ROUTING_RULE_URL = (
    "https://github.com/vamseeachanta/workspace-hub/blob/main/"
    ".claude/rules/codes-standards-data-routing.md"
)

_WALK_HARD_CAP = 8

_KNOWN_LOCAL_CLONES: tuple[Path, ...] = (
    Path("/mnt/local-analysis/llm-wiki"),
    Path.home() / "workspace-hub" / "llm-wiki",
)

_LOGGER = logging.getLogger("worldenergydata.citations.resolver")


def resolve_wiki_base(*, override: Optional[Path] = None) -> Path:
    """Resolve the wiki base directory using the precedence chain.

    Returns a directory that contains either ``wikis/`` or ``knowledge/wikis/``.

    Raises ``CitationResolutionError`` (reason ``resolver_unconfigured``) with an
    actionable message naming ``LLM_WIKI_PATH`` and the private repo URL.
    """
    if override is not None:
        validated = _validate_clone(Path(override))
        if validated is not None:
            return validated
        raise CitationResolutionError(
            code_id="<resolver>",
            wiki_path="<base>",
            reason=(
                f"override_invalid:{override!s} does not contain "
                "wikis/ or knowledge/wikis/"
            ),
        )

    llm_wiki_env = os.environ.get("LLM_WIKI_PATH")
    if llm_wiki_env:
        env_path = Path(llm_wiki_env)
        if not env_path.exists():
            raise CitationResolutionError(
                code_id="<resolver>",
                wiki_path="<base>",
                reason=f"llm_wiki_path_invalid: LLM_WIKI_PATH={env_path!s} does not exist",
            )
        validated = _validate_clone(env_path)
        if validated is not None:
            return validated
        raise CitationResolutionError(
            code_id="<resolver>",
            wiki_path="<base>",
            reason=(
                f"llm_wiki_path_stale_clone: LLM_WIKI_PATH={env_path!s} exists "
                "but does not contain wikis/ or knowledge/wikis/ subdirectory"
            ),
        )

    here = Path(__file__).resolve()
    for parent in [here, *here.parents][:_WALK_HARD_CAP]:
        validated = _validate_clone(parent)
        if validated is not None:
            return validated

    for candidate in _KNOWN_LOCAL_CLONES:
        validated = _validate_clone(candidate)
        if validated is not None:
            return validated

    raise CitationResolutionError(
        code_id="<resolver>",
        wiki_path="<base>",
        reason=(
            "resolver_unconfigured: cannot find an llm-wiki clone.\n\n"
            "The vamseeachanta/llm-wiki repo is PRIVATE "
            "(codes-standards-data-routing rule).\n\n"
            "To fix: clone the private repo (requires GitHub auth) and set:\n"
            "    git clone " + WIKI_REPO_URL + ".git\n"
            "    export LLM_WIKI_PATH=$(pwd)/llm-wiki\n\n"
            "See: " + ROUTING_RULE_URL
        ),
    )


def resolve_wiki_path(
    citation_wiki_path: str, *, override: Optional[Path] = None
) -> Path:
    """Resolve a citation ``wiki_path`` to an absolute file path, both layouts."""
    base = resolve_wiki_base(override=override)
    standalone_join = base / citation_wiki_path
    if standalone_join.is_file():
        return standalone_join
    overlay_join = base / "knowledge" / citation_wiki_path
    if overlay_join.is_file():
        return overlay_join
    return standalone_join


def _validate_clone(base: Path) -> Optional[Path]:
    if not base.is_dir():
        return None
    if (base / "wikis").is_dir():
        return base
    if (base / "knowledge" / "wikis").is_dir():
        return base
    return None
