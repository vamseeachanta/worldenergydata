"""Engineering diagnostics and representative bounded sample selection."""

from collections import defaultdict
from statistics import median


def engineering_qa(rows):
    unique = {r["segment_id"]: r for r in rows}
    rejected, outliers, walls = [], [], []
    for key, row in sorted(unique.items()):
        reason = row.get("route_rejection_reason")
        if reason:
            rejected.append({"segment_id": key, "reason": reason})
        route, permit = row.get("length_m"), row.get("permit_length_m")
        if route is not None and permit is not None and permit > 0:
            ratio = route / permit
            if ratio > 1.5 or ratio < 0.67:
                outliers.append(
                    {
                        "segment_id": key,
                        "route_length_m": route,
                        "permit_length_m": permit,
                        "ratio": ratio,
                    }
                )
        value = row.get("hoop_yield_wall_at_assumed_smys_m")
        if value is not None:
            walls.append(value)
    return {
        "rejected_routes": {"count": len(rejected), "segments": rejected},
        "length_outliers": {
            "count": len(outliers),
            "segments": outliers,
            "criterion": "route/permit < 0.67 or > 1.5",
        },
        "hoop_yield_wall_at_assumed_smys": {
            "count": len(walls),
            "minimum_m": min(walls) if walls else None,
            "median_m": median(walls) if walls else None,
            "count_below_1_mm": sum(v < 0.001 for v in walls),
            "scope": "unique segments; not installed wall thickness",
        },
    }


def stratified_sample(rows, limit=100):
    """Round-robin status, geometry availability and load-case strata."""
    groups = defaultdict(list)
    for row in sorted(rows, key=lambda r: (r["segment_id"], r.get("load_case", ""))):
        key = (
            row.get("status", ""),
            row.get("length_m") is not None,
            row.get("load_case", ""),
        )
        groups[key].append(row)
    sample = []
    while groups and len(sample) < limit:
        for key in sorted(list(groups)):
            sample.append(groups[key].pop(0))
            if not groups[key]:
                del groups[key]
            if len(sample) == limit:
                break
    return sample
