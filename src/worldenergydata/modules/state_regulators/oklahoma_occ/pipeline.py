"""Raw -> normalized -> curated pipeline for Oklahoma OCC data (#740)."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

import yaml

from worldenergydata.modules.state_regulators.oklahoma_occ.parsers import (
    build_pressure_observations,
    build_quality_stats,
    read_completion_workbook,
)


def load_config(config_path: str | Path) -> dict:
    with Path(config_path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


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
    """Write raw/source provenance for configured OCC files."""
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
            "sha256": downloaded.get("sha256") or _sha256(raw_path),
            "size_bytes": downloaded.get("size_bytes") or raw_path.stat().st_size,
            "refresh": source["refresh"],
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
    for source in config["sources"].values():
        downloads.append(
            download_source(source["url"], raw_dir / source["raw_path"])
        )
    manifest = write_manifest(config, base_dir, downloads)

    completions = read_completion_workbook(
        raw_dir / config["sources"]["completion_workbook"]["raw_path"]
    )
    observations = build_pressure_observations(
        completions, config["pressure_observations"]
    )
    quality = build_quality_stats(completions, observations)
    quality["manifest_sources"] = sorted(manifest)

    completions_dir = normalized_dir / "completions"
    completions_dir.mkdir(parents=True, exist_ok=True)
    completions.to_parquet(completions_dir / "completion_pressure_rows.parquet")

    pressure_dir = curated_dir / "pressure"
    pressure_dir.mkdir(parents=True, exist_ok=True)
    observations.to_parquet(pressure_dir / "well_pressure_observations.parquet")
    (pressure_dir / "oklahoma_occ_pressure_observation_quality.json").write_text(
        json.dumps(quality, indent=2), encoding="utf-8"
    )
    return {"manifest": manifest, "quality": quality}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Oklahoma OCC ingest (#740)")
    parser.add_argument("--config", default="config/oklahoma_occ.yml")
    args = parser.parse_args()
    result = run_pipeline(args.config)
    print(json.dumps(result["manifest"], indent=2))


if __name__ == "__main__":
    main()
