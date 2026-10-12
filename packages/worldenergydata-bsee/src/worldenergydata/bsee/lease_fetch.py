"""Sequential public BSEE downloads with immutable raw files and provenance."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

PAGE = "https://www.data.bsee.gov/Main/Leasing.aspx"
TERMS = {
    "source_url": "https://www.data.bsee.gov/Main/HtmlPage.aspx?page=Disclaimer",
    "license": "No explicit license grant stated on the download page.",
    "limitations": (
        "Working database; errors may exist. Not a legal document; "
        "not for navigational use."
    ),
}
USER_AGENT = (
    "WorldEnergyData (+https://github.com/vamseeachanta/worldenergydata; "
    "public lease research, sequential requests)"
)
REQUEST_INTERVAL = 2.0


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"Rejected source URL scheme: {parsed.scheme!r}")
    if parsed.netloc != "www.data.bsee.gov" or parsed.username or parsed.password:
        raise ValueError(f"Rejected source URL host: {parsed.hostname!r}")


def _open_validated_url(url: str) -> Any:
    return httpx.stream(
        "GET",
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=45,
        follow_redirects=False,
    )


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.archives: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href and urlparse(href).path.endswith(".zip"):
            url = urljoin(PAGE, href)
            _validate_url(url)
            self.archives[Path(urlparse(url).path).name] = url


def discover_archives(html: str) -> dict[str, str]:
    """Resolve archive URLs from actual source anchors, never guessed endpoints."""
    parser = _Links()
    parser.feed(html)
    return parser.archives


def _read(url: str, *, sleep: Callable[[float], None] | None = None) -> bytes:
    _validate_url(url)
    pause = sleep if sleep is not None else time.sleep
    for attempt in range(2):
        pause(REQUEST_INTERVAL)
        try:
            with _open_validated_url(url) as response:
                response.raise_for_status()
                _validate_url(str(response.url))
                body = bytearray()
                for chunk in response.iter_bytes(chunk_size=65536):
                    if len(body) + len(chunk) > 100 * 1024 * 1024:
                        raise ValueError("Source exceeds download size limit")
                    body.extend(chunk)
                if any(
                    marker in body[:65536].lower()
                    for marker in (
                        b"verify you are human",
                        b"cf-chl-",
                        b"captcha",
                        b"access denied",
                    )
                ):
                    raise PermissionError(
                        "BSEE automated access challenge; retrieval stopped"
                    )
                return bytes(body)
        except httpx.HTTPStatusError as error:
            if error.response.status_code in {401, 403, 429}:
                raise PermissionError(
                    f"BSEE automated access refused: HTTP {error.response.status_code}"
                ) from error
            if error.response.status_code < 500 or attempt:
                raise
        except (httpx.RequestError, TimeoutError):
            if attempt:
                raise
    raise RuntimeError("Download attempts exhausted")


def download(
    url: str, destination: Path, *, sleep: Callable[[float], None] | None = None
) -> dict[str, Any]:
    """Save once, read back, and return source-byte provenance; never overwrite."""
    _validate_url(url)
    if destination.exists():
        raise FileExistsError(
            "Raw destination already exists; choose a new retrieval directory"
        )
    body = _read(url, sleep=sleep)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        stream.write(body)
    saved = destination.read_bytes()
    if saved != body:
        raise OSError("Downloaded source failed byte-for-byte readback")
    record = {
        "file": destination.name,
        "source_url": url,
        "retrieved_at_utc": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "sha256": hashlib.sha256(saved).hexdigest(),
        "size_bytes": len(saved),
        "terms": dict(TERMS),
    }

    _save_record(destination.with_name(destination.name + ".provenance.json"), record)
    return record


def _save_record(path: Path, record: dict[str, Any]) -> None:
    path.write_text(json.dumps(record, indent=2) + "\n")
    if json.loads(path.read_text()) != record:
        raise OSError("Provenance readback mismatch")


def _fetch_bundle(
    schema: dict[str, Any], destination: Path, sleep: Callable[[float], None] | None
) -> list[dict[str, Any]]:
    """Fetch discovery page, terms, verified layouts and four packages serially."""
    records = [download(PAGE, destination / "leasing-page.html", sleep=sleep)]
    links = discover_archives((destination / "leasing-page.html").read_text())
    records[0]["archive_links"] = links
    records.append(
        download(TERMS["source_url"], destination / "Disclaimer.html", sleep=sleep)
    )
    for kind, spec in schema["tables"].items():
        archive = spec["archive"]
        if archive not in links:
            raise ValueError(f"Expected package absent from source page: {archive}")
        records.append(
            download(
                spec["layout_url"], destination / f"{kind}-layout.html", sleep=sleep
            )
        )
        records.append(download(links[archive], destination / archive, sleep=sleep))
    return records


def fetch_bundle(
    schema: dict[str, Any],
    destination: Path,
    *,
    sleep: Callable[[float], None] | None = None,
) -> list[dict[str, Any]]:
    """Preserve provenance for partial fetches and record a stopped retrieval."""
    try:
        return _fetch_bundle(schema, destination, sleep)
    except (PermissionError, httpx.HTTPError, TimeoutError, ValueError) as error:
        destination.mkdir(parents=True, exist_ok=True)
        reason = (
            str(error) if isinstance(error, PermissionError) else type(error).__name__
        )
        _save_record(
            destination / "interruption.json",
            {
                "state": "stopped",
                "reason": reason,
                "observed_at_utc": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
                "provenance": "Each completed download has a sibling .provenance.json record",
            },
        )
        raise
