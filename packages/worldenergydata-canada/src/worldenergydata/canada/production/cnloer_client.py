"""Local-only C-NLOER PDF acquisition; no production volumes are published.

Report identities and year-prefixed URLs follow the C-NLOER Statistical
Information page, Monthly Production Summary sections (accessed 2026-10-19):
https://www.cnloer.ca/information/statistics/
See also data/cnlopb/_metadata.json in this package. Reuse rights remain
unresolved; raw PDFs and derived volumes shall stay off public surfaces.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener

from worldenergydata.canada.production.cnloer_loader import FIELD_CODES

_SOURCE_ROOT = "https://www.cnloer.ca/wp-content/uploads/"
# ISO 32000-1:2008, section 7.5.2: the file header begins with these bytes.
_PDF_HEADER = b"%PDF-"


class CnloerRedirectHandler(HTTPRedirectHandler):
    """Keep redirects on the regulator's fixed HTTPS origin."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        destination = urlsplit(newurl)
        if (destination.scheme, destination.netloc) != ("https", "www.cnloer.ca"):
            raise HTTPError(
                req.full_url, code, "redirect outside C-NLOER origin", headers, fp
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class CnloerPdfClient:
    """Fetch field/year reports into an explicitly supplied local cache.

    ``timeout`` (seconds) and ``max_bytes`` are caller-selected operational
    limits, not engineering acceptance limits. Existing snapshots are retained
    across refreshes. A cache hit must match its manifest digest. Header checks
    identify PDF candidates only; they do not establish parseability or data
    validity. No automatic fallback to synthetic production is provided.
    """

    def __init__(self, *, cache_dir: Path, timeout: float, max_bytes: int):
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (float, int))
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ValueError("timeout must be finite and positive")
        if (
            isinstance(max_bytes, bool)
            or not isinstance(max_bytes, int)
            or max_bytes <= 0
        ):
            raise ValueError("max_bytes must be a positive integer")
        self.cache_dir = Path(cache_dir)
        self.timeout = timeout
        self.max_bytes = max_bytes

    def download(
        self, *, year: int, field_code: str, force_refresh: bool = False
    ) -> Path:
        """Return a digest-verified cached PDF, or fetch a new snapshot.

        HTTP, transport and filesystem exceptions propagate to the caller.
        Invalid response bodies never replace the last successful manifest.
        """
        # The source names annual reports with a four-digit calendar year;
        # field codes are the published per-field report stems, excluding totals.
        if not re.fullmatch(r"[0-9]{4}", str(year)) or field_code not in FIELD_CODES:
            raise ValueError("expected a four-digit year and a per-field report code")
        stem = f"{year}{field_code}pro"
        url = f"{_SOURCE_ROOT}{stem}.pdf"
        manifest_path = self.cache_dir / f"{stem}.json"
        if manifest_path.exists() and not force_refresh:
            return self._cached_pdf(manifest_path, stem, url)

        opener = build_opener(CnloerRedirectHandler())
        with opener.open(url, timeout=self.timeout) as response:
            # One extra byte distinguishes an exact-limit body from an oversized one.
            payload = response.read(self.max_bytes + 1)
        if len(payload) > self.max_bytes or not payload.startswith(_PDF_HEADER):
            raise ValueError("response exceeds max_bytes or lacks a PDF header")

        digest = hashlib.sha256(payload).hexdigest()
        filename = f"{stem}-{digest}.pdf"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # Keep every cache artifact ignored even when a caller chooses a directory
        # inside a checkout. A pre-existing ignore file is never weakened.
        ignore = self.cache_dir / ".gitignore"
        if ignore.exists() and ignore.read_text() != "*\n":
            raise ValueError("cache .gitignore must ignore all cache artifacts")
        if not ignore.exists():
            _atomic_write(ignore, b"*\n")
        _atomic_write(self.cache_dir / filename, payload)
        manifest = {
            "source_id": "canada-cnloer",
            "source_url": url,
            "field_name": FIELD_CODES[field_code],
            "year": int(year),
            "file": filename,
            "sha256": digest,
            "size_bytes": len(payload),
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "publication_status": "restricted_pending_licence_review",
        }
        _atomic_write(manifest_path, (json.dumps(manifest, indent=2) + "\n").encode())
        return self._cached_pdf(manifest_path, stem, url)

    def _cached_pdf(self, manifest_path: Path, stem: str, url: str) -> Path:
        ignore = self.cache_dir / ".gitignore"
        if not ignore.exists() or ignore.read_text() != "*\n":
            raise ValueError("cache .gitignore must ignore all cache artifacts")
        manifest = json.loads(manifest_path.read_text())
        digest = manifest.get("sha256", "")
        expected = f"{stem}-{digest}.pdf"
        if (
            not isinstance(digest, str)
            or not re.fullmatch(
                r"[0-9a-f]{64}", digest
            )  # FIPS PUB 180-4 (2015), section 6.2: SHA-256.
            or manifest.get("file") != expected
            or manifest.get("source_url") != url
        ):
            raise ValueError("invalid cache manifest")
        path = self.cache_dir / expected
        with path.open("rb") as stream:
            payload = stream.read(self.max_bytes + 1)
        if (
            len(payload) > self.max_bytes
            or len(payload) != manifest.get("size_bytes")
            or hashlib.sha256(payload).hexdigest() != digest
            or not payload.startswith(_PDF_HEADER)
        ):
            raise ValueError("cached PDF digest or size mismatch")
        return path


def _atomic_write(path: Path, payload: bytes) -> None:
    """Replace a cache artifact only after the complete bytes have been written."""
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        staging = Path(stream.name)
        try:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            staging.unlink(missing_ok=True)
            raise
    try:
        staging.replace(path)
    finally:
        staging.unlink(missing_ok=True)
