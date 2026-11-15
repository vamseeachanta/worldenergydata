"""Durable metadata for local BSEE exports, independent of catalog scans."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PureWindowsPath

MANIFEST_NAME = "ingest_manifest.json"


def digest(path: Path) -> str:
    """Hash source/output bytes with bounded memory and no data dependencies."""
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def read_manifest(path: Path, root: Path) -> list[dict]:
    """Load measured records and reject duplicate or redirected output paths."""
    if not path.exists():
        return []
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("version") != 1 or not isinstance(document.get("datasets"), list):
        raise ValueError("Invalid ingest manifest")
    records = document["datasets"]
    seen = set()
    parent = path.parent.relative_to(root).as_posix()
    for record in records:
        relative = record.get("path", "")
        output = Path(relative)
        if (
            not relative
            or output.parent.as_posix() != parent
            or ".." in output.parts
            or not (root / output).resolve().is_relative_to(root.resolve())
            or relative in seen
            or record.get("local_only") is not True
            or not isinstance(record.get("measured_size_bytes"), int)
            or record["measured_size_bytes"] < 0
            or not record.get("source_sha256")
            or not record.get("sha256")
        ):
            raise ValueError("Invalid ingest manifest record")
        seen.add(relative)
    return records


def stage_manifests(
    records: list[dict], root: Path, scratch: Path
) -> list[tuple[Path, Path]]:
    """Upsert each group's manifest before any export or catalog is replaced."""
    grouped = {}
    for record in records:
        path = root / Path(record["path"]).parent / MANIFEST_NAME
        grouped.setdefault(path, []).append(record)
    destinations = []
    for number, (path, additions) in enumerate(grouped.items()):
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("Manifest cannot overwrite outside project")
        previous = {r["path"]: r for r in read_manifest(path, root)}
        previous.update({r["path"]: r for r in additions})
        staged = scratch / f"manifest-{number}.json"
        staged.write_text(
            json.dumps({"version": 1, "datasets": list(previous.values())}, indent=2)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        destinations.append((staged, path))
    return destinations


def preserve_ingest_entries(schema: dict, module_path: Path, root: Path) -> None:
    """Overlay measured provenance, counting bytes only for verified local data."""
    if module_path.name != "bsee":
        return
    preserved = {}
    for manifest in sorted(module_path.glob(f"*/{MANIFEST_NAME}")):
        for record in read_manifest(manifest, root):
            entry = dict(record)
            target = root / entry["path"]
            present = target.is_file()
            if present and (
                target.stat().st_size != entry["measured_size_bytes"]
                or digest(target) != entry["sha256"]
            ):
                raise ValueError("Ingest output differs from manifest; rerun ingest")
            entry["availability"] = "present" if present else "missing"
            entry["size_bytes"] = entry["measured_size_bytes"] if present else 0
            preserved[entry["path"]] = entry
    schema["datasets"] = [
        entry
        for entry in schema["datasets"]
        if PureWindowsPath(entry["path"]).as_posix() not in preserved
    ] + list(preserved.values())
