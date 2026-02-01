"""Abstract base class for LNG terminal data collectors.

Provides HTTP client with rate limiting and retry, a collect lifecycle
(fetch -> parse -> validate), source citation tracking, and a JSON-based
cache layer controlled by :pyclass:`RefreshMode`.
"""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx

from ..config import ScraperConfig, get_cache_dir, get_config
from ..constants import RETRYABLE_HTTP_CODES, RefreshMode, SourceReliability
from ..exceptions import LNGCollectionError
from ..models.data_quality import SourceCitation
from ..models.terminal import LNGTerminal


class BaseCollector(ABC):
    """Abstract base class for LNG terminal data collectors.

    Parameters
    ----------
    source_name:
        Identifier for this data source (used in citations and cache keys).
    refresh_mode:
        Controls cache vs. fresh fetch behavior.  When *None* the value
        from ``config.cache.default_refresh_mode`` is used.
    """

    source_name: str = "unknown"
    source_reliability: SourceReliability = SourceReliability.MEDIUM

    def __init__(
        self,
        source_name: str | None = None,
        refresh_mode: RefreshMode | None = None,
    ) -> None:
        if source_name is not None:
            self.source_name = source_name

        self.config = get_config()
        self._scraper: ScraperConfig = self.config.scraper
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Resolve refresh mode from explicit arg -> config default -> FULL
        if refresh_mode is not None:
            self.refresh_mode = refresh_mode
        else:
            self.refresh_mode = RefreshMode(self.config.cache.default_refresh_mode)

        self.client = httpx.Client(
            timeout=self._scraper.request_timeout,
            headers={"User-Agent": self._scraper.user_agent},
            follow_redirects=True,
        )

        self._last_request_time: float | None = None
        self._request_count: int = 0

    # -- Cache helpers -------------------------------------------------------

    @property
    def _cache_path(self) -> Path:
        """Path to the JSON cache file for this source."""
        return get_cache_dir() / f"{self.source_name}_cache.json"

    @property
    def _cache_meta_path(self) -> Path:
        """Path to the cache metadata file."""
        return get_cache_dir() / f"{self.source_name}_meta.json"

    def _read_cache(self) -> list[dict] | None:
        """Read cached terminal dicts if the cache exists and is not expired.

        Returns *None* when the cache is missing, unreadable, or expired
        (based on ``config.cache.max_age_seconds``).
        """
        if not self._cache_path.exists() or not self._cache_meta_path.exists():
            return None

        try:
            meta = json.loads(self._cache_meta_path.read_text(encoding="utf-8"))
            collected_at = datetime.fromisoformat(meta["collected_at"])
            age_seconds = (datetime.utcnow() - collected_at).total_seconds()

            # Check per-source TTL first, fall back to global max_age
            source_cfg = self.config.sources.get(self.source_name)
            ttl = (
                source_cfg.cache_ttl
                if source_cfg
                else self.config.cache.max_age_seconds
            )
            if ttl and age_seconds > ttl:
                self.logger.info(
                    "Cache for '%s' expired (age=%.0fs, ttl=%ds)",
                    self.source_name,
                    age_seconds,
                    ttl,
                )
                return None

            data = json.loads(self._cache_path.read_text(encoding="utf-8"))
            self.logger.info(
                "Loaded %d records from cache for '%s' (age=%.0fs)",
                len(data),
                self.source_name,
                age_seconds,
            )
            return data
        except Exception as exc:
            self.logger.warning(
                "Failed to read cache for '%s': %s", self.source_name, exc
            )
            return None

    def _write_cache(self, terminals: list[LNGTerminal]) -> None:
        """Persist terminal records and metadata to cache."""
        if not self.config.cache.enabled:
            return
        try:
            cache_dir = get_cache_dir()
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Serialize terminals to JSON-safe dicts
            data = [t.model_dump(mode="json") for t in terminals]
            self._cache_path.write_text(
                json.dumps(data, default=str),
                encoding="utf-8",
            )

            meta = {
                "source_name": self.source_name,
                "collected_at": datetime.utcnow().isoformat(),
                "record_count": len(terminals),
            }
            self._cache_meta_path.write_text(
                json.dumps(meta),
                encoding="utf-8",
            )
            self.logger.debug(
                "Wrote %d records to cache for '%s'",
                len(terminals),
                self.source_name,
            )
        except Exception as exc:
            self.logger.warning(
                "Failed to write cache for '%s': %s", self.source_name, exc
            )

    def _load_from_cache(self) -> list[LNGTerminal]:
        """Deserialise cached dicts back into LNGTerminal models."""
        raw = self._read_cache()
        if raw is None:
            return []
        try:
            return [LNGTerminal.model_validate(r) for r in raw]
        except Exception as exc:
            self.logger.warning(
                "Cache deserialization failed for '%s': %s", self.source_name, exc
            )
            return []

    @property
    def last_collected_at(self) -> datetime | None:
        """Timestamp of the last successful cache write, or *None*."""
        if not self._cache_meta_path.exists():
            return None
        try:
            meta = json.loads(self._cache_meta_path.read_text(encoding="utf-8"))
            return datetime.fromisoformat(meta["collected_at"])
        except Exception:
            return None

    # -- Public lifecycle ----------------------------------------------------

    def collect(self, refresh_mode: RefreshMode | None = None) -> list[LNGTerminal]:
        """Main entry point: fetch -> parse -> validate.

        Parameters
        ----------
        refresh_mode:
            Override the instance-level refresh mode for this call.
        """
        mode = refresh_mode or self.refresh_mode
        self.logger.info(
            "Starting collection from '%s' (mode=%s)",
            self.source_name,
            mode.value,
        )
        start = time.monotonic()

        # --- FORCE_CACHE: never fetch, cache must exist ---
        if mode == RefreshMode.FORCE_CACHE:
            terminals = self._load_from_cache()
            if not terminals:
                raise LNGCollectionError.fetch_failed(
                    source=self.source_name,
                    reason="FORCE_CACHE mode but no valid cache exists",
                )
            return terminals

        # --- CACHE_FIRST: use cache when valid ---
        if mode == RefreshMode.CACHE_FIRST:
            cached = self._load_from_cache()
            if cached:
                return cached

        # --- FULL / INCREMENTAL / CACHE_FIRST (cache miss): fetch fresh ---
        try:
            raw_data = self.fetch_data()
        except Exception as exc:
            raise LNGCollectionError.fetch_failed(
                source=self.source_name,
                reason=str(exc),
                cause=exc,
            ) from exc

        terminals = self.parse_records(raw_data)
        valid = self.validate(terminals)

        # Write to cache for future runs
        self._write_cache(valid)

        elapsed = time.monotonic() - start
        self.logger.info(
            "Collection complete: %d valid from '%s' in %.1fs (requests=%d)",
            len(valid),
            self.source_name,
            elapsed,
            self._request_count,
        )
        return valid

    # -- Abstract hooks ------------------------------------------------------

    @abstractmethod
    def fetch_data(self) -> Any:
        """Fetch raw data from the source. Subclasses implement."""
        ...

    @abstractmethod
    def parse_records(self, raw_data: Any) -> list[LNGTerminal]:
        """Parse raw data into LNGTerminal models. Subclasses implement."""
        ...

    # -- Validation ----------------------------------------------------------

    def validate(self, terminals: list[LNGTerminal]) -> list[LNGTerminal]:
        """Filter out records missing required fields."""
        valid: list[LNGTerminal] = []
        for terminal in terminals:
            if not terminal.terminal_name or not terminal.country:
                self.logger.warning(
                    "Skipping terminal with missing name/country: %r",
                    getattr(terminal, "terminal_name", "?"),
                )
                continue
            valid.append(terminal)
        return valid

    # -- HTTP helpers --------------------------------------------------------

    def _make_request(
        self,
        url: str,
        method: str = "GET",
        **kwargs: Any,
    ) -> httpx.Response:
        """HTTP request with rate limiting and retry."""
        self._wait_for_rate_limit()
        retries = 0

        while retries <= self._scraper.max_retries:
            try:
                self.logger.debug(
                    "Request %s %s (attempt %d)",
                    method,
                    url,
                    retries + 1,
                )
                response = self.client.request(method, url, **kwargs)
                response.raise_for_status()
                self._request_count += 1
                return response

            except httpx.TimeoutException:
                if retries >= self._scraper.max_retries:
                    raise LNGCollectionError.fetch_failed(
                        source=self.source_name,
                        reason=f"Timeout after {self._scraper.max_retries + 1} attempts: {url}",
                    )
                retries += 1
                time.sleep(self._scraper.retry_delay * retries)

            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code

                if status_code == 429:
                    retry_after = int(exc.response.headers.get("Retry-After", 60))
                    if retries >= self._scraper.max_retries:
                        raise LNGCollectionError.fetch_failed(
                            source=self.source_name,
                            reason=f"Rate limited (429) after retries: {url}",
                            cause=exc,
                        ) from exc
                    self.logger.warning("Rate limited, waiting %ds", retry_after)
                    time.sleep(retry_after)
                    retries += 1
                    continue

                if (
                    status_code in RETRYABLE_HTTP_CODES
                    and retries < self._scraper.max_retries
                ):
                    retries += 1
                    time.sleep(self._scraper.retry_delay * retries)
                    continue

                raise LNGCollectionError.fetch_failed(
                    source=self.source_name,
                    reason=f"HTTP {status_code} for {url}",
                    cause=exc,
                ) from exc

            except httpx.RequestError as exc:
                if retries >= self._scraper.max_retries:
                    raise LNGCollectionError.fetch_failed(
                        source=self.source_name,
                        reason=f"Request error: {exc}",
                        cause=exc,
                    ) from exc
                retries += 1
                time.sleep(self._scraper.retry_delay * retries)

        raise LNGCollectionError.fetch_failed(
            source=self.source_name,
            reason=f"Max retries exceeded for {url}",
        )

    def _wait_for_rate_limit(self) -> None:
        """Enforce minimum delay between requests."""
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            if elapsed < self._scraper.rate_limit_delay:
                wait = self._scraper.rate_limit_delay - elapsed
                self.logger.debug("Rate limiting: waiting %.2fs", wait)
                time.sleep(wait)
        self._last_request_time = time.time()

    # -- Citation helpers ----------------------------------------------------

    def _create_citation(self, fields_sourced: list[str]) -> SourceCitation:
        """Create a SourceCitation for data obtained by this collector."""
        return SourceCitation(
            source_name=self.source_name,
            access_date=date.today(),
            fields_sourced=fields_sourced,
            reliability=self.source_reliability,
        )

    # -- Resource management -------------------------------------------------

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
        self.logger.debug("Collector closed. Total requests: %d", self._request_count)

    def __enter__(self) -> BaseCollector:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self.close()
