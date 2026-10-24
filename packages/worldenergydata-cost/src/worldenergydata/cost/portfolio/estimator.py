"""Single physical-driver CAPEX models with separate project-group partitions.

OLS source: NIST/SEMATECH e-Handbook (2003), section 4.4.3.1,
https://www.itl.nist.gov/div898/handbook/pmd/section4/pmd431.htm
Conformal source: A Gentle Introduction to Conformal Prediction and
Distribution-Free Uncertainty Quantification (2021), section 1.1,
https://arxiv.org/html/2107.07511v6

Linear and quadratic degrees are model definitions, not empirical constants.
Every acceptance limit is supplied by the caller with a policy source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_CEILING, Decimal

from .accounting import Basis, Evidence, Interval

ZERO = Decimal(0)
ONE = Decimal(1)


@dataclass(frozen=True)
class EstimateRequest:
    project: str
    group: str
    architecture: str
    region: str
    basis: Basis
    driver_name: str
    driver_unit: str
    driver: Decimal | None
    as_of: date
    feature_evidence: Evidence


@dataclass(frozen=True)
class Comparable:
    project: str
    group: str
    architecture: str
    region: str
    basis: Basis
    driver_name: str
    driver_unit: str
    driver: Decimal | None
    features_on: date
    target: Interval | None
    evidence: Evidence
    synthetic: bool


@dataclass(frozen=True)
class ValidationPolicy:
    alpha: Decimal
    min_training_groups: int
    min_validation_groups: int
    max_mean_ape: Decimal
    min_coverage: Decimal
    source: str

    def __post_init__(self):
        numbers = (self.alpha, self.max_mean_ape, self.min_coverage)
        if not all(isinstance(x, Decimal) and x.is_finite() for x in numbers):
            raise ValueError("finite Decimal policy inputs required")
        if not ZERO < self.alpha < ONE or self.max_mean_ape < ZERO:
            raise ValueError("invalid error policy")
        if not ZERO <= self.min_coverage <= ONE or not self.source.strip():
            raise ValueError("coverage and policy source required")
        if (
            not isinstance(self.min_training_groups, int)
            or not isinstance(self.min_validation_groups, int)
            or min(self.min_training_groups, self.min_validation_groups) < 1
        ):
            raise ValueError("positive group counts required")


@dataclass(frozen=True)
class Estimate:
    status: str
    reason: str
    request: EstimateRequest
    policy: ValidationPolicy
    comparables: tuple[str, ...]
    excluded: dict[str, str]
    partitions: dict[str, tuple[str, ...]]
    inputs: tuple[Comparable, ...] = ()
    method: str | None = None
    coefficients: tuple[Decimal, ...] = ()
    candidate_mae: dict[str, Decimal | None] = field(default_factory=dict)
    selection_folds: tuple[dict, ...] = ()
    calibration_errors: tuple[Decimal, ...] = ()
    validation: tuple[dict, ...] = ()
    validation_mae: Decimal | None = None
    validation_mean_ape: Decimal | None = None
    validation_coverage: Decimal | None = None
    by_region: dict[str, dict] = field(default_factory=dict)
    point: Decimal | None = None
    interval: Interval | None = None


def _valid_driver(value):
    return isinstance(value, Decimal) and value.is_finite() and value > ZERO


def _eligibility(row: Comparable, request: EstimateRequest) -> str:
    if row.project == request.project or row.group == request.group:
        return "target_group"
    if row.synthetic:
        return "synthetic"
    if row.evidence.derivation != "disclosed":
        return "not_disclosed"
    if not row.basis.known or not request.basis.known or row.basis != request.basis:
        return "basis"
    if row.architecture != request.architecture:
        return "architecture"
    if (row.driver_name, row.driver_unit) != (request.driver_name, request.driver_unit):
        return "driver"
    if row.features_on > min(request.as_of, row.evidence.available_on):
        return "future_features"
    if row.evidence.available_on > request.as_of:
        return "future_target"
    if row.target is None or row.target.low != row.target.high:
        return "nonpoint_target"
    if row.target.low <= ZERO:
        return "nonpositive_target"
    if not _valid_driver(row.driver):
        return "missing_driver"
    return ""


def _fit(rows, degree):
    """Solve the OLS normal equations with pivoting (NIST, 2003, 4.4.3.1).

    Centering x keeps the small one-driver design well scaled. The returned
    coefficient tuple starts with the centering offset, then polynomial terms.
    Rank-deficient designs yield no candidate; no fallback coefficient is used.
    """
    if len({r.driver for r in rows}) <= degree:
        return None
    center = sum((r.driver for r in rows), ZERO) / len(rows)
    xs = [r.driver - center for r in rows]

    # The exponent zero is the intercept definition; Decimal disallows 0**0.
    def power(x, p):
        return ONE if p == 0 else x**p

    size = degree + 1
    matrix = [
        [sum((power(x, i + j) for x in xs), ZERO) for j in range(size)]
        + [sum((power(x, i) * r.target.low for x, r in zip(xs, rows)), ZERO)]
        for i in range(size)
    ]
    for col in range(size):
        pivot = max(range(col, size), key=lambda i: abs(matrix[i][col]))
        if not matrix[pivot][col]:
            return None
        matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
        divisor = matrix[col][col]
        matrix[col] = [value / divisor for value in matrix[col]]
        for row in range(size):
            if row == col:
                continue
            factor = matrix[row][col]
            matrix[row] = [a - factor * b for a, b in zip(matrix[row], matrix[col])]
    return (center, *(matrix[i][-1] for i in range(size)))


def _predict(coefficients, driver):
    centered = driver - coefficients[0]
    result = ZERO
    for coefficient in reversed(coefficients[1:]):
        result = result * centered + coefficient
    return result


def _select(training):
    groups = sorted({r.group for r in training})
    folds = tuple(
        {"train_groups": tuple(g for g in groups if g != held), "test_groups": (held,)}
        for held in groups
    )
    errors = {}
    for method, degree in (("linear", 1), ("quadratic", 2)):
        group_errors = []
        for held in groups:
            fitted = _fit([r for r in training if r.group != held], degree)
            if fitted is None:
                break
            test = [r for r in training if r.group == held]
            group_errors.append(
                sum(
                    (abs(_predict(fitted, r.driver) - r.target.low) for r in test), ZERO
                )
                / len(test)
            )
        errors[method] = (
            sum(group_errors, ZERO) / len(groups)
            if len(group_errors) == len(groups)
            else None
        )
    available = [method for method in errors if errors[method] is not None]
    # Stable insertion order retains the simpler linear model on an exact tie.
    selected = min(available, key=lambda method: errors[method]) if available else None
    return selected, errors, folds


def estimate(
    request: EstimateRequest,
    records: tuple[Comparable, ...],
    training_groups: tuple[str, ...],
    calibration_groups: tuple[str, ...],
    validation_groups: tuple[str, ...],
    policy: ValidationPolicy,
) -> Estimate:
    """Select inside training, calibrate separately, then gate on untouched groups.

    Partitions must be declared before observing outcomes. Group maxima calibrate
    whole-project uncertainty. Coverage interpretation requires exchangeable
    groups; real portfolio validation and sampling review remain prerequisites.
    """
    if not all(
        x.strip()
        for x in (
            request.project,
            request.group,
            request.architecture,
            request.region,
            request.driver_name,
            request.driver_unit,
        )
    ):
        raise ValueError("target identities and physical driver metadata required")
    if request.feature_evidence.available_on > request.as_of:
        raise ValueError("future target features")
    if request.feature_evidence.derivation not in {"disclosed", "award_derived"}:
        raise ValueError("observed physical target features required")
    partitions = {
        "training": training_groups,
        "calibration": calibration_groups,
        "validation": validation_groups,
    }
    flattened = [g for part in partitions.values() for g in part]
    if len(flattened) != len(set(flattened)) or request.group in flattened:
        raise ValueError("overlapping or duplicate partition groups")
    if len({r.project for r in records}) != len(records):
        raise ValueError("duplicate project; supply one target vintage per project")
    eligible, excluded = [], {}
    for row in sorted(records, key=lambda r: r.project):
        if not row.project.strip() or not row.group.strip() or not row.region.strip():
            raise ValueError("comparable project, group and region required")
        reason = _eligibility(row, request)
        if not reason and row.group not in flattened:
            reason = "unassigned_partition"
        if reason:
            excluded[row.project] = reason
        else:
            eligible.append(row)
    common = {
        "request": request,
        "policy": policy,
        "comparables": tuple(r.project for r in eligible),
        "excluded": excluded,
        "partitions": {k: tuple(sorted(v)) for k, v in partitions.items()},
        "inputs": tuple(eligible),
    }

    def unavailable(reason, **diagnostics):
        return Estimate("NOT_EVALUATED", reason, **common, **diagnostics)

    if not _valid_driver(request.driver):
        return unavailable("missing_driver")
    train, cal, valid = (
        [r for r in eligible if r.group in groups] for groups in partitions.values()
    )
    if len({r.group for r in train}) < policy.min_training_groups:
        return unavailable("insufficient_training")
    if len({r.group for r in valid}) < policy.min_validation_groups:
        return unavailable("insufficient_validation")
    if not train:
        return unavailable("insufficient_training")
    if (
        not min(r.driver for r in train)
        <= request.driver
        <= max(r.driver for r in train)
    ):
        return unavailable("extrapolation")
    method, errors, folds = _select(train)
    diagnostics = {"method": method, "candidate_mae": errors, "selection_folds": folds}
    if method is None:
        return unavailable("rank_deficient", **diagnostics)
    coefficients = _fit(train, {"linear": 1, "quadratic": 2}[method])
    diagnostics["coefficients"] = coefficients
    group_scores = [
        max(
            abs(r.target.low - _predict(coefficients, r.driver))
            for r in cal
            if r.group == group
        )
        for group in sorted({r.group for r in cal})
    ]
    scores = tuple(sorted(group_scores))
    diagnostics["calibration_errors"] = scores
    # Finite-sample correction: conformal introduction (2021), section 1.1.
    rank = int(
        ((len(scores) + 1) * (ONE - policy.alpha)).to_integral_value(
            rounding=ROUND_CEILING
        )
    )
    if not scores or rank > len(scores):
        return unavailable("insufficient_calibration", **diagnostics)
    radius = scores[rank - 1]

    def bounds(point):
        # CAPEX is nonnegative by the input contract; clip the set, not the fit.
        return Interval(max(ZERO, point - radius), point + radius)

    point = _predict(coefficients, request.driver)
    if point < ZERO or any(
        _predict(coefficients, r.driver) < ZERO for r in (*cal, *valid)
    ):
        return unavailable("negative_prediction", **diagnostics)
    validation = []
    for row in valid:
        predicted = _predict(coefficients, row.driver)
        interval = bounds(predicted)
        error = abs(row.target.low - predicted)
        validation.append(
            {
                "project": row.project,
                "group": row.group,
                "region": row.region,
                "observed": row.target.low,
                "predicted": predicted,
                "interval": interval,
                "error": error,
                "ape": error / row.target.low,
                "covered": interval.low <= row.target.low <= interval.high,
            }
        )
    diagnostics["validation"] = tuple(validation)
    groups = sorted({r["group"] for r in validation})
    grouped = [[r for r in validation if r["group"] == group] for group in groups]
    mae = sum(
        (sum((r["error"] for r in rows), ZERO) / len(rows) for rows in grouped), ZERO
    ) / len(groups)
    ape = sum(
        (sum((r["ape"] for r in rows), ZERO) / len(rows) for rows in grouped), ZERO
    ) / len(groups)
    coverage = Decimal(sum(all(r["covered"] for r in rows) for rows in grouped)) / len(
        groups
    )
    diagnostics.update(
        validation_mae=mae, validation_mean_ape=ape, validation_coverage=coverage
    )
    diagnostics["by_region"] = {
        region: {
            "count": len(rows),
            "mae": sum((r["error"] for r in rows), ZERO) / len(rows),
            "coverage": Decimal(sum(r["covered"] for r in rows)) / len(rows),
        }
        for region in sorted({r["region"] for r in validation})
        for rows in [[r for r in validation if r["region"] == region]]
    }
    if ape > policy.max_mean_ape or coverage < policy.min_coverage:
        return unavailable("validation_failed", **diagnostics)
    return Estimate(
        "modeled",
        "passed_supplied_policy",
        **common,
        **diagnostics,
        point=point,
        interval=bounds(point),
    )
