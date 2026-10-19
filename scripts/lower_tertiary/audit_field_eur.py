#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Audit decline-fit EUR without approving a full-cycle economics basis (#973).

Run with --benchmark CSV --reserves YAML --output JSON. The benchmark uses
api12, field, eur_mmbbl and decline_flag from the existing well benchmark.
Only an explicitly empty decline_flag qualifies a well for the filtered sum;
missing quality evidence, every nonempty flag and invalid volumes are excluded.
No fit-quality or history thresholds are introduced here: the producer defines
those flags in lower_tertiary/well_benchmark.py::_decline_for_well.

The reserves YAML has a `fields` mapping keyed by the benchmark field slug.
Comparisons require eur_mmbbl, source, unit: MMbbl_oil, quantity: recoverable,
scope: full_field and value_kind: estimate. Pending references cannot qualify.
These are explicit evidence assertions by the input curator, not inferred from
prose or independently verified by this script. MMboe, in-place resources,
phase-only figures and lower bounds do not yield like-for-like EUR ratios.
The existing curated table lacks these structured assertions, so its ratios
remain null until its evidence has been qualified.

Equations: raw = sum(valid well EUR); filtered = sum(unflagged valid well EUR);
excluded = sum(valid excluded well EUR); ratio = sum / comparable reference.
These are the additive field model requested in #973, not a new decline model.
The measurement-model convention follows JCGM 100:2008, section 4.1, equation
(1); section 5.1.5 gives linear combinations and section 5.1.6 covers products
and quotients. Quantities must describe the same
measurand before comparison (section 3.1.1). Source:
https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf
For physical volume versus energy equivalents, see EIA, Units and calculators,
"Comparing energy in different fuels" (accessed 2026-10-19):
https://www.eia.gov/energyexplained/units-and-calculators/
No oil-equivalent conversion, reserve value or empirical acceptance limit is
assumed. Ratios are diagnostics; trust is NOT_EVALUATED and full_cycle_eligible
is false until a separately sourced acceptance criterion is implemented.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path

import yaml


def _volume(value: object) -> float | None:
    """Finite nonnegative oil volume, with unknown kept distinct from zero."""
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    # Zero is the additive identity, not an empirical acceptance threshold.
    return number if math.isfinite(number) and number >= 0 else None


def _slug(field: str) -> str:
    return field.strip().lower().replace(" ", "_")


def _sum(values: list[float]) -> float | None:
    """No observations is unknown; an observed zero remains known."""
    if not values:
        return None
    try:
        total = math.fsum(sorted(values))
    except OverflowError:
        raise ValueError("field volume overflow") from None
    return total


def _reference_reasons(reference: Mapping) -> list[str]:
    reasons = []
    value = _volume(reference.get("eur_mmbbl"))
    # A zero reference cannot be a denominator; no reserve limit is assumed.
    if value is None or value == 0:
        reasons.append("reference_value_invalid")
    if reference.get("status") == "pending":
        reasons.append("reference_pending")
    for key, expected, reason in (
        ("unit", "MMbbl_oil", "reference_unit_not_oil"),
        ("quantity", "recoverable", "reference_not_recoverable"),
        ("scope", "full_field", "reference_scope_not_full_field"),
        ("value_kind", "estimate", "reference_not_point_estimate"),
    ):
        if reference.get(key) != expected:
            reasons.append(reason)
    source = reference.get("source")
    if not isinstance(source, str) or not source.strip():
        reasons.append("reference_source_missing")
    return reasons


def _display(total: float | None) -> float | None:
    # One decimal matches the main table in lt_field_performance_comparison.md.
    return round(total, 1) if total is not None else None


def _ratio(total: float | None, reference: float | None) -> float | None:
    if total is None or reference is None:
        return None
    ratio = total / reference
    if not math.isfinite(ratio):
        return None
    # Diagnostic presentation precision follows the field comparison report;
    # no rounded value is used to decide trust or economics eligibility.
    return round(ratio, 1)


