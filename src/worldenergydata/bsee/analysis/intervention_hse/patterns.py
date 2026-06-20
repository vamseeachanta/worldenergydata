"""Pattern-mining functions for the intervention-HSE Phase-2 package.

Descriptive pattern stats over a BSEE INCINV subset cut to a target activity by the
repo-canonical ``IncidentClassifier``. The math (severity proxy, year extraction,
distribution counting, confidence bucketing) is extracted verbatim — behavior
preserving — from the #416 Phase-1A / #426 exploration scripts.

Stdlib only.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

# Activity codes treated as intervention-relevant for the #416 cut. DRILL captures
# well_control / workover / completion drilling-phase events; PROD carries the
# well_intervention / artificial_lift / chemical_injection subactivities.
INTERVENTION_ACTIVITIES: Tuple[str, ...] = ("DRILL", "PROD")


def severity_proxy(accident_type: str) -> str:
    """Map a BSEE ACCIDENT_TYPE string to a coarse severity bucket.

    Extracted verbatim from the #426 ``_severity`` helper.
    """
    t = (accident_type or "").lower()
    if "fatality" in t:
        return "fatality"
    if "blowout" in t or "explosion" in t:
        return "major"  # well-control / explosion = high consequence
    if "lta" in t or "rw/jt" in t or "injury" in t:
        return "injury_lost_time"
    if "fire" in t or "pollution" in t or "collision" in t or "$25k" in t:
        return "serious"
    if "evacuation" in t or "muster" in t or "shutdown" in t:
        return "evacuation_muster"
    return "other"


def parse_year(date_occurred: str) -> Optional[int]:
    """Extract the year from a BSEE ``DATE_OCCURRED`` (M/D/YYYY) string.

    Extracted verbatim from the #426 ``_year`` helper.
    """
    try:
        parts = (date_occurred or "").split("/")
        return int(parts[-1])
    except Exception:
        return None


def _confidence_bucket(confidence: float) -> str:
    if confidence >= 0.90:
        return "direct_code(>=0.90)"
    if confidence >= 0.70:
        return "keyword_high(0.70-0.89)"
    if confidence >= 0.50:
        return "keyword_medium(0.50-0.69)"
    return "keyword_low(<0.50)"


def classify_records(
    classifier,
    rows: List[Dict[str, Any]],
    source: str = "bsee",
) -> Tuple[Counter, List[Tuple[Dict[str, Any], Any]]]:
    """Classify every row; return (activity_distribution, classified_pairs).

    ``classified_pairs`` is a list of (row, ClassificationResult) for ALL rows so
    callers can cut to any activity. Behavior mirrors the #426 main loop.
    """
    activity_dist: Counter = Counter()
    pairs: List[Tuple[Dict[str, Any], Any]] = []
    for row in rows:
        res = classifier.classify(row, source=source)
        activity_dist[res.activity] += 1
        pairs.append((row, res))
    return activity_dist, pairs


def compute_patterns(
    classified_pairs: List[Tuple[Dict[str, Any], Any]],
    activity: str,
    total_records: int,
) -> Dict[str, Any]:
    """Compute the descriptive pattern stats for a single activity cut.

    ``classified_pairs`` is the full (row, result) list from ``classify_records``;
    this function filters to ``result.activity == activity`` and computes the same
    distributions the #426 script emitted (subactivity, match-method, accident-type,
    severity, year, area, confidence buckets, distinct leases).
    """
    cut = [(row, res) for row, res in classified_pairs if res.activity == activity]
    n = len(cut)

    sub_dist: Counter = Counter()
    method_dist: Counter = Counter()
    acc_type_dist: Counter = Counter()
    severity_dist: Counter = Counter()
    year_dist: Counter = Counter()
    area_dist: Counter = Counter()
    conf_buckets: Counter = Counter()
    for row, res in cut:
        sub_dist[res.subactivity] += 1
        method_dist[res.match_method] += 1
        acc_type_dist[(row.get("ACCIDENT_TYPE", "") or "").strip()] += 1
        severity_dist[severity_proxy(row.get("ACCIDENT_TYPE", ""))] += 1
        y = parse_year(row.get("DATE_OCCURRED", ""))
        if y:
            year_dist[y] += 1
        area = (
            (row.get("AREA_BLOCK", "") or "").split()[0]
            if row.get("AREA_BLOCK")
            else ""
        )
        if area:
            area_dist[area] += 1
        conf_buckets[_confidence_bucket(res.confidence)] += 1

    return {
        "activity": activity,
        "total": n,
        "pct_of_records": round(100.0 * n / total_records, 2) if total_records else 0.0,
        "subactivity_distribution": dict(sub_dist.most_common()),
        "match_method": dict(method_dist.most_common()),
        "confidence_buckets": dict(conf_buckets.most_common()),
        "accident_type_top": dict(acc_type_dist.most_common(20)),
        "accident_type_distinct": len(acc_type_dist),
        "severity_proxy": dict(severity_dist.most_common()),
        "by_year": dict(sorted(year_dist.items())),
        "year_range": [min(year_dist), max(year_dist)] if year_dist else None,
        "top_areas": dict(area_dist.most_common(10)),
        "distinct_leases": len(
            {r.get("LEASE_NUMBER", "") for r, _ in cut if r.get("LEASE_NUMBER")}
        ),
    }
