"""Basis-labelled drilling intensity; no basis is ratified by this module.

Input grain is one row per bore, with ``drilling_days``, an opaque ``basis``
label, ``MAX_BH_TOTAL_MD`` and ``MAX_WELL_BORE_TVD`` (feet). The caller shall
supply drilling-only days; ``completion_days`` is never read. This module
normalizes supplied days rather than deriving, validating or choosing their
measurement basis. Publication waits on the basis decision in issue 1064.

Output schema
-------------
``days_per_10k_md`` / ``days_per_10k_tvd`` use measured / true vertical depth.
``days_per_10k_ft`` (display: Days/10K) uses the REQUIRED caller-selected
``days_per_10k_ft_denominator`` (md or tvd). There is no default denominator.
``basis`` accompanies the ratios; ``intensity_status`` indicates computation,
partial coverage, absent valid pairs, missing basis or mixed basis. Each
specific ratio has its own ``intensity_status_md`` / ``intensity_status_tvd``.
``total_drilling_days_*`` and ``total_depth_ft_*`` contain matched-pair totals;
``included_bores_*`` / ``excluded_bores_*`` disclose coverage for each depth.

Field/block rollups sum drilling days and depth over the SAME valid pairs,
then multiply their ratio by 10,000. Missing/nonfinite/negative days or
missing/nonfinite/nonpositive depth exclude a bore from BOTH totals for that
denominator. A measured zero-day numerator remains zero. Empty populations
emit null totals and ratios. Mixed basis, even on an excluded bore, refuses
all totals and ratios; absent/blank/unavailable labels likewise refuse them.
Input rows shall be unique bores; totals are bore sums, not well-level unions.

The issue-reported best-in-class band below is a plausibility reference,
not an acceptance threshold or primary-source verification. Neither its
MD/TVD denominator nor comparability to a supplied basis is established here.
No published report, dataset table or website values are generated.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from math import fsum, isfinite
from numbers import Real
from typing import Literal, cast

Denominator = Literal["md", "tvd"]

REFERENCE_BAND = {
    "lower": 20,
    "upper": 23,
    "units": "Days/10K",
    "citation": "SPE-87117, de Wardt, IADC/SPE 2004, deepwater GoM and North Sea",
    "source_url": "https://github.com/vamseeachanta/worldenergydata/issues/1080",
    "qualification": "Issue-reported best-in-class; source denominator not established",
}

COLUMN_SCHEMA = {
    "days_per_10k_md": "Drilling days / MAX_BH_TOTAL_MD (measured depth, ft) * 10000",
    "days_per_10k_tvd": "Drilling days / MAX_WELL_BORE_TVD (vertical depth, ft) * 10000",
    "days_per_10k_ft": (
        "Days/10K: denominator in days_per_10k_ft_denominator; basis accompanies "
        "each value. Reference: 20–23 Days/10K, SPE-87117, as cited in issue 1080; "
        "see REFERENCE_BAND for citation and limitations."
    ),
}
DEPTH_COLUMNS = {"md": "MAX_BH_TOTAL_MD", "tvd": "MAX_WELL_BORE_TVD"}


def _valid_number(value: object, *, depth: bool = False) -> bool:
    if isinstance(value, bool) or not isinstance(value, Real):
        return False
    number = float(value)
    return isfinite(number) and (number > 0 if depth else number >= 0)


def _basis(rows: list[Mapping[str, object]]) -> tuple[object, str | None]:
    raw_labels = [row.get("basis") for row in rows]
    labels = {label for label in raw_labels if isinstance(label, str)}
    valid = {label for label in labels if label.strip() and label != "unavailable"}
    if "mixed" in valid or len(valid) > 1:
        return "mixed", "mixed_basis"
    if len(valid) != 1 or any(
        not isinstance(label, str) or label not in valid for label in raw_labels
    ):
        return next(iter(labels)) if len(labels) == 1 else None, "missing_basis"
    return next(iter(valid)), None


def _totals(
    rows: list[Mapping[str, object]], depth_column: str, refusal: str | None
) -> dict[str, object]:
    pairs = [
        (float(cast(Real, row["drilling_days"])), float(cast(Real, row[depth_column])))
        for row in rows
        if _valid_number(row.get("drilling_days"))
        and _valid_number(row.get(depth_column), depth=True)
    ]
    result: dict[str, object] = {
        "included_bores": len(pairs),
        "excluded_bores": len(rows) - len(pairs),
        "total_drilling_days": None,
        "total_depth_ft": None,
        "days_per_10k": None,
        "intensity_status": refusal or "no_valid_pairs",
    }
    if refusal or not pairs:
        return result
    try:
        days = fsum(pair[0] for pair in pairs)
        depth = fsum(pair[1] for pair in pairs)
        ratio = (days / depth) * 10000
    except OverflowError:
        result["intensity_status"] = "nonfinite_result"
        return result
    if not all(isfinite(value) for value in (days, depth, ratio)):
        result["intensity_status"] = "nonfinite_result"
        return result
    result.update(
        total_drilling_days=days,
        total_depth_ft=depth,
        days_per_10k=ratio,
        intensity_status="computed_partial" if len(pairs) < len(rows) else "computed",
    )
    return result


def _intensity(
    rows: list[Mapping[str, object]], denominator: Denominator
) -> dict[str, object]:
    if denominator not in DEPTH_COLUMNS:
        raise ValueError("denominator shall be 'md' or 'tvd'")
    basis, refusal = _basis(rows)
    result: dict[str, object] = {
        "basis": basis,
        "days_per_10k_ft_denominator": denominator,
        "bore_count": len(rows),
    }
    for suffix, depth_column in DEPTH_COLUMNS.items():
        totals = _totals(rows, depth_column, refusal)
        for key, value in totals.items():
            result[f"{key}_{suffix}"] = value
    result["days_per_10k_ft"] = result[f"days_per_10k_{denominator}"]
    result["intensity_status"] = result[f"intensity_status_{denominator}"]
    return result


def bore_intensity(
    bore: Mapping[str, object], *, denominator: Denominator
) -> dict[str, object]:
    """Return drilling-only MD/TVD ratios and an explicitly labelled alias."""
    return _intensity([bore], denominator)


def intensity_rollups(
    bores: Iterable[Mapping[str, object]],
    *,
    group_by: Literal["field", "block"],
    denominator: Denominator,
) -> list[dict[str, object]]:
    """Group unique bores by field/block; input order determines group order.

    Group labels shall be nonblank strings. Supply globally unique block
    labels (including area where required); ambiguous block names shall not
    be combined across areas. Missing group labels raise instead of creating
    a misleading unnamed aggregate.
    """
    if group_by not in ("field", "block"):
        raise ValueError("group_by shall be 'field' or 'block'")
    if denominator not in DEPTH_COLUMNS:
        raise ValueError("denominator shall be 'md' or 'tvd'")
    groups: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for bore in bores:
        label = bore.get(group_by)
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"A nonblank {group_by} label is required")
        groups[label].append(bore)
    return [
        {group_by: label, **_intensity(rows, denominator)}
        for label, rows in groups.items()
    ]
