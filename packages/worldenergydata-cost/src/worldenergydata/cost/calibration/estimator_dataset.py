"""Comparable selection with explicit exclusions and project independence."""

from collections import Counter
from dataclasses import dataclass
from datetime import date

from .capex_estimator_schema import FeatureSnapshot, TrainingRecord


@dataclass(frozen=True)
class Cohort:
    records: tuple[TrainingRecord, ...]
    feature_names: tuple[str, ...]
    missing_features: tuple[str, ...]
    exclusions: tuple[tuple[str, str], ...]


def select_cohort(records, target: FeatureSnapshot, cutoff: date) -> Cohort:
    """One point disclosure per independent group; all duplicate groups excluded.

    Exact basis equality deliberately prohibits implicit nominal-year pooling.
    Both project and canonical validation group are checked to avoid leakage.
    """
    if cutoff > target.as_of:
        raise ValueError("training cutoff follows prediction date")
    names = tuple(sorted(k for k, v in target.features.items() if v is not None))
    missing = tuple(sorted(k for k, v in target.features.items() if v is None))
    candidates = [r for r in records if not _exclusion(r, target, cutoff, names)]
    groups = Counter(r.snapshot.validation_group_id for r in candidates)
    projects = Counter(r.snapshot.project_id for r in candidates)
    included, excluded = [], []
    for record in records:
        snap = record.snapshot
        reason = _exclusion(record, target, cutoff, names)
        if not reason and (
            groups[snap.validation_group_id] > 1 or projects[snap.project_id] > 1
        ):
            reason = "duplicate project or validation group"
        if reason:
            excluded.append((snap.project_id, reason))
        else:
            included.append(record)
    return Cohort(
        tuple(sorted(included, key=lambda r: r.snapshot.project_id)),
        names,
        missing,
        tuple(sorted(excluded)),
    )


def _exclusion(record, target, cutoff, names):
    snap = record.snapshot
    if (
        snap.project_id == target.project_id
        or snap.validation_group_id == target.validation_group_id
    ):
        return "target project or validation group"
    if record.derivation != "disclosed" or record.bound_type != "point":
        return "not an observed point disclosure"
    if record.disclosed_on > cutoff:
        return "target disclosed after training cutoff"
    if snap.basis != target.basis:
        return "incompatible accounting or currency basis"
    if (snap.architecture, snap.host_type) != (target.architecture, target.host_type):
        return "incompatible architecture or host"
    if not names or any(snap.features.get(k) is None for k in names):
        return "missing target-available features"
    return None
