"""Evidence gate for externally documented rework cases and negative controls.

Recall = TP/(TP+FN); false-positive rate = FP/(FP+TN), direct definitions
of conditional proportions. Hand-calculated matrix examples accompany tests.
No literature-derived performance limit is assumed: both limits are inputs.
"""

from __future__ import annotations


def validate_cases(rows: list[dict], cases: list[dict], policy: dict) -> dict:
    """Missing cases, citations, scored wells or controls cannot pass the gate.

    ``known_good=False`` requires a documented negative control, not an
    unlabeled well. Source veracity and representativeness need human review.
    Synthetic cases test arithmetic only and establish no field accuracy.
    """
    indexed = {row["well_key"]: row for row in rows}
    counts = dict.fromkeys(("tp", "fn", "fp", "tn"), 0)
    missing = []
    seen = set()
    evidence = []
    for case in cases:
        key = case.get("well_key")
        if key in seen:
            raise ValueError("duplicate validation case")
        seen.add(key)
        row = indexed.get(key)
        if (
            not isinstance(case.get("source"), str)
            or not case["source"].strip()
            or not isinstance(case.get("known_good"), bool)
            or row is None
            or row["status"] != "EVALUATED"
        ):
            missing.append(key)
            continue
        selected, positive = row["candidate"], case["known_good"]
        label = (
            ("tp" if selected else "fn") if positive else ("fp" if selected else "tn")
        )
        counts[label] += 1
        evidence.append({**case, "classification": label})
    positives = counts["tp"] + counts["fn"]
    negatives = counts["fp"] + counts["tn"]
    recall = counts["tp"] / positives if positives else None
    fpr = counts["fp"] / negatives if negatives else None
    if missing or recall is None or fpr is None:
        status = "NOT_EVALUATED"
    elif recall >= policy["min_recall"] and fpr <= policy["max_false_positive_rate"]:
        status = "PASS"
    else:
        status = "FAIL"
    return {
        "status": status,
        "counts": counts,
        "recall": recall,
        "false_positive_rate": fpr,
        "unevaluated_cases": missing,
        "cases": evidence,
        "limits": dict(policy),
        "note": (
            "Documented rework positives and negative controls are required; "
            "no cases means no field accuracy estimate. Labels must postdate "
            "the feature cutoff and be checked independently for leakage."
        ),
    }
