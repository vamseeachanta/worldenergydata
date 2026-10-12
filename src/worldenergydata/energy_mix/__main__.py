"""Offline export validation, normalized output and provenance emission."""

import argparse
from pathlib import Path

from .irena import (
    MAX_EXPORT_BYTES,
    emit_manifest,
    fetch_irena,
    load_export,
    write_table,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("load", "fetch"))
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--retrieved-at-utc")
    parser.add_argument("--terms-quote")
    parser.add_argument("--terms-url")
    args = parser.parse_args()
    if args.operation == "fetch":
        fetch_irena()
    if args.input is None or args.manifest is None:
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
