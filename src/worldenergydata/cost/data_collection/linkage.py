"""
ABOUTME: Sanction-side linkage primitive (issue #335).
ABOUTME: Derived-only exact (operator, project_name) resolution of disclosure
ABOUTME: project rows against existing CostDataPoint sanction records.

Design contract
---------------
This module is the **sanction-side primitive** for disclosure-to-sanction
linkage.  It does one thing and one thing only: given an `(operator,
project_name)` key, it returns one of three explicit outcomes — ``LINKED``,
``UNLINKED``, or ``AMBIGUOUS`` — against a corpus of ``CostDataPoint``
sanction records.

Scope-gating (the parent #334 invariant that only *project-scope* disclosure
rows participate in linkage, and *operator-scope* rows never do) is a
**caller responsibility**.  The resolver deliberately has no scope knowledge;
callers must pre-filter inputs via ``disclosure_row_is_linkable()``.

No fuzzy matching, aliasing, trimming, or case normalization is performed.
If a consumer needs stronger keys than exact `(operator, project_name)`, a
later identifier/uniqueness issue will be required.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from worldenergydata.cost.data_collection.calibration_schema import CostDataPoint
from worldenergydata.cost.data_collection.public_dataset import load_public_dataset

__all__ = [
    "LinkageStatus",
    "CostDataPointLinkResult",
    "resolve_cost_datapoint_link",
    "disclosure_row_is_linkable",
]


# ---------------------------------------------------------------------------
# Linkage outcome enum
# ---------------------------------------------------------------------------


class LinkageStatus(str, Enum):
    """Canonical outcomes for a `(operator, project_name)` resolution."""

    LINKED = "linked"
    UNLINKED = "unlinked"
    AMBIGUOUS = "ambiguous"


# ---------------------------------------------------------------------------
# Linkage result model
# ---------------------------------------------------------------------------


class CostDataPointLinkResult(BaseModel):
    """Immutable outcome of a sanction-side linkage attempt.

    Fields
    ------
    status
        One of ``LinkageStatus.LINKED``, ``UNLINKED``, or ``AMBIGUOUS``.
    match_key_operator
        The operator string the caller supplied; echoed for debuggability.
    match_key_project_name
        The project_name string the caller supplied; echoed for debuggability.
    matched_record
        The single sanction record when ``status == LINKED``; ``None`` otherwise.
    matched_count
        Number of exact candidates found (0 for UNLINKED, 1 for LINKED, >=2 for
        AMBIGUOUS).
    candidates
        Full list of exact-match candidates.  ``[]`` for UNLINKED, a single-
        element list for LINKED, and the complete collision set for AMBIGUOUS.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=False)

    status: LinkageStatus
    match_key_operator: Optional[str] = None
    match_key_project_name: Optional[str] = None
    matched_record: Optional[CostDataPoint] = None
    matched_count: int = Field(ge=0)
    candidates: list[CostDataPoint] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Sanction-side resolver
# ---------------------------------------------------------------------------


def resolve_cost_datapoint_link(
    operator: Optional[str],
    project_name: Optional[str],
    sanctioned_records: Optional[list[CostDataPoint]] = None,
) -> CostDataPointLinkResult:
    """Resolve a disclosure `(operator, project_name)` key to sanction records.

    Parameters
    ----------
    operator
        Operator name exactly as it should match the sanction record.
    project_name
        Project name exactly as it should match the sanction record.
    sanctioned_records
        Sanction-record corpus to match against.  ``None`` (the default)
        triggers a call to :func:`load_public_dataset`.  An explicitly-passed
        empty list ``[]`` is honored as "no records to match" and will never
        fall back to the default loader — this is the contract that lets
        tests and callers inject empty corpora deterministically.

    Returns
    -------
    CostDataPointLinkResult
        Explicit linked / unlinked / ambiguous outcome.  Never raises on
        missing-key inputs; ``None``/empty ``operator`` or ``project_name``
        yields an UNLINKED result.
    """
    if not operator or not project_name:
        return CostDataPointLinkResult(
            status=LinkageStatus.UNLINKED,
            match_key_operator=operator,
            match_key_project_name=project_name,
            matched_record=None,
            matched_count=0,
            candidates=[],
        )

    records = (
        load_public_dataset() if sanctioned_records is None else sanctioned_records
    )

    exact_candidates = [
        rec
        for rec in records
        if rec.operator == operator and rec.project_name == project_name
    ]

    count = len(exact_candidates)
    if count == 0:
        status = LinkageStatus.UNLINKED
        matched_record: Optional[CostDataPoint] = None
    elif count == 1:
        status = LinkageStatus.LINKED
        matched_record = exact_candidates[0]
    else:
        status = LinkageStatus.AMBIGUOUS
        matched_record = None

    return CostDataPointLinkResult(
        status=status,
        match_key_operator=operator,
        match_key_project_name=project_name,
        matched_record=matched_record,
        matched_count=count,
        candidates=exact_candidates,
    )


# ---------------------------------------------------------------------------
# Disclosure-side scope gate (parent #334 invariant)
# ---------------------------------------------------------------------------

# Once #334 lands a ``DisclosureScope(str, Enum)`` in
# ``disclosure_ingest_contract.py``, consumers should pass the enum member's
# string value here (``row.scope.value``).  We accept a plain string to avoid
# importing an unmerged sibling module; the comparison is exact-string, in
# keeping with the "no fuzzy matching" rule for the rest of the module.
_LINKABLE_SCOPE_VALUE = "project"


def disclosure_row_is_linkable(scope: str) -> bool:
    """Return True iff a disclosure row's scope may be linked to a sanction record.

    The parent #334 invariant is that only *project-scope* disclosure rows
    participate in sanction-side linkage; *operator-scope* rows are company-
    level and never linkable to a specific sanctioned project.

    Parameters
    ----------
    scope
        String scope value from the disclosure row (compatible with the
        ``DisclosureScope(str, Enum).value`` that #334 will introduce).

    Returns
    -------
    bool
        ``True`` only if ``scope == "project"``.  Any other value, including
        ``"operator"``, ``None``, or the empty string, yields ``False``.
    """
    return scope == _LINKABLE_SCOPE_VALUE
