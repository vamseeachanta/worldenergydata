"""Reusable intervention-HSE analysis package (Phase 2 of #416 / #418).

Extracts the ad-hoc #416 Phase-1A methodology (and its #426 drilling-HSE
re-application) into importable, behavior-preserving units:

- ``classifier.get_incident_classifier`` — repo-canonical IncidentClassifier,
  loaded import-light (falls back to by-path loading if the heavy root __init__
  blocks the normal import).
- ``loaders`` — BSEE INCINV raw-source resolution + parsing.
- ``patterns`` — classify records and compute descriptive pattern stats cut to a
  target activity (subactivity / severity / year / area / confidence distributions).

Import-light: this module pulls only stdlib at import time. Submodules import the
heavy classifier lazily, so ``import ...intervention_hse`` stays cheap.

Example::

    from worldenergydata.bsee.analysis import intervention_hse as ih
    clf = ih.get_incident_classifier()
    src, rows = ih.load_incinv_records()
    activity_dist, pairs = ih.classify_records(clf, rows)
    drill = ih.compute_patterns(pairs, "DRILL", len(rows))
"""
from __future__ import annotations

from .classifier import get_incident_classifier
from .loaders import (
    DEFAULT_INCINV_CANDIDATES,
    load_incinv_file,
    load_incinv_records,
    resolve_incinv_source,
)
from .patterns import (
    INTERVENTION_ACTIVITIES,
    classify_records,
    compute_patterns,
    parse_year,
    severity_proxy,
)

__all__ = [
    "get_incident_classifier",
    "DEFAULT_INCINV_CANDIDATES",
    "resolve_incinv_source",
    "load_incinv_file",
    "load_incinv_records",
    "INTERVENTION_ACTIVITIES",
    "classify_records",
    "compute_patterns",
    "severity_proxy",
    "parse_year",
]
