"""Interval comparison without implicit normalization or midpoint substitution.

Equations: approved reconciliation plan (2026), Planned Tasks 6 and Pseudocode.
W-C=[W.low-C.high,W.high-C.low]. The policy is an input, never a default.
Interval subtraction: Shape Interrogation for Computer Aided Design and
Manufacturing, online edition (December 2009), section 4.7, equation (4.43):
https://web.mit.edu/hyperbook/
"""

from dataclasses import asdict
from decimal import localcontext

from .models import Interval, MaterialityPolicy, Observation, Result

CLASSIFICATIONS = {
    "scope",
    "basis",
    "timing",
    "currency",
    "assumption_vintage",
    "missing_evidence",
    "model_error",
}


def reconcile(
    workbook: Observation,
    comparison: Observation,
    policy: MaterialityPolicy | None = None,
    classification: str = "missing_evidence",
    evidence: str = "",
) -> Result:
    if workbook.provenance != "workbook_assumption":
        raise ValueError("reference provenance must remain workbook_assumption")
    if classification not in CLASSIFICATIONS:
        raise ValueError("unsupported variance classification")
    left, right = asdict(workbook.basis), asdict(comparison.basis)
    unknown = {"", "unknown", "not_evaluated", "unavailable"}
    mismatch = [
        key
        for key in left
        if left[key].strip().lower() in unknown or left[key] != right[key]
    ]
    if mismatch:
        return Result(
            "NOT_EVALUATED", "incompatible or unknown: " + ", ".join(mismatch)
        )
    w, c = workbook.amount, comparison.amount
    if not w.closed or not c.closed:
        return Result("NOT_EVALUATED", "open or missing interval bounds")
    # Precision is serialization policy, not a financial assumption. Avoid the
    # caller's Decimal context rounding the subtraction of workbook decimals.
    with localcontext() as context:
        context.prec = 80
        variance = Interval(w.low - c.high, w.high - c.low)
        if policy is None or not policy.approved:
            return Result(
                "NOT_EVALUATED", "approved materiality policy unavailable", variance
            )
        threshold = max(policy.absolute, policy.relative * max(abs(w.low), abs(w.high)))
    negative_threshold = threshold.copy_negate()
    if variance.low >= negative_threshold and variance.high <= threshold:
        materiality = "immaterial"
    elif variance.high < negative_threshold or variance.low > threshold:
        materiality = "material"
    else:
        materiality = "uncertain_materiality"
    explained = bool(evidence.strip()) and classification not in {
        "missing_evidence",
        "model_error",
    }
    status = "PASS" if materiality == "immaterial" or explained else "FAIL"
    return Result(
        status,
        "compatible basis",
        variance,
        materiality,
        threshold,
        classification,
        evidence,
    )
