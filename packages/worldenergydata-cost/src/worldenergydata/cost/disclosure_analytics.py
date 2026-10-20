# ABOUTME: Derived annual disclosure analytics views (issue #338).
# ABOUTME: Project revision view, operator capex series, and gated cost-benchmark hook.

"""Derived annual disclosure analytics.

This module takes raw annual-disclosure records and emits *derived* views:

  - :func:`load_project_cost_revision_view` — per-project annual capex with YoY deltas.
  - :func:`load_operator_annual_capex_view` — per-operator annual capex with YoY deltas.
  - :func:`build_cost_disclosure_benchmark` — thin cost-side consumer hook that only
    compares rows already flagged same-basis/comparable under #336 outputs.

Design invariants (per issue #338 plan):

  * Raw-vs-derived separation. The raw input list is never mutated; each derived
    row carries its own copy of provenance metadata.
  * Scope separation. Project-scope rows never leak into the operator view, and
    vice versa.
  * YoY math is only emitted when a prior-year row exists within the same group;
    no forward-fill or interpolation.
  * Comparability policy is owned by #336. This module only accepts rows whose
    ``comparability_status`` is exactly :data:`COMPARABILITY_COMPARABLE`, and
    refuses all other inputs for the benchmark hook (including ``None``).
  * No lower-tertiary consumption. Lower-tertiary field/project mapping is
    deferred to a separate contract issue.

The :class:`DisclosureRecord` shape defined here is a minimal local contract so
#338 can ship ahead of the #334 raw foundation. Once #334 lands, this module can
depend on the canonical type without changing its public API.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date
from typing import Any, TypeVar

from worldenergydata.cost.data_collection.disclosure_ingest_contract import (
    DisclosureRow,
    disclosure_business_key,
)
from worldenergydata.cost.data_collection.disclosure_revision_contract import (
    DisclosureRevision,
    revision_lineage_depths,
)

__all__ = [
    "COMPARABILITY_COMPARABLE",
    "SCOPE_OPERATOR",
    "SCOPE_PROJECT",
    "DisclosureBenchmarkResult",
    "DisclosureRecord",
    "OperatorCapexRow",
    "ProjectRevisionRow",
    "build_cost_disclosure_benchmark",
    "load_current_effective_disclosure_rows",
    "load_disclosure_revision_history",
    "load_operator_annual_capex_view",
    "load_project_cost_revision_view",
]


SCOPE_PROJECT = "project"
SCOPE_OPERATOR = "operator"

COMPARABILITY_COMPARABLE = "comparable"


@dataclass(frozen=True)
class DisclosureRecord:
    """Raw annual-disclosure row consumed by the derived views.

    This is a local contract for #338; once #334's canonical foundation lands,
    this module can accept that type interchangeably.
    """

    operator: str
    fiscal_year: int
    reported_capex_usd_mm: float
    scope: str
    project_name: str | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)
    comparability_status: str | None = None
    comparability_basis: str | None = None
    currency: str | None = None
    revision: DisclosureRevision | None = None

    def __post_init__(self) -> None:
        if self.revision is not None:
            object.__setattr__(
                self, "revision", DisclosureRevision.model_validate(self.revision)
            )


@dataclass
class ProjectRevisionRow:
    """Derived per-project annual capex + YoY revision."""

    operator: str
    project_name: str
    fiscal_year: int
    reported_capex_usd_mm: float
    yoy_delta_usd_mm: float | None
    yoy_delta_pct: float | None
    provenance: dict
    comparability_status: str | None
    revision: DisclosureRevision | None = None


@dataclass
class OperatorCapexRow:
    """Derived per-operator annual capex + YoY delta."""

    operator: str
    fiscal_year: int
    reported_capex_usd_mm: float
    yoy_delta_usd_mm: float | None
    yoy_delta_pct: float | None
    provenance: dict
    comparability_status: str | None
    revision: DisclosureRevision | None = None


@dataclass(frozen=True)
class DisclosureBenchmarkResult:
    """Outcome of the gated cost-vs-disclosure comparison."""

    operator: str
    project_name: str
    fiscal_year: int
    disclosed_capex_usd_mm: float
    predicted_capex_usd_mm: float
    absolute_delta_usd_mm: float
    pct_delta: float
    comparability_status: str


def _copy_provenance(src: Mapping[str, Any]) -> dict:
    return deepcopy(dict(src))


RecordT = TypeVar("RecordT", DisclosureRecord, DisclosureRow)


def _revision_business_key(row: RecordT) -> tuple:
    if isinstance(row, DisclosureRow):
        return disclosure_business_key(row)
    return (row.operator, row.fiscal_year, row.scope, row.project_name, row.currency)


def _revision_precedence(row: RecordT, depths: Mapping[str, int]) -> tuple:
    revision = row.revision
    # Source: issue 344 plan, current-effective precedence. Unknown dates sort first.
    return (
        depths[revision.version_id],
        revision.effective_date or date.min,
        revision.publication_date or date.min,
        revision.version_id,
    )


def load_disclosure_revision_history(
    records: Iterable[RecordT], *, logical_disclosure_key: str | None = None
) -> list[RecordT]:
    """Return all evidence, ordered by logical key then root-relative precedence.

    Exact version replays are collapsed; conflicting IDs or incomplete graphs
    raise ValueError. Without a key filter, legacy rows retain input order ahead
    of versioned groups. No missing identity or publication date is inferred.
    """
    rows = list(records)
    depths = revision_lineage_depths(rows, business_key=_revision_business_key)
    versions = {r.revision.version_id: r for r in rows if r.revision is not None}
    history = sorted(
        versions.values(),
        key=lambda r: (
            r.revision.logical_disclosure_key,
            _revision_precedence(r, depths),
        ),
    )
    if logical_disclosure_key is not None:
        return [
            r
            for r in history
            if r.revision.logical_disclosure_key == logical_disclosure_key
        ]
    return [r for r in rows if r.revision is None] + history


def load_current_effective_disclosure_rows(
    records: Iterable[RecordT],
) -> list[RecordT]:
    """Select one current row per complete logical lineage; preserve legacy rows.

    Precedence: lineage depth, effective date, publication date, lexical ID.
    Competing branches stay in history. Current means the supplied snapshot;
    this API does not infer an as-of date or treat legacy rows as originals.
    """
    history = load_disclosure_revision_history(records)
    selected: dict[str, RecordT] = {}
    for row in history:
        if row.revision is not None:
            selected[row.revision.logical_disclosure_key] = row
    return [r for r in history if r.revision is None] + list(selected.values())


def _yoy(current: float, prior: float | None) -> tuple[float | None, float | None]:
    if prior is None:
        return None, None
    delta = current - prior
    pct = delta / prior if prior != 0 else None
    return delta, pct


def load_project_cost_revision_view(
    records: Iterable[DisclosureRecord],
) -> list[ProjectRevisionRow]:
    """Build the project annual cost revision view.

    Groups by ``(operator, project_name)``, sorts by ``fiscal_year``, and emits
    a derived row per current logical version, carrying revision metadata.
    Differences use the previous observed fiscal year in the same group;
    missing years are not interpolated. Legacy rows retain existing behavior.

    Operator-scope rows and rows missing ``project_name`` are excluded — they
    belong to the operator view, never this one.
    """
    project_rows = [
        r
        for r in load_current_effective_disclosure_rows(records)
        if r.scope == SCOPE_PROJECT and r.project_name
    ]
    groups: dict[tuple[str, str], list[DisclosureRecord]] = {}
    for r in project_rows:
        groups.setdefault((r.operator, r.project_name), []).append(r)

    result: list[ProjectRevisionRow] = []
    for rows in groups.values():
        rows_sorted = sorted(rows, key=lambda x: x.fiscal_year)
        prior_capex: float | None = None
        for r in rows_sorted:
            delta, pct = _yoy(r.reported_capex_usd_mm, prior_capex)
            result.append(
                ProjectRevisionRow(
                    operator=r.operator,
                    project_name=r.project_name,
                    fiscal_year=r.fiscal_year,
                    reported_capex_usd_mm=r.reported_capex_usd_mm,
                    yoy_delta_usd_mm=delta,
                    yoy_delta_pct=pct,
                    provenance=_copy_provenance(r.provenance),
                    comparability_status=r.comparability_status,
                    revision=r.revision,
                )
            )
            prior_capex = r.reported_capex_usd_mm
    return result


def load_operator_annual_capex_view(
    records: Iterable[DisclosureRecord],
) -> list[OperatorCapexRow]:
    """Build the operator annual capex view.

    Groups by ``operator``, sorts by ``fiscal_year``, and emits a derived row
    per current logical version with differences computed within-group only.
    Revision metadata is retained. Missing years are not interpolated; legacy
    rows retain existing behavior.

    Project-scope rows are excluded.
    """
    operator_rows = [
        r
        for r in load_current_effective_disclosure_rows(records)
        if r.scope == SCOPE_OPERATOR
    ]
    groups: dict[str, list[DisclosureRecord]] = {}
    for r in operator_rows:
        groups.setdefault(r.operator, []).append(r)

    result: list[OperatorCapexRow] = []
    for rows in groups.values():
        rows_sorted = sorted(rows, key=lambda x: x.fiscal_year)
        prior_capex: float | None = None
        for r in rows_sorted:
            delta, pct = _yoy(r.reported_capex_usd_mm, prior_capex)
            result.append(
                OperatorCapexRow(
                    operator=r.operator,
                    fiscal_year=r.fiscal_year,
                    reported_capex_usd_mm=r.reported_capex_usd_mm,
                    yoy_delta_usd_mm=delta,
                    yoy_delta_pct=pct,
                    provenance=_copy_provenance(r.provenance),
                    comparability_status=r.comparability_status,
                    revision=r.revision,
                )
            )
            prior_capex = r.reported_capex_usd_mm
    return result


def build_cost_disclosure_benchmark(
    project_revision_view: Iterable[ProjectRevisionRow],
    predictor_cost_usd_mm: float,
    *,
    operator: str,
    project_name: str,
    fiscal_year: int | None = None,
) -> DisclosureBenchmarkResult | None:
    """Compare a predictor output against the latest comparable disclosed capex.

    Parameters
    ----------
    project_revision_view
        Output of :func:`load_project_cost_revision_view`.
    predictor_cost_usd_mm
        Cost point estimate from an upstream predictor (e.g. ``CostPredictor``).
        This function does not call the predictor — it only accepts its scalar
        output, keeping the hook thin and non-intrusive on predictor semantics.
    operator, project_name
        Scope filter for the comparison.
    fiscal_year
        Optional — if provided, compare against the exact fiscal year rather
        than the latest available.

    Returns
    -------
    DisclosureBenchmarkResult | None
        ``None`` if no row matches the scope *or* no matching row has been
        flagged :data:`COMPARABILITY_COMPARABLE` under #336's outputs. Refusing
        rather than inferring keeps comparability policy owned by #336.
    """
    candidates = [
        r
        for r in project_revision_view
        if r.operator == operator
        and r.project_name == project_name
        and r.comparability_status == COMPARABILITY_COMPARABLE
    ]
    if fiscal_year is not None:
        candidates = [r for r in candidates if r.fiscal_year == fiscal_year]
    if not candidates:
        return None

    latest = max(candidates, key=lambda r: r.fiscal_year)
    abs_delta = predictor_cost_usd_mm - latest.reported_capex_usd_mm
    pct_delta = (
        abs_delta / latest.reported_capex_usd_mm
        if latest.reported_capex_usd_mm
        else 0.0
    )
    return DisclosureBenchmarkResult(
        operator=operator,
        project_name=project_name,
        fiscal_year=latest.fiscal_year,
        disclosed_capex_usd_mm=latest.reported_capex_usd_mm,
        predicted_capex_usd_mm=predictor_cost_usd_mm,
        absolute_delta_usd_mm=abs_delta,
        pct_delta=pct_delta,
        comparability_status=latest.comparability_status,
    )
