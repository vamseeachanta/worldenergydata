"""Synchronous, bounded, cache-first state-regulator fetching."""

import socket
import time
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .policy import (
    BudgetExceeded,
    FetchConfig,
    ResponseTooLarge,
    TermsCheck,
    TermsDenied,
    UnreachableTarget,
    header_delay,
    origin_of,
)
from .storage import CacheStore, FetchResult, atomic_json, validate_response


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        return None


class Fetcher:
    """All network attempts share a persisted rolling per-host budget."""

    def __init__(
        self,
        config: FetchConfig,
        terms: list[TermsCheck],
        *,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config
        self.terms = terms
        self.clock = clock
        self.sleep = sleep
        self.store = CacheStore(config.cache_root)
        self.opener = build_opener(_NoRedirect())

    def _host(self, url: str) -> str:
        origin_of(url)
        return str(urlsplit(url).hostname).lower()

    def _reserve(self, url: str) -> None:
        host = self._host(url)
        state = self.store.state["hosts"].setdefault(
            host, {"attempts": [], "next_at": 0}
        )
        delay = max(0.0, state["next_at"] - self.clock())
        if delay > self.config.max_sleep_seconds:
            resume = datetime.fromtimestamp(state["next_at"], timezone.utc)
            raise BudgetExceeded(f"Wait for {host}; resume at {resume.isoformat()} UTC")
        if delay:
            self.sleep(delay)
        now = self.clock()
        state["attempts"] = [
            t for t in state["attempts"] if t > now - self.config.budget_window
        ]
        if len(state["attempts"]) >= self.config.budget_requests:
            raise BudgetExceeded(
                f"Request budget exhausted for {host}; resume after the window"
            )
        state["attempts"].append(now)
        state["next_at"] = now + self.config.fallback_interval
        self.store.save()

    def _cooldown(self, url: str, headers: Any) -> None:
        delay = header_delay(
            dict(headers),
            self.config.fallback_interval,
            self.config.budget_window,
            datetime.fromtimestamp(self.clock(), timezone.utc),
        )
        self.store.state["hosts"][self._host(url)]["next_at"] = self.clock() + delay
        self.store.save()

    def fetch(self, url: str) -> FetchResult:
        """First uncached fetch is preflight; no duplicate probe connection."""
        origin_of(url)
        # Earlier recorded permission keeps cached data readable after withdrawal.
        # This path makes no network request; purging is an explicit operator action.
        cached = self.store.get(url)
        if cached:
            return cached
        permission = next((check for check in self.terms if check.permits(url)), None)
        if permission is None:
            raise TermsDenied(f"No recorded bulk permission for {origin_of(url)}")
        atomic_json(
            self.store.root / "terms-checks.json", [asdict(t) for t in self.terms]
        )
        for attempt in range(self.config.max_retries + 1):
            self._reserve(url)
            try:
                payload, headers = self._request(url)
            except ResponseTooLarge as oversized:
                self._cooldown(url, oversized.headers)
                raise
            except HTTPError as error:
                self._cooldown(url, error.headers)
                error.close()
                if error.code != 429 or attempt == self.config.max_retries:
                    raise
            else:
                self._cooldown(url, headers)
                return self.store.put(
                    url, payload, headers, asdict(permission), retry_count=attempt
                )
        raise AssertionError("Retry loop exhausted without a result")

    def _request(self, url: str) -> tuple[bytes, dict[str, str]]:
        request = Request(url, headers={"User-Agent": self.config.user_agent})
        try:
            with self.opener.open(request, timeout=self.config.timeout) as response:
                cap = self.config.max_response_bytes
                length = response.headers.get("Content-Length")
                try:
                    advertised = int(length) if length is not None else 0
                except ValueError:
                    advertised = 0
                message = f"Response from {origin_of(url)} exceeds cap of {cap} bytes"
                if advertised > cap:
                    raise ResponseTooLarge(message, dict(response.headers))
                payload = response.read(cap + 1)
                if len(payload) > cap:
                    raise ResponseTooLarge(message, dict(response.headers))
                validate_response(
                    url, payload, dict(response.headers), response.getcode()
                )
                return payload, dict(response.headers)
        except HTTPError:
            raise
        except (URLError, OSError) as error:
            reason = error.reason if isinstance(error, URLError) else error
            layer = (
                "name-resolution"
                if isinstance(reason, socket.gaierror)
                else "network-reachability"
            )
            raise UnreachableTarget(
                f"{layer}: target={origin_of(url)} machine=the build host; {reason}"
            ) from error

    def preflight(self, url: str) -> FetchResult:
        """Reachability is verified by the first budgeted fetch, retaining its bytes."""
        return self.fetch(url)

    def run(
        self, urls: Iterable[str], *, dry_run: bool = False
    ) -> list[FetchResult] | dict[str, Any]:
        if dry_run:
            return self.project(urls)
        return [self.preflight(url) for url in urls]

    def project(self, urls: Iterable[str]) -> dict[str, Any]:
        """Offline baseline estimate; retries/latency and unknown windows remain uncertain."""
        pending: dict[str, int] = {}
        unique = list(dict.fromkeys(urls))
        for url in unique:
            host = self._host(url)
            if self.store.get(url) is None:
                pending[host] = pending.get(host, 0) + 1
        count = sum(pending.values())
        estimate = 0.0
        for host, requests in pending.items():
            estimate += self._project_host(host, requests)
        return {
            "projected_requests": count,
            "cached_urls": len(unique) - count,
            "estimated_seconds": estimate,
            "maximum_attempts": count * (self.config.max_retries + 1),
            "terms_permitted": all(
                any(t.permits(url) for t in self.terms) for url in unique
            ),
            "assumptions": (
                "Serial pacing baseline; excludes latency and retries. "
                "Unknown vendor window uses configured window. "
                "Budget exhaustion stops execution for later resume."
            ),
        }

    def _project_host(self, host: str, requests: int) -> float:
        """Simulate serial reservations without mutating the persisted budget."""
        now = self.clock()
        state = self.store.state["hosts"].get(host, {"attempts": [], "next_at": 0})
        attempts = sorted(
            float(t) for t in state["attempts"] if t > now - self.config.budget_window
        )
        projected = max(now, float(state["next_at"]))
        for _ in range(requests):
            attempts = [
                t for t in attempts if t > projected - self.config.budget_window
            ]
            if len(attempts) >= self.config.budget_requests:
                projected = max(projected, attempts[0] + self.config.budget_window)
                attempts = [
                    t for t in attempts if t > projected - self.config.budget_window
                ]
            attempts.append(projected)
            projected += self.config.fallback_interval
        return projected - now
