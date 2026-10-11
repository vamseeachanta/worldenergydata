"""Explicit source permissions, identification and conservative request pacing."""

import logging
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit


class TermsDenied(RuntimeError):
    """Network collection requires a recorded source permission."""


class BudgetExceeded(RuntimeError):
    """The rolling per-host request budget is exhausted."""


class UnreachableTarget(RuntimeError):
    """A target could not be reached from the executing machine."""


def origin_of(url: str) -> str:
    """Normalize an HTTP origin; credentials and fragments are unsupported."""
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("A public HTTP(S) source URL is required")
    if parts.username or parts.password or parts.fragment:
        raise ValueError("Source URL must not contain credentials or fragments")
    port = parts.port or (443 if parts.scheme == "https" else 80)
    host = parts.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    return f"{parts.scheme}://{host}:{port}"


@dataclass(frozen=True)
class FetchConfig:
    """Cache location and identification have no machine-specific defaults."""

    cache_root: Path | str
    contact: str
    fallback_interval: float = 2.0
    budget_requests: int = 30
    budget_window: float = 60.0
    timeout: float = 15.0
    max_retries: int = 2

    def __post_init__(self) -> None:
        if not str(self.cache_root).strip():
            raise ValueError("cache root is required")
        if "@" not in self.contact or any(c.isspace() for c in self.contact):
            raise ValueError("contact address is required")
        for value in (self.fallback_interval, self.budget_window, self.timeout):
            if not math.isfinite(value) or value <= 0:
                raise ValueError(
                    "Pacing, window and timeout must be finite and positive"
                )
        if self.budget_requests < 1 or self.max_retries < 0:
            raise ValueError("Invalid request or retry budget")

    @classmethod
    def from_env(cls, *, contact: str) -> "FetchConfig":
        root = os.environ.get("STATE_FETCH_CACHE_ROOT")
        if not root:
            raise ValueError("Set STATE_FETCH_CACHE_ROOT or configure cache_root")
        return cls(cache_root=root, contact=contact)

    @property
    def user_agent(self) -> str:
        return f"worldenergydata-public-records/1.0 (contact: {self.contact})"


@dataclass(frozen=True)
class TermsCheck:
    """Caller-supplied recorded decision, not an automatic terms assessment."""

    origin: str
    terms_url: str
    checked_at: str
    bulk_allowed: bool

    def __post_init__(self) -> None:
        if type(self.bulk_allowed) is not bool:
            raise ValueError("Bulk permission must be an explicit Boolean")

    def permits(self, url: str) -> bool:
        checked = datetime.fromisoformat(self.checked_at)
        offset = checked.utcoffset()
        if offset is None or offset.total_seconds() != 0:
            raise ValueError("Terms check time must be UTC")
        if checked > datetime.now(timezone.utc):
            raise ValueError("Terms check time must not be in the future")
        origin_of(self.terms_url)
        return self.bulk_allowed and origin_of(self.origin) == origin_of(url)


def _number(value: str | None) -> float | None:
    try:
        number = float(value) if value is not None else None
        return (
            number
            if number is not None and math.isfinite(number) and number >= 0
            else None
        )
    except ValueError:
        return None


def header_delay(
    headers: Mapping[str, str],
    fallback: float,
    window: float,
    now: datetime | None = None,
) -> float:
    """Return minimum spacing; reset values are delta seconds, not epoch time.

    Vendor max tokens alone do not establish window duration or numerator
    semantics. Use the configured window and the smaller possible remaining
    balance. This is a conservative assumption, not measured capacity.
    """
    h = {key.lower(): value for key, value in headers.items()}
    delay = fallback
    remaining = _number(h.get("ratelimit-remaining"))
    reset = _number(h.get("ratelimit-reset"))
    if remaining is not None:
        horizon = reset if reset is not None else window
        delay = max(delay, horizon / max(remaining, 1))
    elif reset is not None:
        delay = max(delay, reset)
    for policy in h.get("ratelimit-limit", "").split(","):
        parts = policy.split(";")
        limit = _number(parts[0])
        advertised_window = next(
            (_number(p.strip()[2:]) for p in parts[1:] if p.strip().startswith("w=")),
            None,
        )
        if limit is not None and limit > 0:
            delay = max(delay, (advertised_window or window) / limit)
    delay = max(delay, _vendor_delay(h, window))
    retry = h.get("retry-after")
    seconds = _number(retry)
    if seconds is None and retry:
        try:
            date = parsedate_to_datetime(retry)
            if date.tzinfo is not None:
                seconds = max(
                    0.0, (date - (now or datetime.now(timezone.utc))).total_seconds()
                )
        except (ValueError, TypeError, OverflowError):
            pass
    return max(delay, seconds or 0.0)


def _vendor_delay(headers: Mapping[str, str], window: float) -> float:
    cost = _number(headers.get("x-dotrequest-cost"))
    available = _number(headers.get("x-dotratelimit-toks-remaining"))
    if available is None:
        parts = headers.get("x-dotratelimit-toks-max", "").split("/")
        if len(parts) == 2:
            balance, capacity = map(_number, parts)
            if balance is not None and capacity is not None and balance <= capacity:
                available = min(balance, capacity - balance)
    if cost is None or cost <= 0 or available is None:
        return 0.0
    reset = _number(headers.get("x-dotratelimit-reset"))
    horizon = reset if reset is not None else window
    return horizon / max(available / cost, 1)


def choose_route(
    bulk_urls: list[str], crawl_url: str, *, use_crawl: bool = False
) -> str:
    """Prefer caller-verified official bulk routes; never crawl to discover them."""
    for url in [*bulk_urls, crawl_url]:
        origin_of(url)
    if bulk_urls and not use_crawl:
        return bulk_urls[0]
    logging.getLogger(__name__).warning(
        "crawl selected: %s; available official bulk routes: %s", crawl_url, bulk_urls
    )
    return crawl_url