def audit_rows(rows: Iterable[Mapping], references: Mapping) -> dict[str, dict]:
    """Return deterministic field diagnostics; never certify reserves or NPV.

    Duplicate well identities are rejected across the entire input so neither
    repeated rows nor overlapping field assignments inflate a field sum.
    Filtered EUR is only a subtotal when coverage is incomplete, never an
    imputed total. Missing and malformed volumes are counted as unknown.
    """
    fields: dict[str, list[Mapping]] = {}
    seen = set()
    for row in rows:
        api, field = row.get("api12"), row.get("field")
        if not isinstance(api, str) or not api.strip():
            raise ValueError("missing well identity")
        if not isinstance(field, str) or not field.strip():
            raise ValueError("missing field identity")
        api = api.strip()
        if api in seen:
            raise ValueError("duplicate well identity")
        seen.add(api)
        fields.setdefault(_slug(field), []).append(row)

    result = {}
    for field in sorted(fields.keys() | references.keys()):
        group = fields.get(field, [])
        raw, included, excluded = [], [], []
        exclusions: Counter = Counter()
        unknown = 0
        for row in group:
            eur = _volume(row.get("eur_mmbbl"))
            flag = row.get("decline_flag")
            if eur is not None:
                raw.append(eur)
            else:
                unknown += 1
            # One primary exclusion reason per row; all invalid volumes remain
            # counted in unknown_eur_wells even if also flagged.
            if not isinstance(flag, str):
                reason = "missing_quality"
            elif flag.strip():
                reason = "decline_flag"
            elif eur is None:
                reason = "invalid_eur"
            else:
                included.append(eur)
                continue
            exclusions[reason] += 1
            if eur is not None:
                excluded.append(eur)

        reference = references.get(field, {})
        ref_reasons = _reference_reasons(reference)
        ref_value = _volume(reference.get("eur_mmbbl"))
        denominator = None if ref_reasons else ref_value
        reasons = list(ref_reasons)
        if not group:
            reasons.append("no_benchmark_wells")
        if exclusions:
            reasons.append("incomplete_reliable_coverage")
        reasons.append("acceptance_criterion_not_supplied")
        raw_total, filtered_total = _sum(raw), _sum(included)
        raw_ratio = _ratio(raw_total, denominator)
        filtered_ratio = _ratio(filtered_total, denominator)
        if denominator is not None and (
            (raw_total is not None and raw_ratio is None)
            or (filtered_total is not None and filtered_ratio is None)
        ):
            reasons.append("ratio_overflow")
        result[field] = {
            "wells": len(group),
            "included_wells": len(included),
            "excluded_wells": sum(exclusions.values()),
            "unknown_eur_wells": unknown,
            "exclusion_counts": dict(sorted(exclusions.items())),
            "raw_decline_eur_mmbbl": _display(raw_total),
            "filtered_decline_eur_mmbbl": _display(filtered_total),
            "excluded_decline_eur_mmbbl": _display(_sum(excluded)),
            "reference_eur": ref_value,
            "reference_unit": reference.get("unit"),
            "reference_basis": reference.get("basis"),
            "reference_source": reference.get("source"),
            "raw_to_reference_ratio": raw_ratio,
            "filtered_to_reference_ratio": filtered_ratio,
            "trust_verdict": "NOT_EVALUATED",
            "full_cycle_eligible": False,
            "reasons": sorted(reasons),
        }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--reserves", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    for input_path in (args.benchmark, args.reserves):
        if args.output.resolve() == input_path.resolve() or (
            args.output.exists() and args.output.samefile(input_path)
        ):
            raise ValueError("output must differ from each input")
    with args.benchmark.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    reserves = yaml.safe_load(args.reserves.read_text(encoding="utf-8"))
    fields = audit_rows(rows, reserves["fields"])
    payload = {
        "meta": {
            "purpose": "Decline EUR diagnostics; full-cycle approval not evaluated",
            "filtered_eur_note": "Subtotal of qualifying wells, not field reserves",
            "ratio_note": "Comparable oil-volume references only; rounded for display",
            "precision_note": "Totals and ratios rounded to one decimal after calculation",
        },
        "fields": fields,
    }
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
