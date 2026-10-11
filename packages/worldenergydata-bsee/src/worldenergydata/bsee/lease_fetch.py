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
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

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
    if (
        parsed.scheme != "https"
        or parsed.netloc != "www.data.bsee.gov"
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Only public BSEE HTTPS source URLs are permitted")


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
    pause = sleep if sleep is not None else time.sleep
    for attempt in range(2):
        pause(REQUEST_INTERVAL)
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=45) as response:
                _validate_url(response.geturl())
                body = response.read(100 * 1024 * 1024 + 1)
                if len(body) > 100 * 1024 * 1024:
                    raise ValueError("Source exceeds download size limit")
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
        except HTTPError as error:
            if error.code in {401, 403, 429}:
                raise PermissionError(
                    f"BSEE automated access refused: HTTP {error.code}"
                ) from error
            if error.code < 500 or attempt:
                raise
        except (URLError, TimeoutError):
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
    except (PermissionError, HTTPError, URLError, TimeoutError, ValueError) as error:
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
