"""Count matched fields by region and as-built development type.

Basis: issue 776 (2026), ``recommendation._DRY_TREE``, and the existing
``portfolio_matched.build_portfolio`` pipeline. Unlike the global facility
report, each record here represents a field, including tieback satellites.
Recommendations never supply missing actual labels.

Counts are set cardinalities, and coverage is typed / total fields (the
definition requested by issue 776). No engineering equations or empirical
coefficients are introduced. Lifecycle quantities cannot be evaluated from
these inputs. Country labels remain country labels unless a recognized BSEE
block provides Gulf basin evidence; this is not a global basin crosswalk.

Export with ``python -m worldenergydata.field_development.development_comparison
--output comparison.json``. Input overrides use ``--crosswalk`` and ``--fields``.
The curated catalog is a historical snapshot, not a current global census.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterable
from pathlib import Path

from worldenergydata.field_development.enums import ConceptType
from worldenergydata.field_development.host_enrichment import _curated_path
from worldenergydata.field_development.portfolio_matched import (
    PortfolioRow,
    _curated_crosswalk_path,
    build_portfolio,
)
from worldenergydata.field_development.recommendation import _DRY_TREE
from worldenergydata.field_development.subseaiq import (
    AREA_ABBR,
    _curated_fields_path,
    bsee_block_key,
)

# Issue 776 (2026), enumerated WET membership; unknown concepts stay OTHER.
_WET_TREE = {
    ConceptType.SEMISUB_FPS,
    ConceptType.FPSO,
    ConceptType.FLNG,
    ConceptType.SUBSEA_TIEBACK,
    ConceptType.SUBSEA_TO_SHORE,
}
_TREE_TYPES = ("dry", "wet", "other")
_GULF_LABELS = {"us", "gulf of mexico", "us gulf of mexico"}


def _normalized(value: str | None) -> str:
    return " ".join((value or "").split())


def _region(row: PortfolioRow) -> tuple[str, str]:
    """Use the existing SubseaIQ area vocabulary, not country-only inference."""
    label = _normalized(row.concept.region)
    block = bsee_block_key(row.match.bsee_block_code)
    if block is not None and block[0] in AREA_ABBR.values():
        if label and label.casefold() not in _GULF_LABELS:
            raise ValueError(
                f"conflicting region and BSEE block for {row.concept.name}"
            )
        return "US Gulf of Mexico", "bsee_block_code"
    if label:
        return label, "field_concept.region"
    return "Unknown region", "missing"


def canonical_fields(rows: Iterable[PortfolioRow]) -> list[dict]:
    """Return one record per matched field; reject ambiguous duplicate identities.

    The matched portfolio joins by field name. Names are compared after
    whitespace normalization and case folding; duplicate rows are rejected
    rather than arbitrarily selecting one of their potentially different labels.
    The enriched concept supplies the actual, including satellite corrections.
    """
    records = []
    seen = set()
    for row in rows:
        name = _normalized(row.match.og_field_name)
        if not name:
            raise ValueError("field name must not be blank")
        identity = name.casefold()
        if identity != _normalized(row.concept.name).casefold():
            raise ValueError(f"field identity mismatch for {name}")
        if identity in seen:
            raise ValueError(f"duplicate field name: {name}")
        seen.add(identity)
        actual = row.actual
        tree = "other"
        if actual in _DRY_TREE:
            tree = "dry"
        elif actual in _WET_TREE:
            tree = "wet"
        region, basis = _region(row)
        records.append(
            {
                "field_name": name,
                "bsee_block_code": row.match.bsee_block_code,
                "region": region,
                "region_basis": basis,
                "water_depth_m": row.concept.water_depth_m,
                "concept_type": actual.value if actual is not None else None,
                "tree_type": tree,
            }
        )
    return sorted(
        records, key=lambda r: (r["region"].casefold(), r["field_name"].casefold())
    )


def _counts(fields: list[dict]) -> dict:
    """Cardinality and typed / total coverage, per issue 776 (2026)."""
    counts = {tree: sum(f["tree_type"] == tree for f in fields) for tree in _TREE_TYPES}
    total = len(fields)
    typed = counts["dry"] + counts["wet"]
    return {
        **counts,
        "total": total,
        "typed": typed,
        "untyped": counts["other"],
        # An empty denominator is unevaluated, not measured zero coverage.
        "coverage_fraction": typed / total if total else None,
    }


def compare_portfolio(rows: Iterable[PortfolioRow]) -> dict:
    """Compare supplied actual field records, retaining unknowns in every count.

    No facility rows are mixed into this field denominator. Non-Gulf input
    regions can be compared as supplied, but the default builder only selects
    BSEE-matched fields and cannot establish all-region coverage.
    """
    fields = canonical_fields(rows)
    by_region: dict[str, list[dict]] = {}
    for record in fields:
        by_region.setdefault(record["region"], []).append(record)
    return {
        "universe": "BSEE-matched field portfolio; not a global field census",
        "classification_basis": "As-built concept; recommendation._DRY_TREE and issue 776",
        "coverage_definition": "typed / total fields; typed = dry + wet",
        "readiness_status": "unverified",
        "limitations": [
            "Historical curated snapshot; present-day completeness is not established.",
            "Country labels and block-derived basin labels have different specificity.",
            "Other means missing or unmapped concept, not absence of producing trees.",
        ],
        "fields": fields,
        "regions": [
            {"region": region, **_counts(records)}
            for region, records in sorted(
                by_region.items(), key=lambda item: item[0].casefold()
            )
        ],
        "totals": _counts(fields),
        "lifecycle_metrics": {
            "status": "NOT_EVALUATED",
            "reason": (
                "Drilling days, completion days, intervention demand and decommissioning "
                "cost require sourced field-level observations and comparable units."
            ),
        },
    }


def build_comparison(
    crosswalk_path: Path | None = None, fields_path: Path | None = None
) -> dict:
    """Reuse the canonical pipeline and fingerprint all its catalog inputs.

    Digests identify observed file contents, not source freshness or engineering
    qualification. A source change during loading invalidates the comparison.
    No caller-local source paths are included in the exported metadata.
    """
    inputs = [
        ("matched_crosswalk", crosswalk_path or _curated_crosswalk_path()),
        ("field_catalog", fields_path or _curated_fields_path()),
        ("host_registry", _curated_path()),
    ]
    digests = [hashlib.sha256(path.read_bytes()).hexdigest() for _, path in inputs]
    result = compare_portfolio(
        build_portfolio(crosswalk_path=crosswalk_path, fields_path=fields_path)
    )
    for (_, path), digest in zip(inputs, digests):
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("source changed during loading; comparison invalidated")
    result["sources"] = [
        {"role": role, "sha256": digest} for (role, _), digest in zip(inputs, digests)
    ]
    return result


def main(argv: list[str] | None = None) -> None:
    """Export a machine-readable comparison; no reports are written implicitly."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crosswalk", type=Path, help="Matched crosswalk CSV override")
    parser.add_argument(
        "--fields", type=Path, help="Curated field catalog CSV override"
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="New destination JSON file"
    )
    args = parser.parse_args(argv)
    if any(
        path is not None and args.output.resolve() == path.resolve()
        for path in (args.crosswalk, args.fields)
    ):
        parser.error("output must not overwrite an input catalog")
    result = build_comparison(crosswalk_path=args.crosswalk, fields_path=args.fields)
    payload = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    with args.output.open("x", encoding="utf-8") as destination:
        destination.write(payload)


if __name__ == "__main__":
    main()
