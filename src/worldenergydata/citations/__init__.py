"""Calc-citation-contract for worldenergydata calc outputs.

Emits ``Citation`` provenance sidecars alongside numeric calc results so every
standards-derived constant is traceable to its source (which standard /
publisher / revision). Mirrors the digitalmodel pilot.

Governing issue: worldenergydata#361
Contract: workspace-hub ``.claude/rules/calc-citation-contract.md``
"""
from __future__ import annotations

from worldenergydata.citations.schema import (
    Citation,
    CitedValue,
    CitationResolutionError,
    CitationValidationError,
    validate_citation,
)
from worldenergydata.citations.resolver import (
    WIKI_REPO_URL,
    ROUTING_RULE_URL,
    resolve_wiki_base,
    resolve_wiki_path,
)
from worldenergydata.citations.sidecar import (
    SIDECAR_SCHEMA_VERSION,
    SIDECAR_SUFFIX,
    build_sidecar,
    emit_sidecar,
    load_sidecar,
)
from worldenergydata.citations.registry import (
    FIRST_WAVE,
    get_bsee_royalty_rate,
    get_wti_price_base,
    get_depth_breakpoint,
)

__all__ = [
    "Citation",
    "CitedValue",
    "CitationResolutionError",
    "CitationValidationError",
    "validate_citation",
    "resolve_wiki_base",
    "resolve_wiki_path",
    "WIKI_REPO_URL",
    "ROUTING_RULE_URL",
    "SIDECAR_SCHEMA_VERSION",
    "SIDECAR_SUFFIX",
    "build_sidecar",
    "emit_sidecar",
    "load_sidecar",
    "FIRST_WAVE",
    "get_bsee_royalty_rate",
    "get_wti_price_base",
    "get_depth_breakpoint",
]
