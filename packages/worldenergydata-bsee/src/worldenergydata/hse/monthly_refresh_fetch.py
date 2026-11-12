# ABOUTME: Fetch public HSE files with robots checks and per-host request pacing.
# ABOUTME: Validate content and catalogue archive members without extracting them.

from __future__ import annotations

import csv
import hashlib
import io
import json
import lzma
import re
import time
import zipfile
import zlib
from collections.abc import Callable
from html.parser import HTMLParser
from typing import Any
from urllib.parse import unquote, urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx


def file_record(
    url: str, timestamp: str, response: httpx.Response | None = None
) -> dict:
    """Describe only the response observed for this data request."""
    return {
        "url": url,
        "effective_url": str(response.url) if response is not None else url,
        "http_status": response.status_code if response is not None else None,
        "bytes": len(response.content) if response is not None else 0,
        "sha256": (
            hashlib.sha256(response.content).hexdigest()
            if response is not None
            else None
        ),
        "content_type": (
            response.headers.get("content-type") if response is not None else None
        ),
        "etag": response.headers.get("etag") if response is not None else None,
        "last_modified": (
            response.headers.get("last-modified") if response is not None else None
        ),
        "retrieved_at_utc": timestamp,
        "members": [],
    }


def validate_url(url: Any) -> str:
    """Require a well-formed HTTPS URL without embedded credentials."""
    try:
        if not isinstance(url, str) or any(
            c.isspace() or not c.isprintable() for c in url
        ):
            raise ValueError
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or "\\" in url
        ):
            raise ValueError
        _ = parsed.port
    except (ValueError, TypeError):
        raise ValueError("expected an HTTPS URL without credentials") from None
    return url


def url_filename(url: str, expect: str) -> str:
    """Return one portable filename; reserve collector metadata names."""
    name = unquote(urlsplit(url).path.rsplit("/", 1)[-1]) or f"index.{expect}"
    if (
        name in {".", ".."}
        or name.lower() in {"manifest.json", "links.json", "latest.json"}
        or any(c in name for c in '/\\:*?"<>|')
        or any(not c.isprintable() for c in name)
        or name.endswith((".", " "))
    ):
        raise ValueError("URL filename is unsafe or reserved")
    return name


class FetchError(Exception):
    """A terminal access or transport failure; no automatic retry is permitted."""

    def __init__(
        self, status: str, reason: str, url: str, response: httpx.Response | None = None
    ) -> None:
        super().__init__(reason)
        self.status, self.url, self.response = status, url, response


