"""Exact, basis-preserving comparisons; no default engineering tolerances."""

from dataclasses import asdict, dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Basis:
    currency: str | None
    price_basis: str | None
    basis_year: str | None
    ownership: str | None
    scope: str | None
    capex_basis: str | None
    unit: str | None
    period: str | None
    vintage: str | None


@dataclass(frozen=True)
class Interval:
    low: Decimal
    high: Decimal

    def __post_init__(self):
        if not all(
            isinstance(v, Decimal) and v.is_finite() for v in (self.low, self.high)
        ):
            raise ValueError("finite Decimal bounds required")
        if self.low > self.high:
            raise ValueError("interval low exceeds high")


@dataclass(frozen=True)
class CostValue:
    project: str
    component: str
    basis: Basis
    amount: Interval
    provenance: str
    source: str

    def __post_init__(self):
        if self.provenance not in {
            "disclosed",
            "mapped",
            "allocated",
            "modeled",
            "workbook_assumption",
        }:
            raise ValueError("unknown provenance")
        if not self.source.strip():
            raise ValueError("source required")


CLASSIFICATIONS = {
    "scope",
    "basis",
    "timing",
    "currency",
    "assumption vintage",
    "missing evidence",
    "model error",
}


def compare(workbook, comparison, threshold, classification=None, evidence=""):
    """Compare closed intervals only on fully known, identical bases.

    Source: issue 1044 approved plan, task 6: [Wlo-Chi, Whi-Clo].
    Materiality uses the caller's absolute threshold in the stated native unit;
    no proposed plan threshold becomes an engineering default.
    """
    if classification is not None and classification not in CLASSIFICATIONS:
        raise ValueError("unknown variance classification")
    if threshold is not None and (
        not isinstance(threshold, Decimal) or not threshold.is_finite() or threshold < 0
    ):
        raise ValueError("threshold must be a finite nonnegative Decimal")
    result = {
        "project": workbook.project,
        "component": workbook.component,
        "basis": asdict(workbook.basis),
        "workbook_low": str(workbook.amount.low),
        "workbook_high": str(workbook.amount.high),
        "comparison_low": str(comparison.amount.low),
        "comparison_high": str(comparison.amount.high),
        "comparison_provenance": comparison.provenance,
        "workbook_source": workbook.source,
        "comparison_source": comparison.source,
        "variance_low": None,
        "variance_high": None,
        "status": "NOT_EVALUATED",
        "materiality": "NOT_EVALUATED",
        "classification": classification,
        "explanation_evidence": evidence,
        "threshold": str(threshold) if threshold is not None else None,
    }
    fields = asdict(workbook.basis)
    if not all(v is not None and str(v).strip() for v in fields.values()):
        return {**result, "reason": "incomplete workbook basis"}
    if (
        workbook.basis != comparison.basis
        or workbook.project != comparison.project
        or workbook.component != comparison.component
    ):
        return {**result, "reason": "incompatible project, component or basis"}
    variance = Interval(
        workbook.amount.low - comparison.amount.high,
        workbook.amount.high - comparison.amount.low,
    )
    result.update(variance_low=str(variance.low), variance_high=str(variance.high))
    if threshold is None:
        return {**result, "reason": "materiality policy required"}
    if variance.low >= -threshold and variance.high <= threshold:
        return {**result, "materiality": "immaterial", "status": "WITHIN_THRESHOLD"}
    materiality = (
        "material"
        if variance.high < -threshold or variance.low > threshold
        else "uncertain_materiality"
    )
    explained = classification not in {None, "missing evidence"} and bool(
        evidence.strip()
    )
    return {
        **result,
        "materiality": materiality,
        "status": "EXPLAINED" if explained else "UNRESOLVED",
    }
