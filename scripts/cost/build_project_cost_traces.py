#!/usr/bin/env python3
"""Build nominal project event histories from the curated cost evidence tables."""

from __future__ import annotations

import argparse
from pathlib import Path

from worldenergydata.cost.timeseries.portfolio_trace import (
    build_portfolio_trace,
    write_trace_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root", type=Path, default=Path("data/modules/cost/curated")
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--revision-date", required=True)
    args = parser.parse_args()
    source = args.data_root.resolve()
    destination = args.output_dir.resolve()
    if destination == source or source in destination.parents:
        parser.error("output directory must be outside the curated input directory")
    trace = build_portfolio_trace(source)
    write_trace_outputs(
        trace, destination, revision=args.revision, revision_date=args.revision_date
    )
    print(f"Projects: {len(trace.projects)}; distinct events: {len(trace.events)}")
    print(f"Component-to-total consistency: {trace.consistency_status}")


if __name__ == "__main__":
    main()
