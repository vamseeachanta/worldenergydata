# ABOUTME: Back-test the recommendation engine against real field concepts.
# ABOUTME: Issue #570/#569 (epic #567) — calibration harness + accuracy metrics.
"""
worldenergydata.field_development.calibration
=============================================

Back-tests :func:`recommend` against the **real** development concepts of the
enriched SubseaIQ fields (the ground truth attached in #569). For each field we
strip the answer (``concept_type``/``operator``), run the engine on the remaining
inputs, and compare its ranked picks to what was actually built.

This is a *calibration* tool, not a unit of business logic: it measures how often
the heuristics' top pick (and top-k) match reality, and exposes the confusion
pattern so the priors can be tuned. A regression test pins the achieved accuracy.

**Honest scope:** the enriched fields carry only water depth + fluid as inputs,
so this measures depth/fluid-driven discrimination. ``subsea_tieback`` (a large
share of reality) needs distance-to-host data the engine doesn't have here, so
it is structurally under-predicted — an *input gap*, recorded in the report,
not a tuning target.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass, field
from typing import Optional

from worldenergydata.field_development.models import FieldConcept
from worldenergydata.field_development.recommendation import recommend
from worldenergydata.field_development.subseaiq import load_subseaiq_fields


@dataclass
class CalibrationReport:
    """Accuracy + confusion from a back-test run."""

    n: int = 0
    top1: int = 0
    topk: int = 0
    k: int = 3
    confusion: dict[tuple[str, str], int] = field(default_factory=dict)

    @property
    def top1_acc(self) -> float:
        return self.top1 / self.n if self.n else 0.0

    @property
    def topk_acc(self) -> float:
        return self.topk / self.n if self.n else 0.0


def backtest_fields(
    fields: Optional[list[FieldConcept]] = None, k: int = 3
) -> CalibrationReport:
    """Run the engine over fields with a known real concept and score it.

    Args:
        fields: Concepts carrying a real ``concept_type`` (defaults to the
            enriched SubseaIQ catalog). Fields without a concept or water depth
            are skipped.
        k: Top-k cutoff for the secondary accuracy metric.

    Returns:
        A :class:`CalibrationReport`.
    """
    if fields is None:
        fields = load_subseaiq_fields(enrich_facilities=True)
    eligible = [f for f in fields
                if f.concept_type is not None and f.water_depth_m is not None]

    rep = CalibrationReport(n=len(eligible), k=k)
    conf: collections.Counter = collections.Counter()
    for f in eligible:
        real = f.concept_type
        # Strip the answer so the engine can't see it.
        probe = f.model_copy(update={"concept_type": None, "operator": None})
        picks = [r.concept_type for r in recommend(probe)]
        if picks and picks[0] == real:
            rep.top1 += 1
        if real in picks[:k]:
            rep.topk += 1
        pred = picks[0].value if picks else "none"
        conf[(real.value, pred)] += 1
    rep.confusion = dict(conf)
    return rep
