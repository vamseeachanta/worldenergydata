"""Bounded HTTP acquisition of the public SENER production workbook."""

from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from time import monotonic
from urllib.parse import quote, unquote, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, build_opener
from uuid import uuid4
from zipfile import ZipFile, is_zipfile

from .bulk import LISTING_URL, ProductionWorkbook, load_production_workbook


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.hrefs.extend(
                value for name, value in attrs if name == "href" and value
            )


def _source_url(url):
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.netloc != urlsplit(LISTING_URL).netloc
        or parts.query
        or parts.fragment
    ):
        raise ValueError("download must use the public SENER source origin")
    return parts._replace(path=quote(unquote(parts.path), safe="/")).geturl()


class SourceRedirectHandler(HTTPRedirectHandler):
    """Check every redirect before urllib retrieves the redirected resource."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(
            req, fp, code, msg, headers, _source_url(newurl)
        )


@dataclass(frozen=True)
class BulkDownload:
    path: Path
    workbook: ProductionWorkbook
    receipt: dict


class BulkProductionClient:
    """No browser fallback; time and size budgets are required caller inputs.

    Discovery fails on absent or multiple candidates. An explicit trusted URL
    can select a reviewed release; numeric media IDs are never ordered as dates.
    The expanded archive budget defaults to ten times the download byte budget.
    Elapsed transfer time is checked between reads; a blocking socket operation
    can take up to the socket timeout before the elapsed budget is checked again.
    """

    def __init__(
        self,
        *,
        timeout: float,
        max_bytes: int,
        max_uncompressed_bytes=None,
        opener=None,
    ):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and positive")
        if (
            isinstance(max_bytes, bool)
            or not isinstance(max_bytes, int)
            or max_bytes <= 0
        ):
            raise ValueError("max_bytes must be a positive integer")
        if max_uncompressed_bytes is None:
            max_uncompressed_bytes = 10 * max_bytes
        if (
            isinstance(max_uncompressed_bytes, bool)
            or not isinstance(max_uncompressed_bytes, int)
            or max_uncompressed_bytes <= 0
        ):
            raise ValueError("max_uncompressed_bytes must be a positive integer")
        self.timeout, self.max_bytes = timeout, max_bytes
        self.max_uncompressed_bytes = max_uncompressed_bytes
        self.opener = opener or build_opener(SourceRedirectHandler()).open

    def _get(self, url):
        url = _source_url(url)
        deadline = monotonic() + self.timeout
        payload = bytearray()
        with self.opener(url, timeout=self.timeout) as response:
            _source_url(response.geturl())
            # HTTPResponse.read1 performs at most one underlying read, so a
            # trickling peer cannot keep one large read alive indefinitely.
            read = getattr(response, "read1", response.read)
            while True:
                if monotonic() >= deadline:
                    raise TimeoutError("source exceeds transfer time budget")
                chunk = read(min(65536, self.max_bytes + 1 - len(payload)))
                if monotonic() >= deadline:
                    raise TimeoutError("source exceeds transfer time budget")
                payload.extend(chunk)
                if len(payload) > self.max_bytes:
                    raise ValueError("source exceeds caller size budget")
                if not chunk:
                    return bytes(payload)

    def discover(self) -> str:
        links = _Links()
        payload = self._get(LISTING_URL)
        try:
            listing = payload.decode("utf-8-sig")
        except UnicodeDecodeError:
            listing = payload.decode("cp1252")
        links.feed(listing)
        candidates = set()
        for href in links.hrefs:
            name = (
                unicodedata.normalize("NFKD", unquote(href))
                .encode("ascii", "ignore")
                .decode()
                .lower()
            )
            if name.endswith(".xlsx") and "produccion-nacional" in name:
                try:
                    candidates.add(_source_url(urljoin(LISTING_URL, href)))
                except ValueError:
                    continue
        if len(candidates) != 1:
            raise ValueError(
                "expected one public production workbook; select a reviewed URL"
            )
        return candidates.pop()

    def download(
        self, directory: str | Path, *, url: str | None = None
    ) -> BulkDownload:
        url = _source_url(url) if url is not None else self.discover()
        payload = self._get(url)
        if not is_zipfile(BytesIO(payload)):
            raise ValueError("source is not an XLSX archive; possible maintenance page")
        with ZipFile(BytesIO(payload)) as archive:
            if (
                sum(member.file_size for member in archive.infolist())
                > self.max_uncompressed_bytes
            ):
                raise ValueError("source exceeds uncompressed archive size budget")
        digest = hashlib.sha256(payload).hexdigest()
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{digest}.xlsx"
        # Content-addressed raw bytes are retained without overwriting prior inputs.
        if path.exists():
            if path.read_bytes() != payload:
                raise ValueError("retained source digest mismatch")
        else:
            with path.open("xb") as stream:
                stream.write(payload)
        workbook = load_production_workbook(path)
        if workbook.sha256 != digest:
            raise ValueError("retained source digest mismatch")
        receipt = {
            "source_url": url,
            "listing_url": LISTING_URL,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "sha256": digest,
            "raw_file": path.name,
            "vintage": workbook.vintage,
            "rows": len(workbook.production),
            "units": {
                "oil_bbl": "bbl/month",
                "condensate_bbl": "bbl/month",
                "gas_mcf": "Mcf/month",
                "water_bbl": "unavailable",
            },
            "readiness": "partial",
            "freshness": "not_evaluated",
        }
        receipt_path = directory / f"{digest}.{uuid4().hex}.json"
        with receipt_path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(receipt, indent=2) + "\n")
        if json.loads(receipt_path.read_text(encoding="utf-8")) != receipt:
            raise ValueError("receipt readback mismatch")
        return BulkDownload(path, workbook, receipt)
