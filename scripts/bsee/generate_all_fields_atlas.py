#!/usr/bin/env python
"""Generate the GoM all-fields production atlas from materialized OGOR-A bins.

Wires the deterministic OGOR ``.bin`` loader into the existing
:class:`AllFieldsRunner` and :class:`AllFieldsReport`, producing a
gulf-wide field table (CSV) plus an interactive HTML atlas and a Markdown
summary.  All inputs are real BSEE public data; nothing is fabricated.

Usage::

    .venv/bin/python scripts/bsee/generate_all_fields_atlas.py \
        --start-year 1996 --end-year 2025 --out reports/bsee/all_fields

Era classification is best-effort: wells absent from Paleowells.csv are
reported as ``Unknown`` rather than guessed.
"""

from __future__ import annotations

import argparse
import logging
from collections import Counter
from pathlib import Path

from worldenergydata.bsee.analysis.all_fields_runner import AllFieldsRunner
from worldenergydata.bsee.data.field_names import FieldNameResolver
from worldenergydata.bsee.data.sources.bin.field_water_depth import (
    load_field_water_depth,
)
from worldenergydata.bsee.data.sources.bin.ogor_production_loader import (
    load_all_fields_production,
)
from worldenergydata.bsee.paleowells.era_classifier import GeologicalEraClassifier
from worldenergydata.bsee.paleowells.field_era import (
    apply_field_era,
    build_field_era_map,
)
from worldenergydata.bsee.reports.all_fields_report import AllFieldsReport
from worldenergydata.common.data_resolver import get_module_data_safe

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("all_fields_atlas")


class FastEraClassifier:
    """O(1)-per-well era classifier with the same ``classify_field`` contract.

    The base :class:`GeologicalEraClassifier.classify_field` re-scans the
    paleo table for every API, which is O(wells x paleo_rows) — far too slow
    for ~30k gulf-wide wells.  This wrapper precomputes the well->era map
    once and resolves each field by majority vote via dict lookups, giving
    results identical to the base classifier.
    """

    def __init__(self, base: GeologicalEraClassifier) -> None:
        self._well_eras = base.get_well_eras()

    def classify_field(self, field_wells) -> str:
        if not field_wells:
            return "Unknown"
        counter: Counter = Counter()
        for api in field_wells:
            era = self._well_eras.get(str(api))
            if era:
                counter[era] += 1
        if not counter:
            return "Unknown"
        return counter.most_common(1)[0][0]


def build_era_classifier() -> FastEraClassifier:
    """Construct a fast era classifier from the Paleowells CSV (best-effort)."""
    paleo = get_module_data_safe("bsee") / "paleowells" / "Paleowells.csv"
    if paleo.exists():
        return FastEraClassifier(GeologicalEraClassifier(paleowells_csv=paleo))
    logger.warning("Paleowells.csv not found at %s — eras will be Unknown", paleo)
    return FastEraClassifier(GeologicalEraClassifier())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=1996)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--out", type=Path, default=Path("reports/bsee/all_fields"))
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="OGOR bin dir (default: resolved bsee module bin/historical_production_yearly)",
    )
    args = parser.parse_args()

    logger.info("Loading OGOR production %d-%d...", args.start_year, args.end_year)
    prod = load_all_fields_production(
        data_dir=args.data_dir,
        start_year=args.start_year,
        end_year=args.end_year,
    )
    if prod.empty:
        logger.error("No production data loaded — aborting.")
        return 1
    logger.info(
        "Loaded %d production rows across %d fields",
        len(prod),
        prod["FIELD_NAME_CODE"].nunique(),
    )

    resolver = FieldNameResolver()
    era = build_era_classifier()

    logger.info("Loading field water depth...")
    field_wd = load_field_water_depth()
    logger.info("Field water depth available for %d field codes", len(field_wd))

    latest_year = None
    if "PROD_YEAR" in prod.columns:
        years = prod["PROD_YEAR"].dropna()
        latest_year = int(years.max()) if not years.empty else None

    logger.info("Aggregating all fields...")
    result = AllFieldsRunner(resolver, era).run(
        prod, field_water_depth=field_wd, latest_year=latest_year
    )
    logger.info("Aggregated %d fields", len(result))

    # Lift paleo-well eras to the field level (all paleo wells, incl.
    # non-producing) so far more fields than the producing-well-only
    # classifier resolves to a real era; also stamps IS_LOWER_TERTIARY.
    logger.info("Lifting eras to field level from all paleo wells...")
    field_era_map = build_field_era_map()
    result = apply_field_era(result, field_era_map)
    if "GEOLOGICAL_ERA" in result.columns and not result.empty:
        from_map = int(result["FIELD_CODE"].astype(str).str.strip().isin(field_era_map).sum())
        unknown = int((result["GEOLOGICAL_ERA"] == "Unknown").sum())
        lt = int(result["IS_LOWER_TERTIARY"].sum())
        logger.info(
            "Field-era map covers %d field codes; %d/%d atlas fields got era "
            "from the field-map, %d remain Unknown, %d flagged Lower Tertiary",
            len(field_era_map),
            from_map,
            len(result),
            unknown,
            lt,
        )

    args.out.mkdir(parents=True, exist_ok=True)
    report = AllFieldsReport(result)
    report.generate_csv(args.out / "gom_all_fields_atlas.csv")
    report.generate_html(args.out / "gom_all_fields_atlas.html")
    report.generate_markdown(args.out / "gom_all_fields_atlas.md")
    logger.info("Atlas written to %s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
