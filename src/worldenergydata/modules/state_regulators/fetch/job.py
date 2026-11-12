"""Explicit single-source collection plan; dry-run is the command default.

Pacing values are required operator inputs, not inferred regulator limits.
User-Agent basis: RFC 9110 (2022), §10.1.5; a public contact URL is required
by this collection policy in addition to the HTTP identification syntax.
"""

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

from .client import Fetcher
from .policy import (
    BudgetExceeded,
    FetchConfig,
    ResponseTooLarge,
    TermsCheck,
    TermsDenied,
    UnreachableTarget,
    choose_route,
    origin_of,
)
from .storage import CacheIntegrityError


def _storage_path(value: str) -> Path:
    expanded = os.path.expandvars(value)
    unresolved = re.search(r"\$\{[^}]+\}|\$[A-Za-z_][A-Za-z0-9_]*|%[^%]+%", expanded)
    if unresolved or not Path(expanded).is_absolute():
        raise ValueError("Storage paths must be absolute with resolved variables")
    return Path(expanded).resolve()


class FetchJob:
    """Validate deployment and route decisions before creating the cache.

    The execution role comes from deployment configuration, not hostname guessing.
    Reachability is separately established by the first permitted uncached fetch.
    """

    def __init__(self, settings: dict[str, Any], *, execution_role: str) -> None:
        required_role = settings["execution_role"]
        if not required_role or execution_role != required_role:
            raise ValueError("Required execution role is unavailable")
        root = _storage_path(settings["storage_root"])
        options = dict(settings["fetch"])
        required = {
            "cache_root",
            "user_agent",
            "fallback_interval",
            "budget_requests",
            "budget_window",
            "timeout",
            "max_retries",
            "max_sleep_seconds",
            "max_response_bytes",
        }
        if required - options.keys():
            raise ValueError("Missing required fetch settings")
        cache = _storage_path(options["cache_root"])
        if not cache.is_relative_to(root):
            raise ValueError("Cache must be contained in the configured storage root")
        options["cache_root"] = cache
        contact = re.search(r"\(\+(https?://[^\s;)]+)", options["user_agent"])
        if contact is None:
            raise ValueError("User-Agent requires a public contact URL in (+URL) form")
        origin_of(contact.group(1))
        self.config = FetchConfig(**options)
        self.terms = [TermsCheck(**record) for record in settings["terms"]]
        bulk, crawl = settings["bulk_urls"], settings["crawl_urls"]
        if not all(isinstance(urls, list) for urls in (bulk, crawl)):
            raise ValueError("Bulk and crawl routes must be URL lists")
        if not bulk and not crawl:
            raise ValueError("At least one official bulk or crawl route is required")
        if type(settings["use_crawl"]) is not bool:
            raise ValueError("Crawl override must be an explicit Boolean")
        for url in [*bulk, *crawl]:
            origin_of(url)
        if settings["use_crawl"] and not crawl:
            raise ValueError("Crawl override requires crawl URLs")
        choose_route(
            bulk, crawl[0] if crawl else bulk[0], use_crawl=settings["use_crawl"]
        )
        self.urls = list(
            dict.fromkeys(crawl if settings["use_crawl"] or not bulk else bulk)
        )
        self.route = "crawl" if settings["use_crawl"] or not bulk else "bulk"

    def fetcher(self, **kwargs: Any) -> Fetcher:
        return Fetcher(self.config, self.terms, **kwargs)

    def run(self, fetcher: Fetcher, *, execute: bool) -> Any:
        if not execute:
            return {**fetcher.project(self.urls), "selected_route": self.route}
        # Refuse the entire plan before its first request if any pending origin
        # lacks permission; cache-only reuse retains existing withdrawal semantics.
        for url in self.urls:
            if fetcher.store.get(url) is None and not any(
                t.permits(url) for t in self.terms
            ):
                raise TermsDenied(f"No recorded bulk permission for {origin_of(url)}")
        return fetcher.run(self.urls)


def _failure(error: Exception) -> tuple[int, str]:
    """Stable exit categories without echoing paths, queries or OS error text."""
    if isinstance(error, TermsDenied):
        return 3, "TermsDenied: recorded permission is required"
    if isinstance(error, BudgetExceeded):
        return (
            4,
            f"BudgetExceeded: origin={error.origin}; resume_at={error.resume_at} UTC",
        )
    if isinstance(error, UnreachableTarget):
        return 5, f"UnreachableTarget: origin={error.origin}; layer={error.layer}"
    if isinstance(error, CacheIntegrityError):
        return 6, "CacheIntegrityError: preserve and inspect retained cache evidence"
    if isinstance(error, ResponseTooLarge):
        return 8, "ResponseTooLarge: response exceeds the configured byte cap"
    if isinstance(error, HTTPError):
        return 9, f"HTTPError: status={error.code}"
    if isinstance(error, OSError):
        return 7, "OSError: configuration or cache access failed"
    if isinstance(error, RuntimeError):
        return 10, "RuntimeError: collection failed"
    if isinstance(error, KeyError):
        return 11, "KeyError: a required configuration field is missing"
    if isinstance(error, TypeError):
        return 12, "TypeError: a configuration field has the wrong type"
    return 2, "ValueError: invalid collection configuration"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="Collection configuration JSON")
    parser.add_argument(
        "--execute", action="store_true", help="Permit network collection"
    )
    args = parser.parse_args(argv)
    try:
        settings = json.loads(args.config.read_text(encoding="utf-8"))
        job = FetchJob(
            settings, execution_role=os.environ.get("STATE_FETCH_EXECUTION_ROLE", "")
        )
        result = job.run(job.fetcher(), execute=args.execute)
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        code, message = _failure(error)
        parser.exit(code, message + "\n")
    if args.execute:
        result = {
            "completed_urls": len(result),
            "cached_urls": sum(r.cached for r in result),
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
