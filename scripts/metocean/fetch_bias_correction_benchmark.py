#!/usr/bin/env python3
"""Fetch the pinned, CC BY 4.0 Oikonomou et al. (2026) benchmark outside Git.

See DOI 10.1016/j.apor.2026.105259 and DOI 10.5281/zenodo.19239166.
Re-check licence before retrieving data; refuse changed bytes and >=100 MB.
"""

import argparse
import hashlib
import io
import json
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
SPEC = json.loads(
    (ROOT / "tests/fixtures/metocean/bias_correction/manifest.json").read_text()
)
LIMIT = 100_000_000


def fetch(destination):
    destination = Path(destination).resolve()
    if destination == ROOT or ROOT in destination.parents:
        raise ValueError("Benchmark data destination must be outside the repository")
    with urlopen(SPEC["metadata_url"], timeout=30) as response:
        record = json.loads(response.read(1_000_000))
    license_id = record.get("metadata", {}).get("license", {}).get("id")
    if license_id != SPEC["license"] or license_id != "cc-by-4.0":
        raise ValueError("Dataset licence does not match the verified reuse permission")
    archive_spec, member_spec = SPEC["file"], SPEC["member"]
    if max(archive_spec["bytes"], member_spec["bytes"]) >= LIMIT:
        raise ValueError("Dataset exceeds the download/uncompressed size limit")
    with urlopen(archive_spec["url"], timeout=30) as response:
        payload = response.read(archive_spec["bytes"] + 1)
    if len(payload) != archive_spec["bytes"]:
        raise ValueError("Dataset archive size changed")
    if hashlib.sha256(payload).hexdigest() != archive_spec["sha256"]:
        raise ValueError("Dataset archive digest changed")
    with ZipFile(io.BytesIO(payload)) as archive:
        member = archive.getinfo(member_spec["name"])
        if member.file_size != member_spec["bytes"]:
            raise ValueError("Dataset member size changed")
        data = archive.read(member)
    if hashlib.sha256(data).hexdigest() != member_spec["sha256"]:
        raise ValueError("Dataset member digest changed")
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / member_spec["name"]
    path.write_bytes(data)
    if hashlib.sha256(path.read_bytes()).hexdigest() != member_spec["sha256"]:
        raise ValueError("Saved dataset digest mismatch")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(fetch(args.destination))
