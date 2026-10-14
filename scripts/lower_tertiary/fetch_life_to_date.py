#!/usr/bin/env python3
"""Fetch public BSEE snapshots and write collector-compatible request receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


def fetch(sources_path, archives_dir, archive_name=None):
    """Retrieve each distinct archive sequentially, retaining failed responses."""
    archives_dir.mkdir(parents=True, exist_ok=True)
    sources = json.loads(sources_path.read_text())["files"]
    requests = {item["source_url"]: item["receipt_name"] for item in sources}
    selected = 0
    for url, receipt_name in requests.items():
        address = urlsplit(url)
        if address.scheme != "https" or address.netloc != "www.data.bsee.gov":
            raise ValueError("archive address is not the recorded public publisher")
        name = Path(address.path).name
        if not name.endswith(".zip") or Path(receipt_name).name != receipt_name:
            raise ValueError("archive or receipt name is invalid")
        if archive_name and name != archive_name:
            continue
        selected += 1
        path = archives_dir / name
        receipt = archives_dir / receipt_name
        completed = subprocess.run(
            ["curl", "--proto", "=https", "--proto-redir", "=https",
             "--silent", "--show-error", "--location", "--output", str(path),
             "--write-out", "%{http_code}", url],
            capture_output=True, text=True, check=False,
        )
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        status = completed.stdout.strip()
        receipt.write_text(f"{url}\n{timestamp}\nHTTP_STATUS: {status}\n", encoding="utf-8")
        if completed.returncode or status != "200":
            raise ValueError(f"archive retrieval failed: {name}; HTTP {status}; curl {completed.returncode}")
        archive_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        print(f"{name}: {timestamp}; HTTP {status}; SHA-256 {archive_digest}", flush=True)
    if not selected:
        raise ValueError("no archive request matches the recorded sources")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=Path("data/economics/julia_life_to_date/sources.json"))
    parser.add_argument("--archives-dir", type=Path, required=True)
    parser.add_argument("--archive", help="Retrieve one archive named in the source record")
    args = parser.parse_args()
    fetch(args.sources, args.archives_dir, args.archive)


if __name__ == "__main__":
    main()
