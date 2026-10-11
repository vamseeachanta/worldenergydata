"""Bounded, sequential BOEM FieldReserves fetch and provenance emission."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Sequence

BASE = "https://www.data.boem.gov"
VINTAGE_LISTING = f"{BASE}/Main/HtmlPage.aspx?page=estimated2023"
FAMILY_LISTING = f"{BASE}/Main/FieldReserves.aspx"
TERMS_URL = f"{BASE}/Main/HtmlPage.aspx?page=Disclaimer"
USER_AGENT = (
    "WorldEnergyData FieldReserves (https://github.com/vamseeachanta/worldenergydata)"
)
FILES = (
    "2023 FldMoPro.zip",
    "2023 Hist.zip",
    "mastproddelimit.zip",
    "appendbdelimit.zip",
)
DISCLAIMER = "This data is not for navigational use."
TERMS_SHA256 = "2e77757d7c92f4652eaca11891165e2e0a9a75cf55a8ef52753d6d5dc3dfb037"


def verify_terms(body: bytes) -> None:
    """Any change to the reviewed source page requires a new terms review."""
    if hashlib.sha256(body).hexdigest() != TERMS_SHA256:
        raise ValueError("Terms page changed; manual terms review required")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> Any:
        raise urllib.error.HTTPError(newurl, code, "Redirect refused", headers, fp)


def _open(request: urllib.request.Request, *, timeout: int) -> Any:
    return urllib.request.build_opener(_NoRedirect()).open(request, timeout=timeout)


class Client:
    """One connection at a time; no retries or refusal workarounds."""

    def __init__(self, max_bytes: int = 64 * 1024 * 1024):
        self.max_bytes = max_bytes
        self._used = False

    def get(self, url: str) -> bytes:
        if not url.startswith(BASE + "/"):
            raise ValueError("URL must use the official BOEM origin")
        if self._used:
            time.sleep(2)
        self._used = True
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        # Redirects could cross origins or bypass robots checks: reject them.
        with _open(request, timeout=30) as response:
            if response.geturl() != url:
                raise ValueError("Unexpected redirect")
            chunks, total = [], 0
            while chunk := response.read(min(65536, self.max_bytes + 1 - total)):
                total += len(chunk)
                if total > self.max_bytes:
                    raise ValueError("Response exceeds size limit")
                chunks.append(chunk)
        return b"".join(chunks)


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href", "") or ""
            self.links.add(urllib.parse.unquote(href))


def validate_listing(html: str, names: Sequence[str]) -> None:
    parser = _Links()
    parser.feed(html)
    for name in names:
        relative = f"/FieldReserves/Files/{name}"
        if relative not in parser.links and BASE + relative not in parser.links:
            raise ValueError(f"Listing missing expected member: {name}")


def record(url: str, payload: bytes, retrieved_utc: str) -> dict:
    return {
        "source_url": url,
        "retrieved_utc": retrieved_utc,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def emit_manifest(records: list[dict], *, terms: str) -> str:
    return (
        json.dumps(
            {
                "schema_version": 1,
                "licence": "not stated by the source",
                "terms_quote": terms,
                "terms_url": TERMS_URL,
                "records": records,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def fixture_manifest(root: Path) -> str:
    """Emit provenance of synthetic bytes using fixed fixture metadata."""
    records = []
    for name in ("synthetic_history.csv", "synthetic_master.csv"):
        item = record(
            "synthetic://" + name, (root / name).read_bytes(), "2026-10-11T00:00:00Z"
        )
        item["data_kind"] = "synthetic"
        records.append(item)
    return emit_manifest(records, terms="not stated by the source")


def fetch_family(cache_root: Path) -> Path:
    """Verify robots, disclaimer and exact listings before fetching archives."""
    cache_root.mkdir(parents=True, exist_ok=True)
    if any(cache_root.iterdir()):
        raise FileExistsError("Preserving existing cache contents; use a fresh directory")
    client, records = Client(), []

    def get(url: str, filename: str) -> bytes:
        target = cache_root / filename
        if target.exists():
            raise FileExistsError(f"Preserving existing output: {filename}")
        body = client.get(url)
        stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        records.append(record(url, body, stamp))
        target.write_bytes(body)
        if target.read_bytes() != body:
            raise OSError("Saved source failed readback")
        return body

    robots = get(BASE + "/robots.txt", "robots.txt").decode("utf-8")
    policy = urllib.robotparser.RobotFileParser()
    policy.parse(robots.splitlines())
    urls = [TERMS_URL, VINTAGE_LISTING, FAMILY_LISTING] + [
        BASE + "/FieldReserves/Files/" + urllib.parse.quote(name) for name in FILES
    ]
    if not all(policy.can_fetch(USER_AGENT, url) for url in urls):
        raise ValueError("Source robots policy refuses automated access")
    verify_terms(get(TERMS_URL, "terms.html"))
    vintage = get(VINTAGE_LISTING, "vintage.html").decode("utf-8")
    family = get(FAMILY_LISTING, "family.html").decode("utf-8")
    validate_listing(vintage, FILES[:2])
    validate_listing(family, FILES[2:])
    for name, url in zip(FILES, urls[3:]):
        body = get(url, name)
        if not body.startswith(b"PK\x03\x04"):
            raise ValueError(f"Expected ZIP, received other content: {name}")
    manifest = cache_root / "manifest.json"
    manifest.write_text(emit_manifest(records, terms=DISCLAIMER), encoding="utf-8")
    return manifest
