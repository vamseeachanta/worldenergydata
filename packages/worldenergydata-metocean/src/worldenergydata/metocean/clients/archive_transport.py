"""Bounded, anonymous archive downloads with serialized requests per host.

Limits are decimal bytes. Retry delays are at least sixty seconds; requests
start at least 1.1 seconds apart. Reuse one instance for a complete update run
so its byte and per-host request budgets include every downloaded resource.
"""

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from types import MappingProxyType
from typing import Callable, Mapping
from urllib.parse import urlsplit

import httpx

USER_AGENT = (
    "worldenergydata-metocean (https://github.com/vamseeachanta/worldenergydata)"
)
_TEMPORARY = {429, 500, 502, 503, 504}
_HEADERS = {"if-none-match", "if-modified-since", "accept"}


class ArchiveLimitError(RuntimeError):
    """The configured download budget would be exceeded."""


@dataclass(frozen=True)
class Download:
    """Immutable response snapshot; content contains HTTP-decoded bytes."""

    url: str
    content: bytes
    status_code: int
    headers: Mapping[str, str]
    fetched_at: datetime


@dataclass
class _Host:
    lock: threading.Lock = field(default_factory=threading.Lock)
    last_request: float | None = None


_HOSTS: dict[str, _Host] = {}
_HOSTS_LOCK = threading.Lock()


class ArchiveTransport:
    """Anonymous HTTPS GET transport; injected clients remain caller-owned."""

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        max_file_bytes: int = 300_000_000,
        max_total_bytes: int = 2_000_000_000,
        max_requests_per_host: int = 2_000,
        interval: float = 1.1,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        utcnow: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        if not (0 < max_file_bytes <= 300_000_000):
            raise ValueError("File limit must be within 300 MB")
        if not (0 < max_total_bytes <= 2_000_000_000):
            raise ValueError("Run limit must be within 2 GB")
        if not (0 < max_requests_per_host <= 2_000) or interval < 1.1:
            raise ValueError("Request limits must not exceed the archive policy")
        self.client = (
            client
            if client is not None
            else httpx.Client(timeout=60, trust_env=False, follow_redirects=False)
        )
        self._owns_client = client is None
        self.max_file_bytes = max_file_bytes
        self.max_total_bytes = max_total_bytes
        self.max_requests_per_host = max_requests_per_host
        self.interval = interval
        self.sleep, self.clock, self.utcnow = sleep, clock, utcnow
        self.bytes_downloaded = 0
        self.requests_by_host: dict[str, int] = {}
        self._run_lock = threading.Lock()
        self._closed = False

    def download(self, url: str, headers: Mapping[str, str] | None = None) -> Download:
        """Fetch a complete response; redirects and non-temporary errors fail."""
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.fragment
        ):
            raise ValueError(
                "An HTTPS URL without user information or fragment is required"
            )
        supplied = {key.lower(): value for key, value in (headers or {}).items()}
        if supplied.keys() - _HEADERS:
            raise ValueError("Only conditional and Accept headers are supported")
        supplied["user-agent"] = USER_AGENT
        supplied["accept-encoding"] = "identity"
        host = parsed.hostname.lower()
        with _HOSTS_LOCK:
            state = _HOSTS.setdefault(host, _Host())
        with self._run_lock, state.lock:
            if self._closed:
                raise RuntimeError("Archive transport is closed")
            return self._download(url, supplied, host, state)

    def _download(self, url, headers, host, state):
        for attempt in range(3):
            count = self.requests_by_host.get(host, 0)
            if count >= self.max_requests_per_host:
                raise ArchiveLimitError("Per-host request budget exhausted")
            if self.bytes_downloaded >= self.max_total_bytes:
                raise ArchiveLimitError("Run byte budget exhausted")
            if state.last_request is not None:
                delay = self.interval - (self.clock() - state.last_request)
                if delay > 0:
                    self.sleep(delay)
            state.last_request = self.clock()
            self.requests_by_host[host] = count + 1
            request = httpx.Request("GET", url, headers=headers)
            response = self.client.send(
                request, stream=True, auth=None, follow_redirects=False
            )
            try:
                if response.status_code in _TEMPORARY and attempt < 2:
                    delay = self._retry_delay(
                        response.headers.get("retry-after"), attempt
                    )
                else:
                    if response.status_code != 304:
                        response.raise_for_status()
                    content = (
                        b"" if response.status_code == 304 else self._read(response)
                    )
                    return Download(
                        url,
                        content,
                        response.status_code,
                        MappingProxyType(dict(response.headers)),
                        self.utcnow(),
                    )
            finally:
                response.close()
            self.sleep(delay)
        raise RuntimeError("Retry loop exhausted without a response")

    def _read(self, response: httpx.Response) -> bytes:
        chunks = []
        size = 0
        chunk_size = min(
            65_536,
            self.max_file_bytes + 1,
            self.max_total_bytes - self.bytes_downloaded + 1,
        )
        for chunk in response.iter_bytes(chunk_size=chunk_size):
            size += len(chunk)
            self.bytes_downloaded += len(chunk)
            if size > self.max_file_bytes:
                raise ArchiveLimitError("Decoded file exceeds file byte budget")
            if self.bytes_downloaded > self.max_total_bytes:
                raise ArchiveLimitError("Decoded response exceeds run byte budget")
            chunks.append(chunk)
        return b"".join(chunks)

    def _retry_delay(self, value: str | None, attempt: int) -> float:
        minimum = 60.0 * (2**attempt)
        if value is None:
            return minimum
        try:
            delay = float(value)
        except ValueError:
            try:
                timestamp = parsedate_to_datetime(value)
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                delay = (timestamp - self.utcnow()).total_seconds()
            except (TypeError, ValueError, OverflowError):
                return minimum
        return max(minimum, delay)

    def close(self) -> None:
        """Close owned connections and prevent additional downloads."""
        with self._run_lock:
            self._closed = True
            if self._owns_client:
                self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
