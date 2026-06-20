"""First-wave registry of citation-emitting getters (worldenergydata#361).

Each getter returns a ``CitedValue`` carrying the provenance of a
standards-derived constant used in worldenergydata calcs. Sources are REAL:

  - BSEE/BOEM federal royalty rate (1/8 = 12.5%) -> 30 CFR Part 250
  - WTI price-deck base reference                -> EIA STEO / FRED (WTISPLC)
  - Water-depth dev-system breakpoints           -> worldenergydata INTERNAL
    calibration (explicitly NOT a published standard; the issue asks to
    "document the source" -- the source is internal calibration, so it is
    cited as such rather than fabricating a standard for the number).

Fail-closed behaviour
---------------------
When ``validate=True`` (and/or ``repo_root`` is provided) each getter resolves
its citation against the live wiki and raises ``CitationResolutionError`` (with
``code_id`` in the message) if the backing page is missing or its frontmatter
disagrees -- per #2481 D2. The default ``validate=False`` lets calcs attach
provenance and emit sidecars even where a wiki clone is not present, which is
the common worldenergydata runtime; flip to ``validate=True`` in the
defensibility/audit path.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from worldenergydata.citations.schema import (
    Citation,
    CitedValue,
    validate_citation,
)

# --- Citation templates (real sources) -------------------------------------

_BSEE_ROYALTY_CITATION = {
    "code_id": "30-cfr-250",
    "publisher": "BSEE",
    "revision": "2024",
    "section": "30 CFR Part 250 (Oil and Gas and Sulphur Operations in the OCS); "
    "1/8 statutory royalty for pre-2007 deepwater OCS leases",
    "wiki_path": "wikis/regulatory/wiki/standards/30-cfr-250.md",
    "units": "fraction",
    "note": "Federal royalty rate on OCS production; published lease rates range "
    "12.5%-18.75% (1/8 to 3/16).",
}

_WTI_PRICE_CITATION = {
    "code_id": "eia-steo-wti",
    "publisher": "EIA",
    "revision": "2025-10",
    "section": "EIA Short-Term Energy Outlook -- WTI spot price; cross-checked "
    "against FRED series WTISPLC",
    "wiki_path": "wikis/markets/wiki/standards/eia-steo-wti.md",
    "units": "USD/bbl",
    "retrieved": "2025-10-31",
    "note": "Price-deck base reference. Time-varying -> 'retrieved'/'revision' "
    "track the as-of date.",
}

_DEPTH_BREAKPOINT_CITATION = {
    "code_id": "wed-devsystem-calibration",
    "publisher": "worldenergydata",
    "revision": "v30",
    "section": "fdas/core/config.classify_dev_system_by_depth thresholds "
    "(<500 ft dry tree; <6000 ft subsea-15; >=6000 ft subsea-20)",
    "wiki_path": "wikis/internal/wiki/standards/wed-devsystem-calibration.md",
    "units": "ft",
    "note": "INTERNAL calibration, not a published standard. Cited as internal so "
    "the breakpoint is traceable without claiming external authority.",
}

# Published OCS royalty rates (fractions). Real: 1/8 = 12.5% (legacy/deepwater
# relief), 3/16 = 18.75% (shallow-water / post-2007 leases). Matches
# fdas/core/config.DEFAULT_ASSUMPTIONS["ROYALTY_RATE"].
_ROYALTY_RATES: dict[str, float] = {
    "deepwater": 0.125,
    "shelf": 0.1875,
}


def get_bsee_royalty_rate(
    lease_class: str = "deepwater",
    *,
    validate: bool = False,
    repo_root: Optional[Path] = None,
) -> CitedValue:
    """BSEE/BOEM federal royalty rate for OCS production (30 CFR Part 250)."""
    if lease_class not in _ROYALTY_RATES:
        raise ValueError(
            f"Unknown lease_class {lease_class!r}; "
            f"expected one of {sorted(_ROYALTY_RATES)}"
        )
    citation = Citation(**_BSEE_ROYALTY_CITATION)
    if validate or repo_root is not None:
        validate_citation(citation, repo_root=repo_root)
    return CitedValue(
        value=_ROYALTY_RATES[lease_class],
        citation=citation,
        units="fraction",
    )


def get_wti_price_base(
    *, validate: bool = False, repo_root: Optional[Path] = None
) -> CitedValue:
    """WTI price-deck base reference (EIA STEO / FRED WTISPLC). USD/bbl."""
    citation = Citation(**_WTI_PRICE_CITATION)
    if validate or repo_root is not None:
        validate_citation(citation, repo_root=repo_root)
    return CitedValue(value=75.0, citation=citation, units="USD/bbl")


def get_depth_breakpoint(
    which: str = "deepwater",
    *,
    validate: bool = False,
    repo_root: Optional[Path] = None,
) -> CitedValue:
    """Water-depth dev-system breakpoint (worldenergydata internal calibration).

    ``which='dry'`` -> 500 ft (dry-tree/subsea boundary);
    ``which='deepwater'`` -> 6000 ft (subsea-15/subsea-20 boundary).
    """
    breakpoints = {"dry": 500.0, "deepwater": 6000.0}
    if which not in breakpoints:
        raise ValueError(
            f"Unknown breakpoint {which!r}; expected one of {sorted(breakpoints)}"
        )
    citation = Citation(**_DEPTH_BREAKPOINT_CITATION)
    if validate or repo_root is not None:
        validate_citation(citation, repo_root=repo_root)
    return CitedValue(value=breakpoints[which], citation=citation, units="ft")


#: First-wave getters, keyed by a stable name for discovery / iteration in tests
#: and the NPV citations panel (#358).
FIRST_WAVE = {
    "bsee_royalty_rate": get_bsee_royalty_rate,
    "wti_price_base": get_wti_price_base,
    "depth_breakpoint": get_depth_breakpoint,
}
