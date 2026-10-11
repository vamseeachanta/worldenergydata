"""Single bounded public request. Callers must check robots and terms first.

No crawling, automatic redirects, credentials, retries or on-disk cache.
A refusal response is evidence to stop that source, not permission to retry.
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from worldenergydata.cost.data_collection.operator_statement_registry import (
    validate_url,
)

USER_AGENT = (
    "WorldEnergyData-StatementRegistry/1.0 "
    "(public disclosure research; https://github.com/vamseeachanta/worldenergydata)"
)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        return None


def fetch_source(
    url: str,
    *,
    max_bytes: int = 2_000_000,
    transport: Callable[..., Any] | None = None,
) -> tuple[dict[str, Any], bytes]:
    """Return exact response metadata and bytes, aborting above the size limit.

    A two-second pause precedes every request. HTTP errors are returned once;
    callers shall stop on 403/429/challenges, including robots refusals. No
    server-requested wait is performed, so Retry-After cannot prolong this call.
    Redirects remain 3xx observations for explicit policy review by the caller.
    """
    validate_url(url)
    if max_bytes < 1 or max_bytes > 30_000_000:
        raise ValueError("size limit must be between 1 and 30000000 bytes")
    request = Request(
        url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
    )
    time.sleep(2)
    send = transport or build_opener(NoRedirect()).open
    try:
        response = send(request, timeout=30)
    except HTTPError as error:
        response = error
    with response:
        body = response.read(max_bytes + 1)
        if len(body) > max_bytes:
            raise ValueError("response exceeds size limit")
        metadata = {
            "url": url,
            "retrieved_at_utc": datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
            "http_status": response.status,
            "content_type": response.headers.get(
                "Content-Type", "not stated by the source"
            ).split(";")[0],
            "sha256": hashlib.sha256(body).hexdigest(),
            "size_bytes": len(body),
        }
    return metadata, body
