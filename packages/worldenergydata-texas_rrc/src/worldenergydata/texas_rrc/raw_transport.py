"""Transport layer for Texas RRC raw snapshot downloads."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Protocol
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen

from worldenergydata.texas_rrc.godrive import (
    GoDriveDirectoryEntry,
    parse_godrive_directory_page,
    parse_godrive_file_form,
    parse_godrive_partial_directory_page,
)


@dataclass(frozen=True)
class TransportResponse:
    """HTTP response payload used by raw snapshot refresh."""

    status_code: int
    headers: dict[str, str]
    content: bytes
    effective_url: str


@dataclass(frozen=True)
class DownloadedArtifact:
    """Metadata for a streamed artifact written to disk."""

    headers: dict[str, str]
    effective_url: str
    checksum_sha256: str
    byte_size: int


class RetryableDownloadError(ValueError):
    """Download error that may succeed on a later attempt."""


class RawRefreshTransport(Protocol):
    """Transport contract for fakeable official-source downloads."""

    def get(self, url: str) -> TransportResponse:
        """Fetch a URL and return response bytes plus metadata."""


class UrlLibTransport:
    """Small urllib-based transport to avoid adding a package dependency."""

    def __init__(self, opener_factory=None):
        self._opener_factory = opener_factory or (
            lambda: build_opener(HTTPCookieProcessor(CookieJar()))
        )

    def get(self, url: str) -> TransportResponse:
        request = Request(url, headers={"User-Agent": "worldenergydata-texas-rrc/1.0"})
        with urlopen(request, timeout=60) as response:
            headers = {key.lower(): value for key, value in response.headers.items()}
            return TransportResponse(
                status_code=response.status,
                headers=headers,
                content=response.read(),
                effective_url=response.geturl(),
            )

    def download_to(self, url: str, output_path: Path) -> DownloadedArtifact:
        request = Request(url, headers={"User-Agent": "worldenergydata-texas-rrc/1.0"})
        with urlopen(request, timeout=60) as response:
            return self._stream_response_to_artifact(response, output_path)

    def download_godrive_file_to(
        self,
        url: str,
        output_path: Path,
        expected_filename: str,
    ) -> DownloadedArtifact:
        opener = build_opener(HTTPCookieProcessor(CookieJar()))
        landing_request = Request(
            url,
            headers={"User-Agent": "worldenergydata-texas-rrc/1.0"},
        )
        with opener.open(landing_request, timeout=60) as landing_response:
            html_text = landing_response.read().decode("utf-8", errors="replace")

        form = parse_godrive_file_form(html_text, expected_filename)
        post_data = urlencode(
            {
                "fileList_SUBMIT": "1",
                form.command_id: form.command_id,
                "javax.faces.ViewState": form.view_state,
            }
        ).encode("utf-8")
        download_request = Request(
            urljoin(url, "/webclient/godrive/PublicGoDrive.xhtml"),
            data=post_data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "worldenergydata-texas-rrc/1.0",
            },
        )
        with opener.open(download_request, timeout=60) as response:
            return self._stream_response_to_artifact(
                response,
                output_path,
                expected_filename=expected_filename,
            )

    def list_godrive_directory(
        self,
        url: str,
        rows_per_page: int = 1000,
    ):
        """List every zip row in an official public GoDrive directory."""
        self._validate_godrive_url(url)
        self._validate_rows_per_page(rows_per_page)
        opener = self._opener_factory()
        landing = self._open_text(opener, Request(url, headers=self._headers()))
        first_page = parse_godrive_directory_page(landing, 0, rows_per_page)
        pages = [first_page]
        view_state = first_page.view_state
        page_step = first_page.rows_per_page
        page_first = page_step
        while page_first < first_page.row_count:
            text = self._post_page(opener, url, page_first, rows_per_page, view_state)
            page = parse_godrive_partial_directory_page(
                text,
                page_first,
                page_step,
                first_page.row_count,
                require_zip_rows=False,
            )
            pages.append(page)
            view_state = page.view_state
            page_first += page_step
        return tuple(pages)

    def download_godrive_directory_file_to(
        self,
        url: str,
        entry: GoDriveDirectoryEntry,
        output_path: Path,
        rows_per_page: int = 1000,
    ) -> DownloadedArtifact:
        """Download one file row from an official public GoDrive directory."""
        self._validate_godrive_url(url)
        self._validate_rows_per_page(rows_per_page)
        opener = self._opener_factory()
        landing = self._open_text(opener, Request(url, headers=self._headers()))
        page = parse_godrive_directory_page(landing, 0, rows_per_page)
        if entry.page_first:
            text = self._post_page(
                opener, url, entry.page_first, rows_per_page, page.view_state
            )
            page = parse_godrive_partial_directory_page(
                text,
                entry.page_first,
                page.rows_per_page,
                page.row_count,
            )
        post_data = urlencode(
            {
                "fileList_SUBMIT": "1",
                entry.command_id: entry.command_id,
                "javax.faces.ViewState": page.view_state,
            }
        ).encode("utf-8")
        request = Request(
            urljoin(url, "/webclient/godrive/PublicGoDrive.xhtml"),
            data=post_data,
            headers={
                **self._headers(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        with opener.open(request, timeout=60) as response:
            return self._stream_response_to_artifact(
                response,
                output_path,
                expected_filename=entry.filename,
            )

    def _post_page(
        self,
        opener,
        url: str,
        page_first: int,
        rows_per_page: int,
        view_state: str,
    ) -> str:
        request = Request(
            urljoin(url, "/webclient/godrive/PublicGoDrive.xhtml"),
            data=self._pagination_data(page_first, rows_per_page, view_state),
            headers={
                **self._headers(),
                "Content-Type": "application/x-www-form-urlencoded",
                "Faces-Request": "partial/ajax",
            },
        )
        return self._open_text(opener, request)

    @staticmethod
    def _pagination_data(page_first: int, rows_per_page: int, view_state: str) -> bytes:
        return urlencode(
            {
                "javax.faces.partial.ajax": "true",
                "javax.faces.source": "fileTable",
                "javax.faces.partial.execute": "fileTable",
                "javax.faces.partial.render": "fileTable",
                "javax.faces.behavior.event": "page",
                "javax.faces.partial.event": "page",
                "fileList": "fileList",
                "fileTable_pagination": "true",
                "fileTable_first": str(page_first),
                "fileTable_rows": str(rows_per_page),
                "fileTable_skipChildren": "true",
                "fileTable_encodeFeature": "true",
                "fileList_SUBMIT": "1",
                "javax.faces.ViewState": view_state,
            }
        ).encode("utf-8")

    @staticmethod
    def _headers() -> dict[str, str]:
        return {"User-Agent": "worldenergydata-texas-rrc/1.0"}

    @staticmethod
    def _open_text(opener, request: Request) -> str:
        with opener.open(request, timeout=60) as response:
            return response.read().decode("utf-8", errors="replace")

    @staticmethod
    def _validate_godrive_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != "mft.rrc.texas.gov":
            raise ValueError("URL must use the official RRC GoDrive host")

    @staticmethod
    def _validate_rows_per_page(rows_per_page: int) -> None:
        if rows_per_page < 1:
            raise ValueError("rows_per_page must be at least 1")

    @staticmethod
    def _stream_response_to_artifact(
        response,
        output_path: Path,
        expected_filename: str | None = None,
    ) -> DownloadedArtifact:
        headers = {key.lower(): value for key, value in response.headers.items()}
        UrlLibTransport._validate_artifact_response(
            response.status,
            headers,
            expected_filename=expected_filename,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sha256 = hashlib.sha256()
        byte_size = 0
        with output_path.open("wb") as stream:
            while chunk := response.read(1024 * 1024):
                sha256.update(chunk)
                byte_size += len(chunk)
                stream.write(chunk)
        UrlLibTransport._validate_content_length(headers, byte_size)
        return DownloadedArtifact(
            headers=headers,
            effective_url=response.geturl(),
            checksum_sha256=sha256.hexdigest(),
            byte_size=byte_size,
        )

    @staticmethod
    def _validate_artifact_response(
        status_code: int,
        headers: dict[str, str],
        expected_filename: str | None = None,
    ) -> None:
        if status_code >= 500:
            raise RetryableDownloadError(
                f"Download failed with HTTP status {status_code}"
            )
        if status_code >= 400:
            raise ValueError(f"Download failed with HTTP status {status_code}")
        content_type = headers.get("content-type", "").lower()
        if "text/html" in content_type:
            raise ValueError(
                "Direct-source refresh received HTML instead of a data artifact"
            )
        if expected_filename:
            disposition = headers.get("content-disposition", "")
            if disposition and expected_filename not in disposition:
                raise ValueError(
                    "Official GoDrive download did not return expected file "
                    f"{expected_filename!r}"
                )

    @staticmethod
    def _validate_content_length(headers: dict[str, str], byte_size: int) -> None:
        raw_content_length = headers.get("content-length")
        if not raw_content_length:
            return
        expected_size = int(raw_content_length)
        if expected_size != byte_size:
            raise RetryableDownloadError(
                f"Content-Length mismatch: expected {expected_size} bytes, "
                f"received {byte_size} bytes"
            )


__all__ = [
    "DownloadedArtifact",
    "RawRefreshTransport",
    "RetryableDownloadError",
    "TransportResponse",
    "UrlLibTransport",
]
