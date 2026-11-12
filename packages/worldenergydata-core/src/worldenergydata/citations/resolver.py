"""Resolve direct-file citation targets without machine-specific search paths.

Precedence: explicit override, LLM_WIKI_PATH, bounded sibling-clone discovery.
Both standalone wikis/ and overlay knowledge/wikis/ layouts are supported.
Invalid explicit configuration fails closed rather than falling back.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from .schema import CitationResolutionError, _join_with_layout_detection

_WALK_HARD_CAP = 8
# Reserved for one-time resolution warnings in calculation consumers.
_RESOLUTION_CACHE: dict[str, bool] = {}
_LOGGER = logging.getLogger(__name__)


def resolve_wiki_base(*, override: Path | str | None = None) -> Path:
    """Find a canonical wiki root or raise an actionable resolution error."""
    if override is not None:
        return _configured_base(Path(override), "override_invalid")

    configured = os.environ.get("LLM_WIKI_PATH")
    if configured:
        return _configured_base(Path(configured), "llm_wiki_path_invalid")

    for candidate in _sibling_candidates():
        validated = _validate_clone(candidate)
        if validated is not None:
            _emit_info_log("citation-resolver: sibling clone at %s", validated)
            return validated

    _emit_error_log("citation-resolver: no wiki root resolved")
    raise CitationResolutionError(
        code_id="<resolver>",
        wiki_path="<base>",
        reason=(
            "resolver_unconfigured: cannot find an llm-wiki clone. "
            "Obtain access to the private llm-wiki repository and set "
            "LLM_WIKI_PATH to its root, or pass an explicit override. "
            "The root must contain wikis/ or knowledge/wikis/."
        ),
    )


def resolve_wiki_path(
    citation_wiki_path: str, *, override: Path | str | None = None
) -> Path:
    """Join a canonical citation path; the validator reports missing pages."""
    base = resolve_wiki_base(override=override)
    return _join_with_layout_detection(base, citation_wiki_path)


def _configured_base(base: Path, reason: str) -> Path:
    validated = _validate_clone(base)
    if validated is not None:
        _emit_info_log("citation-resolver: configured clone at %s", validated)
        return validated
    _emit_error_log("citation-resolver: invalid configured clone at %s", base)
    raise CitationResolutionError(
        code_id="<resolver>",
        wiki_path="<base>",
        reason=(
            f"{reason}: expected a directory containing wikis/ or knowledge/wikis/. "
            "Check the override or LLM_WIKI_PATH."
        ),
    )


def _sibling_candidates() -> tuple[Path, ...]:
    """Bound discovery across nested source and workspace-member layouts."""
    return tuple(
        parent / "llm-wiki"
        for parent in list(Path(__file__).resolve().parents)[:_WALK_HARD_CAP]
    )


def _is_contained(child: Path, base: Path) -> bool:
    try:
        child.relative_to(base)
        return True
    except ValueError:
        return False


def _validate_clone(base: Path) -> Path | None:
    """Reject missing roots, symlink loops and escaping wiki directories."""
    try:
        resolved_base = base.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    if not resolved_base.is_dir():
        return None
    for sub in (resolved_base / "wikis", resolved_base / "knowledge" / "wikis"):
        try:
            resolved_sub = sub.resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if resolved_sub.is_dir() and _is_contained(resolved_sub, resolved_base):
            return resolved_base
    return None


def _redact(value: object) -> str:
    """Collapse a home-directory prefix for resolver logs."""
    text = str(value)
    try:
        home = str(Path.home())
    except (RuntimeError, OSError):
        return "[path removed]"
    if text == home or text.startswith(home + os.sep):
        return "~" + text[len(home) :]
    return text


def _quiet() -> bool:
    return os.environ.get("WORLDENERGYDATA_QUIET_RESOLVER") == "1"


def _emit_info_log(fmt: str, *args: object) -> None:
    if not _quiet():
        _LOGGER.info(fmt, *(_redact(arg) for arg in args))


def _emit_error_log(fmt: str, *args: object) -> None:
    if not _quiet():
        _LOGGER.error(fmt, *(_redact(arg) for arg in args))
