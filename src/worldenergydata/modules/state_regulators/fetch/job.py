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

from .client import Fetcher
from .policy import FetchConfig, TermsCheck, TermsDenied, choose_route, origin_of


def _storage_path(value: str) -> Path:
    expanded = os.path.expandvars(value)
    if "$" in expanded or not Path(expanded).is_absolute():
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
        route = choose_route(
            bulk, crawl[0] if crawl else bulk[0], use_crawl=settings["use_crawl"]
        )
        self.urls = list(
            dict.fromkeys(crawl if settings["use_crawl"] or not bulk else [route])
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="Collection configuration JSON")
    parser.add_argument(
        "--execute", action="store_true", help="Permit network collection"
    )
    args = parser.parse_args(argv)
    try:
        settings = json.loads(args.config.read_text())
        job = FetchJob(
            settings, execution_role=os.environ.get("STATE_FETCH_EXECUTION_ROLE", "")
        )
        result = job.run(job.fetcher(), execute=args.execute)
    except (ValueError, KeyError, TypeError, OSError, RuntimeError):
        # Do not echo configuration, URLs, filesystem locations or OS error text.
        parser.exit(
            1,
            "Collection refused; check deployment, terms, budget and cache evidence.\n",
        )
    if args.execute:
        result = {
            "completed_urls": len(result),
            "cached_urls": sum(r.cached for r in result),
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