class CitizenFetcher:
    """Cache robots policy per origin and pace every request per hostname."""

    def __init__(
        self,
        client: httpx.Client,
        user_agent: str,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.client, self.user_agent = client, user_agent
        self.sleep, self.clock = sleep, clock
        self.last_request: dict[str, float] = {}
        self.policies: dict[str, RobotFileParser | FetchError | None] = {}

    def _get(self, url: str) -> httpx.Response:
        host = urlsplit(url).hostname or ""
        if host in self.last_request:
            delay = 1.0 - (self.clock() - self.last_request[host])
            if delay > 0:
                self.sleep(delay)
        self.last_request[host] = self.clock()
        return self.client.get(
            url,
            headers={"User-Agent": self.user_agent},
            follow_redirects=False,
            auth=None,
        )

    def _request(self, url: str, *, robots: bool = False) -> httpx.Response:
        for _ in range(11):
            try:
                validate_url(url)
            except ValueError as exc:
                raise FetchError("failed", str(exc), url) from exc
            if not robots:
                self._check_robots(url)
            try:
                response = self._get(url)
            except httpx.RequestError as exc:
                raise FetchError("failed", str(exc), url) from exc
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location")
                if not location:
                    raise FetchError(
                        "failed", "redirect has no Location", url, response
                    )
                try:
                    target = urljoin(url, location)
                    validate_url(target)
                except ValueError as exc:
                    raise FetchError(
                        "failed",
                        "redirect requires HTTPS without credentials",
                        url,
                        response,
                    ) from exc
                url = target
                continue
            return response
        raise FetchError("failed", "redirect limit exceeded", url)

    def _check_robots(self, url: str) -> None:
        parsed = urlsplit(url)
        origin = f"https://{parsed.netloc}"
        if origin not in self.policies:
            self.policies[origin] = self._robots_policy(origin)
        policy = self.policies[origin]
        if isinstance(policy, FetchError):
            raise FetchError(policy.status, str(policy), url)
        if policy is not None and not policy.can_fetch(self.user_agent, url):
            raise FetchError(
                "disallowed_by_robots", f"disallowed by {origin}/robots.txt", url
            )

    def _robots_policy(self, origin: str) -> RobotFileParser | FetchError | None:
        url = origin + "/robots.txt"
        try:
            response = self._request(url, robots=True)
        except FetchError as exc:
            return FetchError("robots_unavailable", f"robots unavailable: {exc}", url)
        code = response.status_code
        if code in {401, 403, 429}:
            return FetchError(
                "blocked", f"robots.txt returned HTTP {code}", url, response
            )
        if 400 <= code < 500:
            return None
        if not 200 <= code < 300:
            return FetchError(
                "robots_unavailable", f"robots.txt returned HTTP {code}", url, response
            )
        parser = RobotFileParser(url)
        parser.parse(response.text.splitlines())
        return parser

    def fetch(self, url: str) -> httpx.Response:
        response = self._request(url)
        code = response.status_code
        if code in {401, 403, 429}:
            raise FetchError(
                "blocked", f"data URL returned HTTP {code}", str(response.url), response
            )
        if not 200 <= code < 300:
            raise FetchError(
                "failed", f"data URL returned HTTP {code}", str(response.url), response
            )
        return response


def check_content(
    payload: bytes, expect: str, encoding: str = "utf-8-sig"
) -> list[dict[str, Any]]:
    """Light format checks, including ZIP integrity and header-excluded row counts."""
    if expect in {"zip", "xlsx"}:
        if not payload.startswith(b"PK"):
            raise ValueError(f"expected {expect} archive")
        with zipfile.ZipFile(io.BytesIO(payload)) as zipped:
            try:
                if zipped.testzip() is not None:
                    raise ValueError("archive member failed CRC check")
            except (zlib.error, lzma.LZMAError) as exc:
                raise ValueError(f"invalid archive compression: {exc}") from exc
            if expect == "xlsx" and not {
                "[Content_Types].xml",
                "xl/workbook.xml",
            } <= set(zipped.namelist()):
                raise ValueError("expected an XLSX workbook")
            members = []
            for member in zipped.infolist():
                record: dict[str, Any] = {
                    "name": member.filename,
                    "bytes": member.file_size,
                }
                if not member.is_dir() and member.filename.lower().endswith(
                    (".txt", ".csv")
                ):
                    with zipped.open(member) as stream:
                        lines = io.TextIOWrapper(
                            stream, encoding="utf-8-sig", errors="replace"
                        )
                        record["rows"] = max(0, sum(1 for _ in lines) - 1)
                members.append(record)
            return members if expect == "zip" else []
    if expect == "pdf":
        if not payload.startswith(b"%PDF-"):
            raise ValueError("expected PDF signature")
        return []
    text = payload.decode("utf-8-sig" if expect == "json" else encoding).strip()
    html = bool(re.search(r"<(?:!doctype\s+html|html|head|body|a\b|div\b)", text, re.I))
    if expect == "html" and not html:
        raise ValueError("expected HTML markup")
    if expect == "json":
        json.loads(text)
    if expect == "csv":
        if not text or html or "\0" in text:
            raise ValueError("expected delimited text")
        try:
            csv.Sniffer().sniff(text[:8192], delimiters=",;\t|")
        except csv.Error as exc:
            raise ValueError("expected delimited text") from exc
    return []


class ListingParser(HTMLParser):
    """Collect document URLs and visible link text, without fetching documents."""

    def __init__(
        self,
        base_url: str,
        link_patterns: tuple[str, ...] | None = None,
        link_classes: tuple[str, ...] | None = None,
    ) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url, self.href = base_url, None
        self.filtered = link_patterns is not None or link_classes is not None
        self.patterns = tuple(re.compile(pattern) for pattern in link_patterns or ())
        self.classes = frozenset(link_classes or ())
        self.anchor_classes: set[str] = set()
        self.text: list[str] = []
        self.links: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            attributes = dict(attrs)
            self.href = attributes.get("href")
            self.anchor_classes = set((attributes.get("class") or "").split())
            self.text = []

    def handle_data(self, data: str) -> None:
        if self.href is not None:
            self.text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self.href is None:
            return
        try:
            url = urljoin(self.base_url, self.href)
            parsed = urlsplit(url)
        except ValueError:
            self.href = None
            return
        if self.filtered:
            keep = any(pattern.search(url) for pattern in self.patterns) or bool(
                self.classes & self.anchor_classes
            )
        else:
            keep = (
                parsed.path.lower().endswith(".pdf")
                or "/sites/" in url
                or "/media/" in url
            )
        if parsed.scheme in {"http", "https"} and keep and not self.links.get(url):
            self.links[url] = " ".join("".join(self.text).split())
        self.href = None
