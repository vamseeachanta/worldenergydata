"""Official Kansas KGS raw source catalog and manifest helpers."""

from __future__ import annotations

import hashlib
import json
import shutil
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Callable, Mapping

import yaml

DEFAULT_KANSAS_KGS_ROOT = Path("/mnt/ace/worldenergydata/data/modules/kansas_kgs")


@dataclass(frozen=True)
class RawSource:
    """One official KGS source and its raw storage location."""

    source_id: str
    source_url: str
    raw_path: Path
    optional: bool = False


def load_source_catalog(
    catalog_path: Path | None = None,
    root: Path | str = DEFAULT_KANSAS_KGS_ROOT,
) -> dict[str, RawSource]:
    """Load the packaged KGS source catalog and validate raw paths."""
    payload = _load_yaml(catalog_path or _package_file("source_catalog.yml"))
    root_path = Path(root)
    catalog = {}
    for source_id, source in payload.get("sources", {}).items():
        raw_path = Path(source["raw_path"])
        resolved = raw_path if raw_path.is_absolute() else root_path / raw_path
        _validate_under_root(resolved, root_path)
        catalog[source_id] = RawSource(
            source_id=source_id,
            source_url=str(source["source_url"]),
            raw_path=resolved,
            optional=bool(source.get("optional", False)),
        )
    return catalog


def load_kansas_counties() -> dict[str, str]:
    """Load Kansas API/FIPS county-code names from package data."""
    path = _package_file("kansas_counties.yml")
    payload = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader) or {}
    return {str(code).zfill(3): str(name) for code, name in payload.items()}


def ensure_raw_sources(
    root: Path | str = DEFAULT_KANSAS_KGS_ROOT,
    refresh: bool = False,
    fetcher: Callable[[RawSource, Path], None] | None = None,
    allow_non_ace_root: bool = False,
    http_metadata: Mapping[str, Mapping[str, object]] | None = None,
    metadata_fetcher: Callable[[RawSource], Mapping[str, object]] | None = None,
    generated_at: datetime | None = None,
) -> dict[str, dict[str, object]]:
    """Ensure required raw KGS files exist and write a manifest."""
    root_path = Path(root)
    _validate_storage_root(root_path, allow_non_ace_root)
    catalog = load_source_catalog(root=root_path)
    manifest_sources = {}
    stamp = _timestamp(generated_at)
    for source_id, source in catalog.items():
        if source.optional:
            continue
        fetched_metadata = {}
        if refresh or not source.raw_path.exists():
            fetched_metadata = _fetch_source(source, fetcher)
        metadata = dict(fetched_metadata)
        if http_metadata and source_id in http_metadata:
            metadata.update(http_metadata.get(source_id, {}))
        elif metadata_fetcher is not None:
            metadata.update(metadata_fetcher(source))
        elif not allow_non_ace_root:
            metadata.update(_head_metadata(source))
        manifest_sources[source_id] = _source_manifest(
            source,
            metadata,
            stamp,
        )
    payload = {
        "generated_at": stamp,
        "root": str(root_path),
        "sources": manifest_sources,
    }
    manifest_path = root_path / "raw" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    tmp_path.replace(manifest_path)
    return manifest_sources


def _fetch_source(
    source: RawSource,
    fetcher: Callable[[RawSource, Path], None] | None,
) -> dict[str, object]:
    source.raw_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = source.raw_path.with_suffix(source.raw_path.suffix + ".tmp")
    if fetcher is not None:
        fetcher(source, tmp_path)
        metadata: dict[str, object] = {}
    else:
        with urllib.request.urlopen(source.source_url, timeout=60) as response:
            metadata = _response_metadata(response)
            with tmp_path.open("wb") as output:
                shutil.copyfileobj(response, output)
    tmp_path.replace(source.raw_path)
    return metadata


def _head_metadata(source: RawSource) -> dict[str, object]:
    request = urllib.request.Request(source.source_url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return _response_metadata(response)
    except Exception:
        return {}


def _response_metadata(response) -> dict[str, object]:
    headers = dict(response.headers.items())
    return {
        "status": getattr(response, "status", None),
        "last_modified": headers.get("Last-Modified"),
        "content_length": headers.get("Content-Length"),
        "content_type": headers.get("Content-Type"),
        "headers": headers,
    }


def _source_manifest(
    source: RawSource,
    http_metadata: Mapping[str, object],
    observed_at: str,
) -> dict[str, object]:
    data = source.raw_path.read_bytes()
    return {
        "source_url": source.source_url,
        "raw_path": str(source.raw_path),
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "observed_at": observed_at,
        "http_metadata": dict(http_metadata),
    }


def _validate_storage_root(root: Path, allow_non_ace_root: bool) -> None:
    if allow_non_ace_root:
        return
    _validate_under_root(root, DEFAULT_KANSAS_KGS_ROOT)


def _validate_under_root(path: Path, root: Path) -> None:
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Kansas KGS path must stay under {root}: {path}")


def _package_file(name: str) -> Path:
    return Path(str(resources.files("worldenergydata.kansas_kgs.data") / name))


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _timestamp(value: datetime | None) -> str:
    stamp = value or datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
