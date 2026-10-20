"""Project-held-out CAPEX estimation, isolated from the legacy predictor.

Methods: NIST/SEMATECH e-Handbook (2012), sections 4.4.3.1 and 4.4.5.2;
Distribution-Free Predictive Inference For Regression (2017), arXiv:1604.04173v2,
section 2.2. Application limits are required inputs, not literature constants.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import date

import numpy as np

from .capex_estimator_schema import EstimatorPolicy, FeatureSnapshot, TrainingRecord
from .estimator_dataset import select_cohort


@dataclass
class Estimate:
    project_id: str
    status: str
    reason: str
    basis: dict
    model_vintage: str
    model_hash: str
    comparables: tuple[str, ...]
    feature_names: tuple[str, ...]
    missing_features: tuple[str, ...]
    feature_completeness: float
    exclusions: tuple[tuple[str, str], ...]
    policy: dict
    estimate: float | None = None
    lower: float | None = None
    upper: float | None = None
    method: str | None = None
    selection: dict = field(default_factory=dict)
    validation: dict = field(default_factory=dict)
    backtests: list[dict] = field(default_factory=list)
    comparable_evidence: list[dict] = field(default_factory=list)
    fit_groups: list[str] = field(default_factory=list)
    calibration_groups: list[str] = field(default_factory=list)
    model_parameters: dict = field(default_factory=dict)


def conformal_radius(residuals, alpha):
    """Split conformal rank, sec. 2.2, arXiv:1604.04173v2 (2017).

    k=ceil((m+1)(1-alpha)); k>m implies an unbounded interval, never a
    substituted empirical maximum. Residuals are absolute log-cost errors.
    """
    if not 0 < alpha < 1 or not residuals:
        raise ValueError("invalid calibration inputs")
    values = np.asarray(residuals, dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("invalid calibration residuals")
    rank = math.ceil((len(values) + 1) * (1 - alpha))
    if rank > len(values):
        raise ValueError("insufficient calibration projects for finite interval")
    return float(np.sort(values)[rank - 1])


def _features(snapshots, names):
    return np.array([[s.features[k].value for k in names] for s in snapshots])


def _design(x, degree):
    # Polynomial definition, not a calibrated coefficient. OLS: NIST sec. 4.4.3.1.
    columns = [np.ones((len(x), 1)), x]
    if degree == 2:
        columns.append(x**2)
    return np.hstack(columns)


def _fit(rows, names, degree, minimum):
    if len(rows) < minimum:
        raise ValueError("insufficient training projects")
    x = _features([r.snapshot for r in rows], names)
    mean, scale = x.mean(axis=0), x.std(axis=0)
    if (scale == 0).any():
        raise ValueError("no feature variation")
    design = _design((x - mean) / scale, degree)
    # Full column rank is algebraically required to identify the parameters.
    if np.linalg.matrix_rank(design) < design.shape[1]:
        raise ValueError("unidentifiable model")
    beta = np.linalg.lstsq(design, np.log([r.amount for r in rows]), rcond=None)[0]
    return mean, scale, beta, degree


def _predict_log(model, snapshots, names):
    mean, scale, beta, degree = model
    return _design((_features(snapshots, names) - mean) / scale, degree) @ beta


def _select(rows, names, policy):
    """Inner leave-one-project-out selection uses proper training only.

    One record per canonical group has already been enforced by select_cohort.
    Compare mean absolute log error; an exact tie retains the linear baseline.
    The outer fold never participates in this choice or in calibration.
    """
    if len(rows) <= policy.min_training_projects:
        raise ValueError("insufficient independent projects for inner model selection")
    scores = {}
    for degree in (1, 2):
        errors = []
        try:
            for i, row in enumerate(rows):
                model = _fit(
                    rows[:i] + rows[i + 1 :],
                    names,
                    degree,
                    policy.min_training_projects,
                )
                prediction = _predict_log(model, [row.snapshot], names)[0]
                errors.append(abs(math.log(row.amount) - prediction))
            scores[degree] = float(np.mean(errors))
        except ValueError:
            scores[degree] = math.inf
    degree = min(scores, key=scores.get)
    if not math.isfinite(scores[degree]):
        raise ValueError("insufficient independent projects for inner model selection")
    return degree, {str(k): v if math.isfinite(v) else None for k, v in scores.items()}


def _procedure(rows, target, names, policy, *, retrospective=False):
    """Outcome-independent hash partition; salt shall be fixed before evaluation.

    Split-conformal marginal coverage requires exchangeable projects. A hash
    split is reproducible but cannot establish exchangeability of supplied data.
    """
    ordered = sorted(
        rows,
        key=lambda r: hashlib.sha256(
            (policy.split_salt + "\0" + r.snapshot.validation_group_id).encode()
        ).hexdigest(),
    )
    calibration = ordered[: policy.calibration_projects]
    proper = ordered[policy.calibration_projects :]
    if len(calibration) != policy.calibration_projects:
        raise ValueError("insufficient calibration projects")
    if not proper:
        raise ValueError("insufficient training projects")
    x = _features([r.snapshot for r in proper], names)
    requested = _features([target], names)[0]
    outside = (requested < x.min(axis=0)) | (requested > x.max(axis=0))
    extrapolation_features = [name for name, flag in zip(names, outside) if flag]
    if extrapolation_features and not retrospective:
        raise ValueError(
            "target requires extrapolation beyond proper-training feature range"
        )
    degree, scores = _select(proper, names, policy)
    model = _fit(proper, names, degree, policy.min_training_projects)
    predicted = _predict_log(model, [r.snapshot for r in calibration], names)
    residuals = [abs(math.log(r.amount) - p) for r, p in zip(calibration, predicted)]
    radius = conformal_radius(residuals, policy.alpha)
    center = float(_predict_log(model, [target], names)[0])
    values = [math.exp(center), math.exp(center - radius), math.exp(center + radius)]
    if not all(math.isfinite(v) and v > 0 for v in values):
        raise ValueError("non-finite or underflowed prediction")
    return dict(
        estimate=values[0],
        lower=values[1],
        upper=values[2],
        method="log_linear" if degree == 1 else "log_quadratic",
        selection=scores,
        fit_groups=[r.snapshot.validation_group_id for r in proper],
        calibration_groups=[r.snapshot.validation_group_id for r in calibration],
        extrapolation_features=extrapolation_features,
        model_parameters=dict(
            feature_center=model[0].tolist(),
            feature_scale=model[1].tolist(),
            coefficients=model[2].tolist(),
            degree=model[3],
        ),
    )


def _metrics(backtests):
    successes = [b for b in backtests if b["status"] == "modeled"]
    if not successes:
        return dict(
            count=0, failures=len(backtests), median_ape=None, coverage=None, errors=[]
        )
    errors = [abs(b["estimate"] - b["observed"]) / b["observed"] for b in successes]
    coverage = [b["lower"] <= b["observed"] <= b["upper"] for b in successes]
    return dict(
        count=len(successes),
        failures=len(backtests) - len(successes),
        median_ape=float(np.median(errors)),
        coverage=float(np.mean(coverage)),
        errors=errors,
    )


class CapexEstimator:
    """No corpus or policy is loaded implicitly; all evidence is caller-supplied."""

    def __init__(
        self, records: list[TrainingRecord], policy: EstimatorPolicy, cutoff: date
    ):
        # Round-trip to detach mutable feature dictionaries and validate copies.
        self.records = [TrainingRecord.model_validate(r.model_dump()) for r in records]
        self.policy = EstimatorPolicy.model_validate(policy.model_dump())
        self.cutoff = cutoff

    def predict(self, target: FeatureSnapshot) -> Estimate:
        target = FeatureSnapshot.model_validate(target.model_dump())
        cohort = select_cohort(self.records, target, self.cutoff)
        packet = dict(
            algorithm="capex-split-conformal-v1",
            cutoff=self.cutoff.isoformat(),
            records=sorted(
                [r.model_dump(mode="json") for r in self.records],
                key=lambda r: json.dumps(r, sort_keys=True),
            ),
            target=target.model_dump(mode="json"),
            policy=self.policy.model_dump(),
        )
        digest = hashlib.sha256(
            json.dumps(packet, sort_keys=True, allow_nan=False).encode()
        ).hexdigest()
        result = Estimate(
            target.project_id,
            "NOT_EVALUATED",
            "",
            target.basis.model_dump(),
            self.cutoff.isoformat(),
            digest,
            tuple(r.snapshot.project_id for r in cohort.records),
            cohort.feature_names,
            cohort.missing_features,
            len(cohort.feature_names) / len(target.features) if target.features else 0,
            cohort.exclusions,
            self.policy.model_dump(),
        )
        result.comparable_evidence = [r.model_dump(mode="json") for r in cohort.records]
        try:
            self._evaluate(result, target, list(cohort.records), cohort.feature_names)
        except (ValueError, OverflowError, np.linalg.LinAlgError) as error:
            result.reason = str(error)
        return result

    def _evaluate(self, result, target, rows, names):
        if not names or not rows:
            raise ValueError("insufficient comparable evidence or available features")
        for i, row in enumerate(rows):
            fold = dict(
                held_out=row.snapshot.validation_group_id,
                project_id=row.snapshot.project_id,
                region=row.snapshot.region,
                architecture=row.snapshot.architecture,
                observed=row.amount,
            )
            try:
                fold.update(
                    _procedure(
                        rows[:i] + rows[i + 1 :],
                        row.snapshot,
                        names,
                        self.policy,
                        retrospective=True,
                    )
                )
                fold["status"] = "modeled"
            except (ValueError, OverflowError, np.linalg.LinAlgError) as error:
                fold.update(status="NOT_EVALUATED", reason=str(error))
            result.backtests.append(fold)
        groups = {"overall": result.backtests}
        for key in ("region", "architecture"):
            for value in sorted({b[key] for b in result.backtests}):
                groups[f"{key}:{value}"] = [
                    b for b in result.backtests if b[key] == value
                ]
        result.validation = {name: _metrics(folds) for name, folds in groups.items()}
        overall = result.validation["overall"]
        if overall["failures"]:
            reason = next(
                b["reason"] for b in result.backtests if b["status"] != "modeled"
            )
            raise ValueError(f"outer validation failure: {reason}")
        if (
            overall["count"] < self.policy.min_backtests
            or overall["median_ape"] > self.policy.max_median_ape
            or overall["coverage"] < self.policy.min_coverage
        ):
            raise ValueError(
                "outer validation does not meet supplied application criteria"
            )
        prediction = _procedure(rows, target, names, self.policy)
        for key in (
            "estimate",
            "lower",
            "upper",
            "method",
            "selection",
            "fit_groups",
            "calibration_groups",
            "model_parameters",
        ):
            setattr(result, key, prediction[key])
        result.status = "modeled"
        result.reason = "passed supplied application criteria; exchangeability remains an assumption"


def reconcile(direct, components):
    """Caller asserts disjoint, exhaustive component scopes and identical bases.

    Interval arithmetic: B=[sum(lo),sum(hi)], variance=Dpoint-sum(Bpoint).
    No midpoint substitution or independence assumption is used. Sum bounds
    are an envelope, not a joint prediction interval with stated coverage.
    """
    for interval in [direct, *components]:
        if interval is not None and (
            len(interval) != 3
            or not all(math.isfinite(v) for v in interval)
            or not 0 <= interval[1] <= interval[0] <= interval[2]
        ):
            raise ValueError("invalid estimate interval")
    if direct is None or not components or any(c is None for c in components):
        return dict(
            bottom_up=None,
            lower=None,
            upper=None,
            variance=None,
            relation="indeterminate",
        )
    point, low, high = (sum(c[i] for c in components) for i in range(3))
    relation = (
        "direct_above"
        if direct[1] > high
        else "bottom_up_above" if low > direct[2] else "overlap"
    )
    return dict(
        bottom_up=point,
        lower=low,
        upper=high,
        variance=direct[0] - point,
        relation=relation,
    )


def reconcile_estimates(
    direct: Estimate, components: dict[str, Estimate], required_scopes: set[str]
):
    """Reconcile exhaustive caller-declared disjoint scopes with basis checks.

    Required scopes shall come from the upstream requirements map. Their
    physical disjointness cannot be inferred from names. Unavailable estimates
    or incomplete coverage yield indeterminate rather than a partial total.
    """
    if set(components) != required_scopes or not required_scopes:
        return reconcile(None, [])
    common = {k: v for k, v in direct.basis.items() if k != "scope_basis"}
    for scope, component in components.items():
        if component.project_id != direct.project_id:
            raise ValueError("component belongs to a different project")
        if component.basis["scope_basis"] != scope:
            raise ValueError("component scope does not match required scope")
        if {k: v for k, v in component.basis.items() if k != "scope_basis"} != common:
            raise ValueError("component has incompatible cost basis")

    def interval(result):
        if result.status != "modeled":
            return None
        if any(v is None for v in (result.estimate, result.lower, result.upper)):
            return None
        return result.estimate, result.lower, result.upper

    return reconcile(interval(direct), [interval(c) for c in components.values()])


def render_report(
    results, *, revision: str, issued_on: date, reconciliations=(), prior_revisions=()
):
    """Generate portable HTML from calculation results; no files written implicitly."""
    from html import escape

    def table(rows, headers):
        head = "".join(f"<th>{escape(h)}</th>" for h in headers)
        body = "".join(
            "<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in row) + "</tr>"
            for row in rows
        )
        return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

    def number(value):
        if value is None:
            return "Not Evaluated"
        if 0 < value < 0.1:
            return "<0.1"
        if -0.1 < value < 0:
            return ">-0.1"
        return f"{value:.1f}"

    predictions, backtests, details = [], [], []
    for result in results:
        predictions.append(
            [
                result.project_id,
                result.status,
                number(result.estimate),
                number(result.lower),
                number(result.upper),
                result.reason,
            ]
        )
        for fold in result.backtests:
            backtests.append(
                [
                    fold["project_id"],
                    fold["status"],
                    number(fold["observed"]),
                    number(fold.get("estimate")),
                    fold.get("reason", ""),
                ]
            )

        # Raw diagnostics retain full numeric precision for machine consumers;
        # the human-facing report rounds all float values to one decimal place.
        def rounded(value, key=""):
            if isinstance(value, float):
                if key in {
                    "alpha",
                    "median_ape",
                    "max_median_ape",
                    "coverage",
                    "min_coverage",
                    "feature_completeness",
                    "errors",
                }:
                    return f"{value * 100:.1f}%"
                return number(value) if 0 < abs(value) < 0.1 else round(value, 1)
            if isinstance(value, dict):
                return {k: rounded(v, k) for k, v in value.items()}
            if isinstance(value, (list, tuple)):
                return [rounded(v, key) for v in value]
            return value

        details.append(
            "<pre>"
            + escape(json.dumps(rounded(asdict(result)), sort_keys=True, indent=2))
            + "</pre>"
        )
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        "<title>CAPEX estimator analysis</title><body><h1>CAPEX estimator analysis</h1>"
        "<h2>Summary</h2><p>Modeled estimates are distinct from observed disclosures. "
        "No public-project qualification is implied by this report.</p><h2>Revision history</h2>"
        + table(
            [
                *prior_revisions,
                [
                    revision,
                    issued_on.isoformat(),
                    "Estimator results issued from supplied evidence and criteria",
                ],
            ],
            ["Revision", "Date", "Change and reason"],
        )
        + "<h2>Predictions</h2>"
        + table(
            predictions,
            [
                "Project",
                "Status",
                "Estimate (currency million)",
                "Lower (currency million)",
                "Upper (currency million)",
                "Criterion / limitation",
            ],
        )
        + "<h2>Known-project backtests</h2>"
        + table(
            backtests,
            [
                "Project",
                "Status",
                "Observed (currency million)",
                "Modeled (currency million)",
                "Failure reason",
            ],
        )
        + "<h2>Reconciliation</h2><p>Component bounds form an envelope; joint coverage is not established.</p>"
        + table(
            [
                [
                    r["project_id"],
                    r["relation"],
                    number(r["bottom_up"]),
                    number(r["lower"]),
                    number(r["upper"]),
                    number(r["variance"]),
                ]
                for r in reconciliations
            ],
            [
                "Project",
                "Relation",
                "Bottom-up (currency million)",
                "Lower (currency million)",
                "Upper (currency million)",
                "Direct minus bottom-up (currency million)",
            ],
        )
        + "<h2>Basis, comparables, features and validation</h2>"
        + "".join(details)
        + "</body></html>"
    )
