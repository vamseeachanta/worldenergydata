"""CLI for activity taxonomy classification.

Classify HSE incidents from raw data files into the standardized
activity/subactivity taxonomy, or display taxonomy summaries.

Usage:
    uv run python -m worldenergydata.safety_analysis.taxonomy.cli \
        classify --source bsee \
        --input data/modules/hse/raw/bsee/IncInvRawData/mv_acc_investigations.txt \
        --output results/hse/bsee_classified.csv

    uv run python -m worldenergydata.safety_analysis.taxonomy.cli \
        summary

    uv run python -m worldenergydata.safety_analysis.taxonomy.cli \
        taxonomy
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from worldenergydata.safety_analysis.taxonomy.activity_registry import (
    ActivityTaxonomy,
)
from worldenergydata.safety_analysis.taxonomy.incident_classifier import (

from worldenergydata.common.logging import get_logger

logger = get_logger(__name__)
    IncidentClassifier,
)


def _parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="taxonomy-cli",
        description="HSE Activity Taxonomy Classifier",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # classify command
    classify_parser = subparsers.add_parser(
        "classify",
        help="Classify incidents from a data file",
    )
    classify_parser.add_argument(
        "--source",
        required=True,
        choices=["bsee", "osha", "marine_safety", "phmsa", "epa_tri"],
        help="Data source identifier",
    )
    classify_parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Input CSV/TXT file path",
    )
    classify_parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output classified CSV file path",
    )
    classify_parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of records to classify (0 = all)",
    )

    # summary command
    subparsers.add_parser(
        "summary",
        help="Display classification summary from a classified file",
    )

    # taxonomy command
    subparsers.add_parser(
        "taxonomy",
        help="Display the full activity taxonomy",
    )

    return parser.parse_args(argv)


def _load_csv_records(path: Path) -> List[Dict[str, Any]]:
    """Load records from a CSV/TXT file."""
    records: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Strip whitespace and quotes from keys and values
            clean = {
                k.strip().strip('"'): v.strip().strip('"')
                for k, v in row.items()
                if k is not None
            }
            records.append(clean)
    return records


def cmd_classify(args: argparse.Namespace) -> None:
    """Classify incidents from input file and write results."""
    if not args.input.exists():
        logger.error(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Loading records from {args.input}...")
    records = _load_csv_records(args.input)
    if args.limit > 0:
        records = records[: args.limit]
    logger.info(f"Loaded {len(records)} records")

    classifier = IncidentClassifier()
    logger.info(f"Classifying with source={args.source}...")
    results = classifier.classify_batch(records, source=args.source)

    # Write results alongside original fields
    fieldnames = list(records[0].keys()) if records else []
    result_fields = [
        "activity",
        "activity_name",
        "subactivity",
        "subactivity_name",
        "confidence",
        "match_method",
    ]
    all_fields = fieldnames + result_fields

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_fields)
        writer.writeheader()
        for record, result in zip(records, results):
            row = dict(record)
            row.update(
                {
                    "activity": result.activity,
                    "activity_name": result.activity_name,
                    "subactivity": result.subactivity,
                    "subactivity_name": result.subactivity_name,
                    "confidence": f"{result.confidence:.2f}",
                    "match_method": result.match_method,
                }
            )
            writer.writerow(row)

    logger.info(f"Wrote {len(results)} classified records to {args.output}")

    # Print distribution summary
    _print_distribution(results)


def cmd_taxonomy(args: argparse.Namespace) -> None:
    """Display the full taxonomy tree."""
    taxonomy = ActivityTaxonomy()
    logger.info(f"Activity Taxonomy ({len(taxonomy.activities)} activities)")
    logger.info("=" * 60)
    for activity in taxonomy.activities:
        logger.info(f"\n  {activity.code}: {activity.name}")
        logger.info(f"    {activity.description}")
        if activity.sic_codes:
            logger.info(f"    SIC: {', '.join(activity.sic_codes)}")
        if activity.naics_codes:
            logger.info(f"    NAICS: {', '.join(activity.naics_codes)}")
        if activity.bsee_accident_types:
            logger.info(f"    BSEE types: {', '.join(activity.bsee_accident_types)}")
        if activity.marine_incident_types:
            logger.info(f"    Marine types: {', '.join(activity.marine_incident_types)}")
        if activity.phmsa_cause_categories:
            logger.info(f"    PHMSA causes: {', '.join(activity.phmsa_cause_categories)}")
        for sub in activity.subactivities:
            logger.info(f"      - {sub.code}: {sub.name}")


def cmd_summary(args: argparse.Namespace) -> None:
    """Display taxonomy summary statistics."""
    classifier = IncidentClassifier()
    summary = classifier.get_taxonomy_summary()
    logger.info(json.dumps(summary, indent=2))


def _print_distribution(results: list) -> None:
    """Print activity distribution of classification results."""
    from collections import Counter

    activity_counts: Counter = Counter()
    method_counts: Counter = Counter()
    for r in results:
        activity_counts[f"{r.activity} ({r.activity_name})"] += 1
        method_counts[r.match_method] += 1

    logger.info("\nActivity Distribution:")
    for activity, count in activity_counts.most_common():
        pct = 100.0 * count / len(results)
        logger.info(f"  {activity}: {count} ({pct:.1f}%)")

    logger.info("\nMatch Method Distribution:")
    for method, count in method_counts.most_common():
        pct = 100.0 * count / len(results)
        logger.info(f"  {method}: {count} ({pct:.1f}%)")


def main(argv: List[str] | None = None) -> None:
    """Entry point for taxonomy CLI."""
    args = _parse_args(argv)
    if args.command == "classify":
        cmd_classify(args)
    elif args.command == "taxonomy":
        cmd_taxonomy(args)
    elif args.command == "summary":
        cmd_summary(args)


if __name__ == "__main__":
    main()
