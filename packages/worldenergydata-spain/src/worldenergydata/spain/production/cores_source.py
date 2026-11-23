"""Official CORES workbook discovery and download support (#806)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Mapping, Optional
from urllib.parse import urljoin
from urllib.request import Request, urlopen

STATISTICS_PAGE_URL = "https://www.cores.es/en/estadisticas"


@dataclass(frozen=True)
class CoresWorkbook:
    """Official CORES workbook contract."""

    product: str
    dataset_name: str
    source_url: str
    filename: str
    source_unit: str
    normalized_column: str


DEFAULT_WORKBOOKS = {
    "oil": CoresWorkbook(
        product="oil",
        dataset_name="CORES Indigenous Crude Oil Production",
        source_url=(
            "https://www.cores.es/sites/default/files/archivos/estadisticas/"
            "crude-oil-production.xlsx"
        ),
        filename="crude-oil-production.xlsx",
        source_unit="tonnes",
        normalized_column="oil_bbl",
    ),
    "gas": CoresWorkbook(
        product="gas",
        dataset_name="CORES Indigenous Natural Gas Production",
        source_url=(
            "https://www.cores.es/sites/default/files/archivos/estadisticas/"
            "gas-production.xlsx"
        ),
        filename="gas-production.xlsx",
        source_unit="GWh",
        normalized_column="gas_mcf",
    ),
}


@dataclass(frozen=True)
class CoresHttpResponse:
    """HTTP response value object used by the injectable downloader boundary."""

    content: bytes
    headers: Mapping[str, str]
    status: int = 200


class CoresSourceError(RuntimeError):
    """Raised when CORES source discovery or download fails closed."""


class CoresWorkbookSource:
    """Discovers and downloads the official CORES production workbooks."""

    def __init__(
        self,
        *,
        cache_root: Path,
        http_get: Optional[Callable[..., CoresHttpResponse]] = None,
        clock: Optional[Callable[[], str]] = None,
    ):
        self.cache_root = Path(cache_root)
        self.raw_dir = self.cache_root / "raw"
        self.metadata_dir = self.cache_root / "metadata"
        self.metadata_path = self.metadata_dir / "cores_refresh_metadata.json"
        self._http_get = http_get or _urlopen_get
        self._clock = clock or utc_now_iso

    def discover(self, *, page_html: Optional[str] = None) -> dict[str, CoresWorkbook]:
        html = page_html if page_html is not None else self._fetch_statistics_page()
        hrefs = _extract_hrefs(html)
        inventory = {}
        for product, workbook in DEFAULT_WORKBOOKS.items():
            source_url = _find_workbook_url(hrefs, workbook.filename)
            if source_url is None:
                raise CoresSourceError(
                    "CORES statistics page missing workbook link for "
                    f"{product}: {workbook.filename}"
                )
            inventory[product] = replace(workbook, source_url=source_url)
        return inventory

    def download_all(
        self,
        *,
        force_refresh: bool = False,
        validate_links: bool = True,
    ) -> dict[str, Path]:
        workbooks = self.discover() if validate_links else DEFAULT_WORKBOOKS
        paths = {}
        entries = {}
        for product, workbook in workbooks.items():
            path, entry = self._download_or_reuse(workbook, force_refresh)
            paths[product] = path
            entries[product] = entry
        self._write_metadata(entries)
        return paths

    def download(
        self,
        product: str,
        *,
        force_refresh: bool = False,
        validate_links: bool = True,
    ) -> Path:
        workbook = (
            self.discover()[product] if validate_links else DEFAULT_WORKBOOKS[product]
        )
        path, entry = self._download_or_reuse(workbook, force_refresh)
        metadata = self.metadata()
        entries = dict(metadata.get("workbooks", {}))
        entries[product] = entry
        self._write_metadata(entries)
        return path

    def metadata(self) -> dict[str, Any]:
        if not self.metadata_path.exists():
            return {}
        with self.metadata_path.open(encoding="utf-8") as fh:
            return json.load(fh)

    def _fetch_statistics_page(self) -> str:
        response = self._http_get(STATISTICS_PAGE_URL, method="GET")
        if response.status >= 400:
            raise CoresSourceError(
                f"CORES statistics page returned HTTP {response.status}"
            )
        return response.content.decode("utf-8", errors="replace")

    def _download_or_reuse(
        self,
        workbook: CoresWorkbook,
        force_refresh: bool,
    ) -> tuple[Path, dict[str, Any]]:
        path = self.raw_dir / workbook.filename
        if path.exists() and not force_refresh:
            return path, self._cached_metadata(workbook, path)
        response = self._http_get(workbook.source_url, method="GET")
        _validate_workbook_response(workbook, response)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write(path, response.content)
        return path, self._response_metadata(workbook, path, response)

    def _cached_metadata(
        self,
        workbook: CoresWorkbook,
        path: Path,
    ) -> dict[str, Any]:
        entry = self.metadata().get("workbooks", {}).get(workbook.product, {})
        if entry:
            return entry
        return _workbook_metadata(
            workbook=workbook,
            path=path,
            cache_root=self.cache_root,
            content=path.read_bytes(),
            headers={},
            status=200,
        )

    def _response_metadata(
        self,
        workbook: CoresWorkbook,
        path: Path,
        response: CoresHttpResponse,
    ) -> dict[str, Any]:
        return _workbook_metadata(
            workbook=workbook,
            path=path,
            cache_root=self.cache_root,
            content=response.content,
            headers=response.headers,
            status=response.status,
        )

    def _write_metadata(self, workbook_entries: Mapping[str, Any]) -> None:
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        metadata = {
            "statistics_page": STATISTICS_PAGE_URL,
            "refreshed_at_utc": self._clock(),
            "workbooks": workbook_entries,
        }
        self.metadata_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


class _HrefParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.hrefs.append(urljoin(STATISTICS_PAGE_URL, value))


def _extract_hrefs(html: str) -> list[str]:
    parser = _HrefParser()
    parser.feed(html)
    return parser.hrefs


def _find_workbook_url(hrefs: list[str], filename: str) -> Optional[str]:
    for href in hrefs:
        if href.split("?", 1)[0].endswith(filename):
            return href
    return None


def _validate_workbook_response(
    workbook: CoresWorkbook,
    response: CoresHttpResponse,
) -> None:
    if response.status >= 400:
        raise CoresSourceError(f"{workbook.filename} returned HTTP {response.status}")
    if not response.content:
        raise CoresSourceError(f"{workbook.filename} download was empty")
    content_type = _header(response.headers, "content-type").lower()
    valid_type = any(
        token in content_type for token in ("spreadsheet", "excel", "octet-stream")
    )
    if content_type and not valid_type:
        raise CoresSourceError(
            f"{workbook.filename} returned non-Excel content type: {content_type}"
        )


def _workbook_metadata(
    *,
    workbook: CoresWorkbook,
    path: Path,
    cache_root: Path,
    content: bytes,
    headers: Mapping[str, str],
    status: int,
) -> dict[str, Any]:
    return {
        "byte_count": len(content),
        "content_type": _header(headers, "content-type") or None,
        "dataset_name": workbook.dataset_name,
        "filename": workbook.filename,
        "last_modified": _header(headers, "last-modified") or None,
        "normalized_column": workbook.normalized_column,
        "raw_path": str(path.relative_to(cache_root)),
        "sha256": hashlib.sha256(content).hexdigest(),
        "source_unit": workbook.source_unit,
        "source_url": workbook.source_url,
        "status_code": status,
    }


def _header(headers: Mapping[str, str], name: str) -> str:
    target = name.lower()
    for key, value in headers.items():
        if str(key).lower() == target:
            return str(value)
    return ""


def _atomic_write(path: Path, content: bytes) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_bytes(content)
    tmp_path.replace(path)


def _urlopen_get(url: str, *, method: str = "GET") -> CoresHttpResponse:
    request = Request(url, method=method, headers={"User-Agent": "worldenergydata"})
    with urlopen(request, timeout=60) as response:
        return CoresHttpResponse(
            content=response.read(),
            headers=dict(response.headers.items()),
            status=getattr(response, "status", 200),
        )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
