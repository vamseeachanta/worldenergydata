"""Offline export validation, provenance emission and country/year queries."""

import argparse
import sys
from pathlib import Path

from .irena import (
    MAX_EXPORT_BYTES,
    emit_manifest,
    fetch_irena,
    load_export,
    write_table,
)
from .query import query_export


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("load", "fetch", "query"))
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--retrieved-at-utc")
    parser.add_argument("--terms-quote")
    parser.add_argument("--terms-url")
    parser.add_argument(
        "--country", action="append", help="Query country; repeat for a union"
    )
    parser.add_argument("--start-year", type=int, help="Inclusive query year bound")
    parser.add_argument("--end-year", type=int, help="Inclusive query year bound")
    parser.add_argument("--generation-unit", choices=("GWh", "MWh"))
    args = parser.parse_args()
    query_options = (args.country, args.start_year, args.end_year, args.generation_unit)
    if args.operation != "query" and any(value is not None for value in query_options):
        parser.error("Country, year and generation-unit options require query")
    if args.operation == "fetch":
        fetch_irena()
    if args.operation == "query" and any(
        (
            args.manifest,
            args.synthetic,
            args.retrieved_at_utc,
            args.terms_quote,
            args.terms_url,
        )
    ):
        parser.error("Query does not emit a manifest or accept provenance options")
    if args.input is None:
        parser.error("load and query require --input")
    if args.operation == "load" and args.manifest is None:
        parser.error("load requires --input and --manifest")
    paths = [
        p.resolve() for p in (args.input, args.output, args.manifest) if p is not None
    ]
    if len(paths) != len(set(paths)):
        parser.error("Input, output and manifest paths must be distinct")
    for destination in (args.output, args.manifest):
        if destination is not None and destination.exists():
            raise FileExistsError("Output or manifest already exists")
    with args.input.open("rb") as stream:
        raw = stream.read(MAX_EXPORT_BYTES + 1)
    if args.operation == "query":
        result = query_export(
            raw,
            countries=args.country,
            start_year=args.start_year,
            end_year=args.end_year,
            generation_unit=args.generation_unit or "GWh",
        )
        if args.output:
            with args.output.open("xb") as stream:
                stream.write(result)
        else:
            sys.stdout.write(result.decode("utf-8"))
        return
    records = load_export(raw)
    manifest = emit_manifest(
        raw,
        synthetic=args.synthetic,
        retrieved_at_utc=args.retrieved_at_utc,
        terms_quote=args.terms_quote,
        terms_url=args.terms_url,
    )
    if args.output:
        with args.output.open("xb") as stream:
            stream.write(write_table(records))
    with args.manifest.open("xb") as stream:
        stream.write(manifest)


if __name__ == "__main__":
    main()
