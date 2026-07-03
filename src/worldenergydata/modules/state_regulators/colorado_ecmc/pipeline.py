"""Raw -> normalized -> curated pipeline for Colorado ECMC data (#745)."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

import pandas as pd
import yaml

from worldenergydata.modules.state_regulators.colorado_ecmc.parsers import (
    build_pressure_observations,
    build_quality_stats,
    read_production_csv,
    read_wells_shapefile,
)


def load_config(config_path: str | Path) -> dict:
    with Path(config_path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def configured_sources(config: dict) -> list[dict]:
    """Expand configured ECMC sources into named download entries."""
    return [{"name": name, **source} for name, source in config["sources"].items()]


def download_source(url: str, destination: str | Path, timeout: int = 120) -> dict:
    """Download one direct-source file and return response/file metadata."""
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size = 0
    with urlopen(url, timeout=timeout) as response, path.open("wb") as handle:
        while True:
            chunk = response.read(1 << 20)
            if not chunk:
                break
            handle.write(chunk)
            digest.update(chunk)
            size += len(chunk)
        headers = response.headers
        return {
            "url": url,
            "path": str(path),
            "size_bytes": size,
            "sha256": digest.hexdigest(),
            "last_modified": headers.get("Last-Modified"),
            "etag": headers.get("ETag"),
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
        }


def write_manifest(config: dict, base_dir: str | Path, downloads: list[dict]) -> dict:
    """Write raw/source provenance for configured ECMC files."""
    base = Path(base_dir)
    raw_dir = base / config["storage"]["raw_dir"]
    raw_dir.mkdir(parents=True, exist_ok=True)
    by_url = {item["url"]: item for item in downloads}
    entries = {}
    for name, source in config["sources"].items():
        raw_path = raw_dir / source["raw_path"]
        downloaded = by_url.get(source["url"], {})
        entries[name] = {
            "source_url": source["url"],
            "raw_path": str(raw_path),
            "source_type": source.get("source_type"),
            "sha256": downloaded.get("sha256") or _sha256(raw_path),
            "size_bytes": downloaded.get("size_bytes") or raw_path.stat().st_size,
            "refresh": source.get("refresh"),
            "required_columns": list(source.get("required_columns", [])),
            "last_modified": downloaded.get("last_modified"),
            "etag": downloaded.get("etag"),
            "downloaded_at": downloaded.get("downloaded_at"),
            "manifest_written_at": datetime.now(timezone.utc).isoformat(),
        }
    (raw_dir / "manifest.json").write_text(
        json.dumps(entries, indent=2), encoding="utf-8"
    )
    return entries


def run_pipeline(config_path: str | Path) -> dict:
    config = load_config(config_path)
    base_dir = Path(config["storage"]["base_dir"])
    raw_dir = base_dir / config["storage"]["raw_dir"]
    normalized_dir = base_dir / config["storage"]["normalized_dir"]
    curated_dir = base_dir / config["storage"]["curated_dir"]
    downloads = []
    for source in configured_sources(config):
        downloads.append(download_source(source["url"], raw_dir / source["raw_path"]))
    manifest = write_manifest(config, base_dir, downloads)

    production = _read_configured_production(config, raw_dir)
    wells = read_wells_shapefile(
        raw_dir / config["sources"]["wells_shapefile"]["raw_path"]
    )
    observations = build_pressure_observations(
        production, wells, config["pressure_observations"]
    )
    quality = build_quality_stats(
        production, wells, observations, config["pressure_observations"]
    )
    quality["manifest_sources"] = sorted(manifest)

    production_dir = normalized_dir / "production"
    production_dir.mkdir(parents=True, exist_ok=True)
    production.to_parquet(production_dir / "production_pressure_rows.parquet")

    wells_dir = normalized_dir / "wells"
    wells_dir.mkdir(parents=True, exist_ok=True)
    wells.to_parquet(wells_dir / "wells.parquet")

    pressure_dir = curated_dir / "pressure"
    pressure_dir.mkdir(parents=True, exist_ok=True)
    observations.to_parquet(pressure_dir / "well_pressure_observations.parquet")
    (pressure_dir / "colorado_ecmc_pressure_observation_quality.json").write_text(
        json.dumps(quality, indent=2), encoding="utf-8"
    )
    return {"manifest": manifest, "quality": quality}


def _read_configured_production(config: dict, raw_dir: Path) -> pd.DataFrame:
    frames = []
    for source in configured_sources(config):
        if source.get("source_type") != "production_csv":
            continue
        frames.append(
            read_production_csv(
                raw_dir / source["raw_path"], {"source_name": source["name"]}
            )
        )
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Colorado ECMC ingest (#745)")
    parser.add_argument("--config", default="config/colorado_ecmc.yml")
    args = parser.parse_args()
    result = run_pipeline(args.config)
    print(json.dumps(result["manifest"], indent=2))


if __name__ == "__main__":
    main()
