"""HTTP-only opening for direct-source downloads, including redirected requests."""

from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener


def _require_http(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("An HTTP(S) source URL is required")


class _HTTPRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _require_http(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def urlopen(url: str, timeout: int = 120):
    """Reject non-HTTP schemes before opening the source or any redirect."""
    _require_http(url)
    return build_opener(_HTTPRedirects()).open(url, timeout=timeout)
