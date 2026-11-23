# ABOUTME: Analogs query layer over the past-projects registry (ranked, explained).
# ABOUTME: Issue #932 (epic #929, A3) — region/water-depth/asset-type analog screening.
"""
worldenergydata.field_development.analogs
=========================================

Analog past projects for a screening run: given a region, a water depth and/or
an asset type (development system), rank the projects in the past-projects
registry (:mod:`~worldenergydata.field_development.past_projects`, issue #931)
by similarity — with an **explicit match rationale** per project, so a
screening consumer can see *why* something is (or is not) an analog.

Scoring
-------
Every supplied criterion (``region``, water depth, ``development_system``,
``status``) is assessed per project as **matched** (credit 1.0), **near_miss**
(partial credit), **missed** (credit 0.0) or **unknown** (credit 0.0 — the
registry attribute is ``null``; nulls NEVER silently count as matches). The
score is the weight-normalised sum of credits over the criteria actually
supplied, so it is always in ``[0, 1]`` regardless of how many criteria the
caller passed. All weights and near-miss credits live in
:data:`ANALOG_WEIGHTS_PATH` (``analogs_weights.yml``, shipped next to this
module) — **no scoring numbers are hardcoded here**.

Ranking is deterministic: score (desc), then absolute water-depth distance
(asc, when both the query and the project depth are known), then
``project_id`` (asc) as the stable tie-break.

Candidates with at least one matched/near-missed criterion are returned;
projects that *miss* every supplied criterion are excluded. A project whose
relevant attributes are all ``null`` (nothing matched, nothing missed) is kept
at score 0.0 with an all-``unknown`` rationale — it cannot be ruled out, and
silently dropping it would turn "unknown" into a hidden "no".

This module only **queries** the registry — it adds no project data. It is
intentionally NOT exported from the package ``__init__`` (same as ``terrain``
and ``past_projects``): import it directly.

Usage::

    from worldenergydata.field_development.analogs import find_analogs, to_records

    matches = find_analogs(
        region="gulf_of_mexico",
        water_depth_m=1580.0,
        development_system="subsea20",
    )
    to_records(matches)  # plain JSON-serialisable dicts for the API consumer

Consumers: digitalmodel#1507 (field-development layout epic) via the
``analogs`` API endpoint (digitalmodel#1512).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

from worldenergydata.field_development.past_projects import (
    VALID_STATUSES,
    WATER_DEPTH_CLASSES,
    PastProject,
    classify_water_depth,
    load_past_projects,
)

__all__ = [
    "ANALOG_WEIGHTS_PATH",
    "CRITERIA",
    "FT_PER_M",
    "AnalogMatch",
    "CriterionAssessment",
    "find_analogs",
    "load_analog_weights",
    "to_records",
]

ANALOG_WEIGHTS_PATH = Path(__file__).parent / "analogs_weights.yml"

#: The criteria the query layer scores, in rationale order. The weights file
#: must cover exactly this set.
CRITERIA = ("region", "water_depth", "development_system", "status")

#: Near-miss credit keys the weights file must define (see analogs_weights.yml).
NEAR_MISS_CREDIT_KEYS = (
    "water_depth_adjacent_class",
    "development_system_same_family",
)

#: Exact unit conversion (1 ft == 0.3048 m by definition). The registry stores
#: depths in feet (BOEM convention); the query accepts metres for the
#: digitalmodel consumer.
FT_PER_M = 1.0 / 0.3048

#: Assessment statuses, from best to worst.
MATCHED = "matched"
NEAR_MISS = "near_miss"
MISSED = "missed"
UNKNOWN = "unknown"

#: Full credit for a matched criterion (definitional — not a tunable weight).
_FULL_CREDIT = 1.0
_NO_CREDIT = 0.0


@dataclass(frozen=True)
class CriterionAssessment:
    """How one query criterion fared against one project (match rationale)."""

    criterion: str
    status: str  # matched | near_miss | missed | unknown
    weight: float
    credit: float  # 0..1 credit earned for this criterion
    detail: str

    def to_record(self) -> dict[str, Any]:
        """Plain JSON-serialisable dict form."""
        return {
            "criterion": self.criterion,
            "status": self.status,
            "weight": self.weight,
            "credit": self.credit,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class AnalogMatch:
    """One ranked analog candidate: project + score + explicit rationale."""

    project: PastProject
    score: float
    rationale: tuple[CriterionAssessment, ...]
    #: |query depth - project depth| in ft; None unless BOTH are known.
    water_depth_distance_ft: Optional[float]

    def to_record(self) -> dict[str, Any]:
        """Plain JSON-serialisable dict form (for the digitalmodel consumer)."""
        p = self.project
        return {
            "project_id": p.project_id,
            "display_name": p.display_name,
            "region": p.region,
            "region_display_name": p.region_display_name,
            "operator": p.operator,
            "water_depth_ft": p.water_depth_ft,
            "water_depth_class": p.water_depth_class,
            "development_system": p.development_system,
            "facility": p.facility,
            "status": p.status,
            "first_oil_year": p.first_oil_year,
            "play": p.play,
            "bsee_area_blocks": list(p.bsee_area_blocks),
            "sources": list(p.sources),
            "notes": p.notes,
            "score": self.score,
            "water_depth_distance_ft": self.water_depth_distance_ft,
            "rationale": [a.to_record() for a in self.rationale],
        }


def to_records(matches: list[AnalogMatch]) -> list[dict[str, Any]]:
    """Ranked matches as plain JSON-serialisable dicts (screening-run form)."""
    return [m.to_record() for m in matches]


def load_analog_weights(path: Optional[Path] = None) -> dict[str, dict[str, float]]:
    """Load and validate the scoring-weights file.

    Contract (fail loud on violation): ``criteria_weights`` covers exactly
    :data:`CRITERIA`, every weight is a positive number, the weights sum to
    1.0, and every :data:`NEAR_MISS_CREDIT_KEYS` credit is a number in
    ``[0, 1)`` (a near-miss must never earn as much as a real match).
    """
    weights_path = Path(path) if path is not None else ANALOG_WEIGHTS_PATH
    data = yaml.safe_load(weights_path.read_text(encoding="utf-8")) or {}

    weights = data.get("criteria_weights")
    if not isinstance(weights, dict):
        raise ValueError(f"{weights_path} has no 'criteria_weights' mapping")
    if set(weights) != set(CRITERIA):
        raise ValueError(
            f"{weights_path} criteria_weights keys {sorted(weights)} != "
            f"expected criteria {sorted(CRITERIA)}"
        )
    for criterion, weight in weights.items():
        if not isinstance(weight, (int, float)) or weight <= 0:
            raise ValueError(
                f"{weights_path} weight for {criterion!r} must be a positive "
                f"number, got {weight!r}"
            )
    total = sum(weights.values())
    if not math.isclose(total, 1.0, rel_tol=0, abs_tol=1e-9):
        raise ValueError(
            f"{weights_path} criteria_weights must sum to 1.0, got {total!r}"
        )

    credits = data.get("near_miss_credits")
    if not isinstance(credits, dict):
        raise ValueError(f"{weights_path} has no 'near_miss_credits' mapping")
    if set(credits) != set(NEAR_MISS_CREDIT_KEYS):
        raise ValueError(
            f"{weights_path} near_miss_credits keys {sorted(credits)} != "
            f"expected {sorted(NEAR_MISS_CREDIT_KEYS)}"
        )
    for key, credit in credits.items():
        if not isinstance(credit, (int, float)) or not 0 <= credit < 1:
            raise ValueError(
                f"{weights_path} near-miss credit {key!r} must be a number in "
                f"[0, 1), got {credit!r}"
            )

    return {
        "criteria_weights": {k: float(v) for k, v in weights.items()},
        "near_miss_credits": {k: float(v) for k, v in credits.items()},
    }


def _norm(value: str) -> str:
    return " ".join(value.split()).lower()


def _dev_system_family(dev_system: str) -> str:
    """Taxonomy family = the token with trailing digits stripped.

    ``subsea15``/``subsea20`` -> ``subsea``; ``tieback15`` -> ``tieback``;
    ``dry`` -> ``dry``.
    """
    return _norm(dev_system).rstrip("0123456789")


def _assess_region(
    query: str, project: PastProject, weight: float
) -> CriterionAssessment:
    if _norm(query) in (_norm(project.region), _norm(project.region_display_name)):
        return CriterionAssessment(
            "region",
            MATCHED,
            weight,
            _FULL_CREDIT,
            f"project region {project.region!r} matches query {query!r}",
        )
    return CriterionAssessment(
        "region",
        MISSED,
        weight,
        _NO_CREDIT,
        f"project region {project.region!r} != query {query!r}",
    )


def _adjacent_classes(class_a: str, class_b: str) -> bool:
    order = list(WATER_DEPTH_CLASSES)
    return abs(order.index(class_a) - order.index(class_b)) == 1


def _assess_water_depth(
    query_class: str,
    query_depth_ft: Optional[float],
    project: PastProject,
    weight: float,
    adjacent_credit: float,
) -> tuple[CriterionAssessment, Optional[float]]:
    if project.water_depth_ft is None:
        return (
            CriterionAssessment(
                "water_depth",
                UNKNOWN,
                weight,
                _NO_CREDIT,
                "water depth not stated in the registry (null) — cannot "
                f"compare with query class {query_class!r}",
            ),
            None,
        )
    project_class = project.water_depth_class
    distance = (
        abs(query_depth_ft - project.water_depth_ft)
        if query_depth_ft is not None
        else None
    )
    depth_note = f"; |depth distance| = {distance:g} ft" if distance is not None else ""
    if project_class == query_class:
        return (
            CriterionAssessment(
                "water_depth",
                MATCHED,
                weight,
                _FULL_CREDIT,
                f"project depth {project.water_depth_ft:g} ft is "
                f"{project_class!r} == query class{depth_note}",
            ),
            distance,
        )
    if _adjacent_classes(project_class, query_class):
        return (
            CriterionAssessment(
                "water_depth",
                NEAR_MISS,
                weight,
                adjacent_credit,
                f"project class {project_class!r} is adjacent to query class "
                f"{query_class!r}{depth_note}",
            ),
            distance,
        )
    return (
        CriterionAssessment(
            "water_depth",
            MISSED,
            weight,
            _NO_CREDIT,
            f"project class {project_class!r} is not adjacent to query class "
            f"{query_class!r}{depth_note}",
        ),
        distance,
    )


def _assess_development_system(
    query: str, project: PastProject, weight: float, family_credit: float
) -> CriterionAssessment:
    if project.development_system is None:
        return CriterionAssessment(
            "development_system",
            UNKNOWN,
            weight,
            _NO_CREDIT,
            "development_system not stated in the registry (null) — cannot "
            f"match query {query!r}",
        )
    if _norm(project.development_system) == _norm(query):
        return CriterionAssessment(
            "development_system",
            MATCHED,
            weight,
            _FULL_CREDIT,
            f"development_system {project.development_system!r} matches "
            f"query {query!r}",
        )
    if _dev_system_family(project.development_system) == _dev_system_family(query):
        return CriterionAssessment(
            "development_system",
            NEAR_MISS,
            weight,
            family_credit,
            f"development_system {project.development_system!r} is in the "
            f"same family as query {query!r}",
        )
    return CriterionAssessment(
        "development_system",
        MISSED,
        weight,
        _NO_CREDIT,
        f"development_system {project.development_system!r} != query {query!r}",
    )


def _assess_status(
    query: str, project: PastProject, weight: float
) -> CriterionAssessment:
    if project.status is None:
        return CriterionAssessment(
            "status",
            UNKNOWN,
            weight,
            _NO_CREDIT,
            f"status not stated in the registry (null) — cannot match query {query!r}",
        )
    if project.status == query:
        return CriterionAssessment(
            "status",
            MATCHED,
            weight,
            _FULL_CREDIT,
            f"status {project.status!r} matches query",
        )
    return CriterionAssessment(
        "status",
        MISSED,
        weight,
        _NO_CREDIT,
        f"status {project.status!r} != query {query!r}",
    )


def find_analogs(
    region: Optional[str] = None,
    water_depth_m: Optional[float] = None,
    water_depth_class: Optional[str] = None,
    development_system: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    path: Optional[Path] = None,
    weights_path: Optional[Path] = None,
) -> list[AnalogMatch]:
    """Ranked analog past projects for a screening run.

    Args:
        region: Region key (``"gulf_of_mexico"``) or display name
            (``"US Gulf of Mexico"``); case-insensitive.
        water_depth_m: Site water depth in **metres**; classified via
            :func:`classify_water_depth` (BOEM convention, ft) and also used
            to rank by absolute depth distance where project depths are known.
            Mutually exclusive with ``water_depth_class``.
        water_depth_class: One of the BOEM classes (``shallow`` /
            ``deepwater`` / ``ultra_deepwater``) when the caller already has a
            class instead of a depth.
        development_system: Asset type — the registry's ``development_system``
            taxonomy (e.g. ``subsea15``, ``subsea20``, ``tieback15``, ``dry``);
            case-insensitive. Same-family variants score a near-miss.
        status: One of the registry statuses (case-insensitive); validated,
            fail-loud on typos.
        limit: Keep only the top-``limit`` matches after ranking.
        path: Optional alternate past-projects catalog path (tests).
        weights_path: Optional alternate scoring-weights path (tests).

    Returns:
        :class:`AnalogMatch` list, best first. Deterministic order: score
        (desc), then absolute depth distance (asc, known distances before
        unknown), then ``project_id`` (asc). Projects that miss every
        supplied criterion are excluded; all-``unknown`` candidates are kept
        at score 0.0 (they cannot be ruled out).

    Raises:
        ValueError: No criterion supplied, both ``water_depth_m`` and
            ``water_depth_class`` supplied, non-positive ``water_depth_m``,
            unknown ``water_depth_class``/``status``, non-positive ``limit``,
            or an invalid weights file.
    """
    if all(
        arg is None
        for arg in (
            region,
            water_depth_m,
            water_depth_class,
            development_system,
            status,
        )
    ):
        raise ValueError(
            "find_analogs() needs at least one criterion (region, water_depth_m, "
            "water_depth_class, development_system, status)"
        )
    if water_depth_m is not None and water_depth_class is not None:
        raise ValueError(
            "Pass either water_depth_m or water_depth_class, not both "
            "(the class is derived from the depth)"
        )
    query_depth_ft: Optional[float] = None
    query_class: Optional[str] = water_depth_class
    if water_depth_m is not None:
        if not isinstance(water_depth_m, (int, float)) or water_depth_m <= 0:
            raise ValueError(
                f"water_depth_m must be a positive number, got {water_depth_m!r}"
            )
        # Round the converted depth so an exact metric equivalent of a BOEM
        # threshold (e.g. 304.8 m == 1,000 ft) can never fall on the wrong
        # side of the class boundary through float error.
        query_depth_ft = round(water_depth_m * FT_PER_M, 6)
        query_class = classify_water_depth(query_depth_ft)
    if query_class is not None and query_class not in WATER_DEPTH_CLASSES:
        raise ValueError(
            f"Unknown water_depth_class {query_class!r} "
            f"(expected one of {list(WATER_DEPTH_CLASSES)})"
        )
    status_key: Optional[str] = None
    if status is not None:
        by_norm = {_norm(s): s for s in VALID_STATUSES}
        status_key = by_norm.get(_norm(status))
        if status_key is None:
            raise ValueError(
                f"Unknown status {status!r} (expected one of {sorted(VALID_STATUSES)})"
            )
    if limit is not None and limit <= 0:
        raise ValueError(f"limit must be a positive integer, got {limit!r}")

    weights_cfg = load_analog_weights(path=weights_path)
    weights = weights_cfg["criteria_weights"]
    credits = weights_cfg["near_miss_credits"]

    matches: list[AnalogMatch] = []
    for project in load_past_projects(path=path):
        rationale: list[CriterionAssessment] = []
        distance: Optional[float] = None
        if region is not None:
            rationale.append(_assess_region(region, project, weights["region"]))
        if query_class is not None:
            assessment, distance = _assess_water_depth(
                query_class,
                query_depth_ft,
                project,
                weights["water_depth"],
                credits["water_depth_adjacent_class"],
            )
            rationale.append(assessment)
        if development_system is not None:
            rationale.append(
                _assess_development_system(
                    development_system,
                    project,
                    weights["development_system"],
                    credits["development_system_same_family"],
                )
            )
        if status_key is not None:
            rationale.append(_assess_status(status_key, project, weights["status"]))

        earned = sum(a.weight * a.credit for a in rationale)
        applicable = sum(a.weight for a in rationale)
        score = round(earned / applicable, 6)
        if score <= 0 and any(a.status == MISSED for a in rationale):
            # Definitively not an analog on every supplied axis it answers.
            continue
        matches.append(
            AnalogMatch(
                project=project,
                score=score,
                rationale=tuple(rationale),
                water_depth_distance_ft=distance,
            )
        )

    matches.sort(
        key=lambda m: (
            -m.score,
            m.water_depth_distance_ft is None,
            m.water_depth_distance_ft or 0.0,
            m.project.project_id,
        )
    )
    if limit is not None:
        matches = matches[:limit]
    return matches
