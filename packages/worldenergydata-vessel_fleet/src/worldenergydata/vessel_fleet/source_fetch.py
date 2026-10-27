"""Fetch manifest-pinned liftboat sources to an explicitly chosen directory.

Raw documents are not package data. Downloads run serially through curl and
must match the curated manifest before being promoted from a partial file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from worldenergydata.vessel_fleet.loaders.liftboat_loader import LiftboatLoader


def _verify(path: Path, source: dict) -> None:
    if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
        raise ValueError("source digest mismatch; retained bytes were not overwritten")
    if path.stat().st_size != source["size_bytes"]:
        raise ValueError("source size mismatch")


def _verify_receipt(target: Path, source: dict) -> None:
    receipt_path = target.with_suffix(target.suffix + ".receipt.json")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(
            "source receipt missing or invalid; inspect retained provenance before resuming"
        ) from error
    expected = {
        "url": source["url"],
        "http_status": 200,
        "sha256": source["sha256"],
        "size_bytes": source["size_bytes"],
    }
    if not isinstance(receipt, dict) or any(
        receipt.get(field) != value for field, value in expected.items()
    ):
        raise ValueError("source receipt metadata mismatch")
    timestamp = receipt.get("retrieved_at")
    if not isinstance(timestamp, str):
        raise ValueError("source receipt requires a retrieval timestamp")
    try:
        observed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("source receipt retrieval timestamp is invalid") from error
    if observed.tzinfo is None:
        raise ValueError("source receipt retrieval timestamp requires a timezone")


def fetch_sources(
    output_dir: Path | str,
    manifest_path: Path | str | None = None,
    source_ids: list[str] | None = None,
) -> list[str]:
    """Fetch public documents once, verifying existing bytes on subsequent runs.

    Existing files require both matching bytes and a valid retrieval receipt.
    Missing or invalid receipts, different digests and leftover partial files
    stop the operation without overwriting or removing evidence. Local seed
    records and inaccessible index pages are excluded. Changed upstream bytes
    require a reviewed manifest update; no digest is silently refreshed.
    """
    if manifest_path is None:
        manifest = LiftboatLoader().manifest
    else:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    sources = manifest["sources"]
    selected = (
        source_ids
        if source_ids is not None
        else [
            identity
            for identity, source in sources.items()
            if source["kind"] == "public_document"
        ]
    )
    for identity in selected:
        if identity not in sources or sources[identity]["kind"] != "public_document":
            raise ValueError("source is not downloadable")
        source = sources[identity]
        filename = source["raw_file"]
        if not filename or Path(filename).name != filename or "\\" in filename:
            raise ValueError("unsafe raw filename")
        if not source["url"].startswith("https://"):
            raise ValueError("source URL must use HTTPS")
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    completed = []
    for identity in selected:
        source = sources[identity]
        target = destination / source["raw_file"]
        if target.exists():
            _verify(target, source)
            _verify_receipt(target, source)
            completed.append(identity)
            continue
        partial = target.with_suffix(target.suffix + ".part")
        if partial.exists():
            raise FileExistsError(
                "partial source exists; inspect retained bytes before resuming"
            )
        result = subprocess.run(
            [
                "curl",
                "--fail",
                "--location",
                "--silent",
                "--show-error",
                "--max-time",
                "120",
                "--proto",
                "=https",
                "--proto-redir",
                "=https",
                "--output",
                partial.as_posix(),
                "--write-out",
                "%{http_code}",
                source["url"],
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.stdout != "200":
            raise ValueError("source returned unexpected HTTP status")
        _verify(partial, source)
        partial.rename(target)
        receipt = {
            "url": source["url"],
            "http_status": 200,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "sha256": source["sha256"],
            "size_bytes": source["size_bytes"],
        }
        target.with_suffix(target.suffix + ".receipt.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        completed.append(identity)
    return completed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--source", action="append", dest="source_ids")
    arguments = parser.parse_args()
    completed = fetch_sources(arguments.output_dir, source_ids=arguments.source_ids)
    print(f"Verified {len(completed)} source documents.")


if __name__ == "__main__":
    main()
