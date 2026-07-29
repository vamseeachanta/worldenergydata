"""ABOUTME: Canonical loader for the BSEE WAR ``WELL_ACTIVITY_CD`` vocabulary.
ABOUTME: Reads data/war_activity_codes.yml -- the single definition source (#1065).

Why this module exists
----------------------
This vocabulary used to live in four disconnected places: a mislabelled doc
under ``docs/data-sources/bsee/data/WELL_ACTIVITY_CD/``, a hand-maintained dict
in ``lower_tertiary.ops_timeline``, a borehole-status mirror in
``base_configs/modules/bsee/bsee.yml``, and a fourth label map in
``reports/gtm/seasonal_intervention_risk_windows.py``.  Copying is how the
uncertainty flag on ``PND`` was lost: the doc said "PENDING/UNKNOWN" and the
mirrors said "PENDING".

``data/war_activity_codes.yml`` is now the only place these codes are defined.
Everything else imports from here.

The one rule
------------
**Never attach a meaning to a code whose provenance is ``unknown``.**  BSEE
publishes no code list for ``WELL_ACTIVITY_CD`` at all; six of the twelve codes
merely reuse tokens from the published ``BOREHOLE_STAT_CD`` domain (our
inference, corroborated by remark text), and six -- ``WO``, ``PND``, ``CHZ``,
``MPF``, ``REC``, ``TBK`` -- are undocumented anywhere.  Those six carry
``label: None``.  :func:`activity_labels` therefore omits them rather than
inventing a meaning, and a test pins that property so a label cannot be quietly
added later.

Backwards compatibility
-----------------------
:data:`LEGACY_DISPLAY_LABELS` reproduces, byte for byte, the dict that
``ops_timeline.WAR_ACTIVITY_LABELS`` has always exported.  Those strings are
*display* strings, not definitions -- ``lower_tertiary.well_benchmark`` selects
interventions by matching them exactly, so changing them would silently move
published intervention counts.  They are sourced from the YAML's
``legacy_display_label`` field, which is documented there as carrying zero
evidentiary weight.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any, Optional

_DATA_DIR = Path(__file__).resolve().parent / "data"
_CODES_YML = _DATA_DIR / "war_activity_codes.yml"

#: Provenance value marking a code BSEE has never published a meaning for.
PROVENANCE_UNKNOWN = "unknown"

#: Provenance value marking a token that is published, but in the *borehole
#: status* domain rather than as a WAR activity code.  The reuse is inferred.
PROVENANCE_PUBLISHED_OTHER_DOMAIN = "published_other_domain"

__all__ = [
    "PROVENANCE_UNKNOWN",
    "PROVENANCE_PUBLISHED_OTHER_DOMAIN",
    "codes_yaml_path",
    "load_activity_codes",
    "activity_codes",
    "activity_labels",
    "undocumented_codes",
    "LEGACY_DISPLAY_LABELS",
    "legacy_display_labels",
]


def codes_yaml_path() -> Path:
    """Absolute path to the canonical YAML (for docs/tests that cite it)."""
    return _CODES_YML


@functools.lru_cache(maxsize=1)
def load_activity_codes(path: Optional[Path] = None) -> dict[str, Any]:
    """Parse and cache the canonical WAR activity-code definition file.

    Returns the whole document -- ``meta`` (including the record of every BSEE
    surface searched for a published domain), ``borehole_stat_cd``, ``codes``
    and ``outstanding_query`` -- so callers can cite provenance, not just
    labels.
    """
    import yaml

    target = Path(path) if path is not None else _CODES_YML
    with open(target, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _code_rows() -> list[dict[str, Any]]:
    return list(load_activity_codes().get("codes", []))


@functools.lru_cache(maxsize=1)
def activity_codes() -> frozenset[str]:
    """Every non-null ``WELL_ACTIVITY_CD`` token observed in the WAR corpus.

    The null code (882 pre-eWell rows, 1997-2001) is deliberately excluded --
    it is a missing value, not a token.
    """
    return frozenset(
        str(row["code"]) for row in _code_rows() if row.get("code") is not None
    )


@functools.lru_cache(maxsize=1)
def activity_labels() -> dict[str, str]:
    """Code -> label, for codes that have a defensible label ONLY.

    Codes whose provenance is ``unknown`` are absent from this mapping by
    design.  Callers should render the bare code for them (``.get(code, code)``)
    rather than substituting a guess.
    """
    return {
        str(row["code"]): str(row["label"])
        for row in _code_rows()
        if row.get("code") is not None and row.get("label") is not None
    }


@functools.lru_cache(maxsize=1)
def undocumented_codes() -> frozenset[str]:
    """Codes BSEE has published no meaning for, in any domain.

    A basis that includes or excludes any of these is making a choice, not a
    measurement; see #1065, which is open with BSEE for the full domain.
    """
    return frozenset(
        str(row["code"])
        for row in _code_rows()
        if row.get("code") is not None and row.get("provenance") == PROVENANCE_UNKNOWN
    )


@functools.lru_cache(maxsize=1)
def legacy_display_labels() -> dict[str, str]:
    """The historical display strings, preserved for existing consumers.

    NOT definitions.  See the module docstring and the YAML's own note: for an
    ``unknown`` code the string is a guess somebody typed.  Retained only
    because ``lower_tertiary.well_benchmark`` matches on the exact text.
    """
    return {
        str(row["code"]): str(row["legacy_display_label"])
        for row in _code_rows()
        if row.get("code") is not None and row.get("legacy_display_label") is not None
    }


#: Module-level alias of :func:`legacy_display_labels`, re-exported by
#: ``lower_tertiary.ops_timeline`` as the long-standing public name
#: ``WAR_ACTIVITY_LABELS``.
LEGACY_DISPLAY_LABELS = legacy_display_labels()
