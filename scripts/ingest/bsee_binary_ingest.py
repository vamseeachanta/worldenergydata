#!/usr/bin/env python3
"""Convert the locally mounted/cached BSEE binary tier to CSV or Parquet.

The source data must already be available locally (the approved plan requires
the external data store to be mounted). No download, solver or network access
is performed. Set --source-root to the BSEE root holding bin/ and zip/; cached
raw ZIPs under .local/ are also supported. --current-root selects the existing
current CSV tier. Only explicitly trusted local DataFrame pickles may be read.
Run with --help for the Makefile-compatible interface.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

try:  # Direct script execution and repository-package import.
    from .bsee_binary_formats import (
        SUFFIXES,
        CurrentIndex,
        detect_format,
        digest,
        tables,
    )
    from .bsee_ingest_manifest import stage_manifests
except ImportError:
    from bsee_binary_formats import (
        SUFFIXES,
        CurrentIndex,
        detect_format,
        digest,
        tables,
    )
    from bsee_ingest_manifest import stage_manifests

GROUPS = ("borehole", "war", "rig_fleet", "directional_survey")


def discover(root: Path, group: str) -> list[Path]:
    """Prefer original archives to already parsed representations."""
    files = []
    for tier in ("zip", ".local", "bin"):
        folder = root / tier / group
        if folder.is_dir():
            files.extend(
                p
                for p in folder.iterdir()
                if p.is_file() and p.suffix.lower() in SUFFIXES
            )
    if group == "directional_survey":
        folder = root / "bin/dsptsdelimit"
        if not any(p.stem.lower() == "dsptsdelimit" for p in files) and folder.is_dir():
            files.extend(
                p
                for p in folder.iterdir()
                if p.is_file() and p.suffix.lower() in SUFFIXES
            )
    if not files:
        raise ValueError(f"No source tables for {group}")
    return sorted(
        files,
        key=lambda p: (
            p.suffix.lower() != ".zip",
            p.suffix.lower() not in {".bin", ".pkl", ".pickle"},
            p.as_posix(),
        ),
    )


def write_table(target: Path, chunks, index: CurrentIndex, output_format: str):
    """Stream filtered chunks to one staged output; return measured counts."""
    count = source_count = 0
    compared = []
    columns = None
    writer = None
    try:
        for chunk in chunks:
            if columns is None:
                columns = list(chunk.columns)
            if list(chunk.columns) != columns:
                raise ValueError("Chunk schemas differ")
            source_count += len(chunk)
            filtered, compared = index.filter(chunk)
            if output_format == "csv":
                filtered.to_csv(
                    target, index=False, mode="a", header=not target.exists()
                )
            else:
                import pyarrow as pa
                import pyarrow.parquet as pq

                schema = pa.schema([(c, pa.string()) for c in columns])
                if writer is None:
                    writer = pq.ParquetWriter(target, schema)
                writer.write_table(
                    pa.Table.from_pandas(filtered, schema=schema, preserve_index=False)
                )
            count += len(filtered)
    finally:
        if writer is not None:
            writer.close()
    return columns, source_count, count, compared


def update_catalog(catalog: dict, records: list[dict], timestamp: str) -> None:
    """Upsert measured outputs without replacing unrelated catalog entries."""
    modules = catalog.setdefault("modules", {})
    bsee = modules.setdefault("bsee", {"module": "bsee", "description": "BSEE data"})
    outputs = {r["path"] for r in records}
    bsee["datasets"] = [
        r for r in bsee.get("datasets", []) if r["path"] not in outputs
    ] + records
    catalog["generated_at"] = timestamp
    catalog["total_modules"] = len(modules)
    catalog["total_datasets"] = sum(
        len(m.get("datasets", [])) for m in modules.values()
    )
    catalog["total_binary_stores"] = sum(
        len(m.get("binary_stores", [])) for m in modules.values()
    )
    catalog["total_size_bytes"] = sum(
        r.get("size_bytes", 0)
        for m in modules.values()
        for key in ("datasets", "binary_stores")
        for r in m.get(key, [])
    )


def ingest(
    source_root: Path,
    project_root: Path,
    current_root: Path,
    groups,
    run_date: date,
    output_format="csv",
    chunk_size=10000,
    encoding="latin-1",
    trust_pickles=False,
) -> list[dict]:
    """Validate all inputs, stage all outputs, then register successful tables."""
    if chunk_size < 1:
        raise ValueError("Chunk size must be positive")
    source_root, project_root = source_root.resolve(), project_root.resolve()
    current_root = current_root.resolve()
    sources = [(group, discover(source_root, group)) for group in groups]
    index = CurrentIndex(current_root, encoding)
    catalog_path = project_root / "data/catalog.yaml"
    catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(catalog, dict):
        raise ValueError("Catalog must be a mapping")
    timestamp = datetime.now(timezone.utc).isoformat()
    records, destinations, selected = [], [], set()
    with tempfile.TemporaryDirectory(
        prefix="bsee-ingest-", dir=catalog_path.parent
    ) as scratch:
        scratch = Path(scratch)
        for group, paths in sources:
            for path in paths:
                if (
                    path.suffix.lower() != ".zip"
                    and (group, path.stem.lower()) in selected
                ):
                    continue
                kind = detect_format(path)
                source_hash = digest(path)
                for name, member, chunks in tables(
                    path, chunk_size, encoding, trust_pickles
                ):
                    identity = (group, name)
                    if identity in selected:
                        if kind == "zip":
                            raise ValueError("Ambiguous table name in source archives")
                        continue  # Original ZIP already supplied this table.
                    selected.add(identity)
                    suffix = (
                        ""
                        if group == "borehole" and name == "mv_boreholes_all"
                        else f"_{name}"
                    )
                    relative = (
                        Path("data/modules/bsee")
                        / group
                        / f"{run_date:%Y%m%d}{suffix}.{output_format}"
                    )
                    target = project_root / relative
                    if (
                        not target.resolve().is_relative_to(project_root)
                        or target.resolve() == path.resolve()
                        or target.resolve().is_relative_to(current_root)
                    ):
                        raise ValueError(
                            "Output cannot overwrite a source/current tier"
                        )
                    staged = scratch / f"{len(records)}.{output_format}"
                    columns, source_count, count, compared = write_table(
                        staged, chunks, index, output_format
                    )
                    schema_status = (
                        "positional_unverified"
                        if name == "directdelimit"
                        else "source_columns"
                    )
                    records.append(
                        {
                            "name": name,
                            "path": relative.as_posix(),
                            "format": output_format,
                            "columns": [
                                {
                                    "name": c,
                                    "type": "string",
                                    "description": "",
                                    "unit": "",
                                }
                                for c in columns
                            ],
                            "row_count": count,
                            "source_row_count": source_count,
                            "duplicate_rows": source_count - count,
                            "size_bytes": staged.stat().st_size,
                            "measured_size_bytes": staged.stat().st_size,
                            "local_only": True,
                            "availability": "present",
                            "sha256": digest(staged),
                            "last_modified": timestamp,
                            "ingested_at": timestamp,
                            "source_id": (
                                "bsee-ewell-war"
                                if group == "war"
                                else "bsee-data-center"
                            ),
                            "source": path.relative_to(source_root).as_posix(),
                            "source_member": member,
                            "source_format": kind,
                            "source_sha256": source_hash,
                            "source_modified_at": datetime.fromtimestamp(
                                path.stat().st_mtime, timezone.utc
                            ).isoformat(),
                            "schema_status": schema_status,
                            "encoding": encoding if kind != "pickle" else None,
                            "data_status": "real",
                            "readiness_status": "partial",
                            "source_vintage": {
                                "state": "unknown",
                                "reason": "File modification time does not establish source vintage",
                            },
                            "deduplication": {
                                "method": "exact_full_row_same_schema",
                                "status": (
                                    "exact_text_only"
                                    if compared
                                    else "no_comparable_schema"
                                ),
                                "compared_files": compared,
                                "compared_sources": [
                                    index.sources[p] for p in compared
                                ],
                            },
                        }
                    )
                    destinations.append((staged, target))
                if digest(path) != source_hash:
                    raise ValueError("Source changed while being read")
        destinations.extend(stage_manifests(records, project_root, scratch))
        update_catalog(catalog, records, timestamp)
        staged_catalog = scratch / "catalog.yaml"
        staged_catalog.write_text(
            yaml.safe_dump(catalog, sort_keys=False), encoding="utf-8"
        )
        for staged, target in destinations:
            target.parent.mkdir(parents=True, exist_ok=True)
            staged.replace(target)
        staged_catalog.replace(catalog_path)
    return records


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(os.environ.get("BSEE_SOURCE_ROOT", "data/modules/bsee")),
    )
    parser.add_argument(
        "--project-root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    parser.add_argument("--current-root", type=Path)
    parser.add_argument("--dataset", action="append", choices=GROUPS)
    parser.add_argument("--date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--format", choices=("csv", "parquet"), default="csv")
    parser.add_argument("--chunk-size", type=int, default=10000)
    parser.add_argument("--encoding", default="latin-1")
    parser.add_argument("--trust-pickles", action="store_true")
    args = parser.parse_args(argv)
    try:
        records = ingest(
            args.source_root,
            args.project_root,
            args.current_root or args.project_root / "data/modules/bsee/current",
            args.dataset or GROUPS,
            args.date,
            args.format,
            args.chunk_size,
            args.encoding,
            args.trust_pickles,
        )
    except Exception as exc:
        # Do not disclose machine paths or source row contents in reports.
        message = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        parser.exit(1, f"BSEE ingest failed: {message}\n")
    print(
        json.dumps(
            {
                "tables": len(records),
                "source_rows": sum(r["source_row_count"] for r in records),
                "output_rows": sum(r["row_count"] for r in records),
                "duplicate_rows": sum(r["duplicate_rows"] for r in records),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
