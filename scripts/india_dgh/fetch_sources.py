"""Fetch the public India upstream source files and verify their SHA-256.

Usage:
    python scripts/india_dgh/fetch_sources.py --dest <empty-dir> [--pause 5]

The manifest is ``worldenergydata/india_dgh/data/source_manifest.json``. Each
entry records the public URL, the expected SHA-256 at review time and the
terms that govern reuse. Files are fetched one at a time with a pause between
requests. ``url`` is the Internet Archive capture of ``original_url``: the DGH
and PPAC origins refused or timed out connections from the build host on
2026-10-31. No sign-in, form or registration is used; the National Data
Repository is out of scope.

A digest mismatch is reported and the run exits non-zero. A mismatch means the
publisher replaced the file; review it before updating the manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

MANIFEST = (
    Path(__file__).resolve().parents[2]
    / "packages/worldenergydata-india_dgh/src/worldenergydata/india_dgh/data"
    / "source_manifest.json"
)
ALLOWED_HOSTS = {
    "web.archive.org",
    "dghindia.gov.in",
    "www.dghindia.gov.in",
    "ppac.gov.in",
    "www.ppac.gov.in",
    "mopng.gov.in",
    "www.mopng.gov.in",
    "data.gov.in",
    "www.data.gov.in",
}
USER_AGENT = "worldenergydata-india_dgh/0.1 (+https://github.com/vamseeachanta/worldenergydata)"
MAX_BYTES = 60 * 1024 * 1024


def _check_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"URL outside the reviewed public origins: {url}")
    return url


def fetch(url: str, timeout: float = 120.0) -> bytes:
    request = Request(_check_url(url), headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - origin checked
        _check_url(response.geturl())
        payload = response.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError(f"download exceeds {MAX_BYTES} bytes: {url}")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dest", type=Path, required=True)
    parser.add_argument("--pause", type=float, default=5.0)
    parser.add_argument("--only", help="fetch a single manifest id")
    args = parser.parse_args(argv)

    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]
    if args.only:
        entries = [e for e in entries if e["id"] == args.only]
    args.dest.mkdir(parents=True, exist_ok=True)
    failures = 0
    for index, entry in enumerate(entries):
        if index:
            time.sleep(args.pause)
        target = args.dest / entry["filename"]
        try:
            payload = fetch(entry["url"])
        except Exception as exc:  # report the layer, continue with the rest
            print(f"FAIL {entry['id']}: {type(exc).__name__}: {exc}")
            failures += 1
            continue
        digest = hashlib.sha256(payload).hexdigest()
        target.write_bytes(payload)
        status = "OK" if digest == entry["sha256"] else "DIGEST-CHANGED"
        failures += status != "OK"
        print(f"{status} {entry['id']} {len(payload)} bytes sha256={digest}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
