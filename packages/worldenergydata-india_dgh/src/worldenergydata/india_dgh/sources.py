"""Source manifest: public URL, SHA-256 at review, terms of reuse."""

from __future__ import annotations

import hashlib
import json
from importlib import resources
from pathlib import Path

REQUIRED_KEYS = {"id", "publisher", "title", "url", "filename", "sha256", "retrieved", "terms_url"}


def data_path(name: str) -> Path:
    """Path of a file shipped in ``worldenergydata/india_dgh/data``."""
    return Path(str(resources.files("worldenergydata.india_dgh") / "data" / name))


def load_source_manifest() -> dict:
    manifest = json.loads(data_path("source_manifest.json").read_text(encoding="utf-8"))
    ids = set()
    for entry in manifest["files"]:
        missing = REQUIRED_KEYS - set(entry)
        if missing:
            raise ValueError(f"manifest entry {entry.get('id')} lacks {sorted(missing)}")
        if len(entry["sha256"]) != 64:
            raise ValueError(f"manifest entry {entry['id']} has no SHA-256")
        if entry["id"] in ids:
            raise ValueError(f"duplicate manifest id {entry['id']}")
        ids.add(entry["id"])
    return manifest


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_file(path: str | Path, source_id: str) -> str:
    """Return the digest of ``path``; raise if it differs from the manifest."""
    entries = {e["id"]: e for e in load_source_manifest()["files"]}
    digest = sha256_file(path)
    if digest != entries[source_id]["sha256"]:
        raise ValueError(f"{path} does not match the reviewed {source_id} file")
    return digest
