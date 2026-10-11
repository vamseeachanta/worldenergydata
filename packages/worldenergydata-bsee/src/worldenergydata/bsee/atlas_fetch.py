"""Sequential BSEE Atlas retrieval; raw files stay in a caller-selected directory."""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from http.client import HTTPSConnection
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse

from worldenergydata.bsee.atlas import TABLES, load_atlas

SOURCE_PAGE = "https://www.data.bsee.gov/Main/GandG.aspx"
TERMS_URL = "https://www.data.bsee.gov/Main/HtmlPage.aspx?page=Disclaimer"
TERMS = (
    "Source disclaimer: working database; errors may exist; not a legal document; "
    "not for navigational use. No explicit reuse licence is stated on the download page."
)
USER_AGENT = "worldenergydata/2023-atlas public research; sequential retrieval"


class DownloadLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href and "2023" in href and href.lower().endswith(".zip"):
                self.links.append(urljoin(SOURCE_PAGE, href))


def _request_bytes(url: str) -> bytes:
    parsed = urlparse(url)
    connection = HTTPSConnection("www.data.bsee.gov", timeout=120)
    try:
        target = parsed.path + ("?" + parsed.query if parsed.query else "")
        connection.request("GET", target, headers={"User-Agent": USER_AGENT})
        response = connection.getresponse()
        if response.status >= 300:
            raise HTTPError(
                url, response.status, response.reason, response.headers, None
            )
        return response.read()
    finally:
        connection.close()


def _download(url: str, destination: Path) -> dict[str, object]:
    if urlparse(url).scheme != "https" or urlparse(url).hostname != "www.data.bsee.gov":
        raise ValueError("download URL must be HTTPS on the public BSEE data site")
    for attempt in range(2):
        try:
            data = _request_bytes(url)
            destination.write_bytes(data)
            return file_record(destination, url)
        except HTTPError as error:
            # A refusal is final. No alternate host, headers or access route.
            if error.code < 500 or attempt:
                raise
        except (URLError, TimeoutError):
            if attempt:
                raise
        time.sleep(2)
    raise RuntimeError("download exhausted")


def file_record(path: Path, source_url: str) -> dict[str, object]:
    return {
        "file": path.name,
        "source_url": source_url,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
        "terms_url": TERMS_URL,
        "terms": TERMS,
    }


def fetch_atlas(
    directory: Path, schema_path: Path, mdb_export: str = "mdb-export"
) -> dict[str, object]:
    """Discover the ZIP, retain originals, export only the requested tables.

    MDB Tools is an external prerequisite; no system installation is attempted.
    Existing output files are preserved by refusing to overwrite them.
    """
    directory.mkdir(parents=True, exist_ok=True)
    expected = [
        "source-page.html",
        "disclaimer.html",
        "atlas-2023.zip",
        "atlas-2023.accdb",
        "manifest.json",
        "refusal.json",
        "handmade-fixture.json",
    ]
    expected += [f"{table}.csv" for table in TABLES]
    if any((directory / name).exists() for name in expected):
        raise FileExistsError("use a new data directory or reuse existing exports")
    records = []
    try:
        records.append(_download(SOURCE_PAGE, directory / "source-page.html"))
        parser = DownloadLinks()
        parser.feed((directory / "source-page.html").read_text())
        links = sorted(set(parser.links))
        if len(links) != 1:
            raise ValueError("expected one discovered 2023 Atlas ZIP link")
        records.append(_download(TERMS_URL, directory / "disclaimer.html"))
        records.append(_download(links[0], directory / "atlas-2023.zip"))
    except HTTPError as error:
        _record_refusal(directory, error, records)
        raise
    records.extend(_export_tables(directory, links[0], mdb_export))
    atlas = load_atlas(directory, schema_path)
    manifest = {
        "source_id": "bsee-data-center",
        "edition": 2023,
        "source_page": SOURCE_PAGE,
        "files": records,
        "row_counts": {name: len(rows) for name, rows in atlas.items()},
    }
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def _record_refusal(
    directory: Path, error: HTTPError, records: list[dict[str, object]]
) -> None:
    refusal = {
        "status": "refused",
        "http_status": error.code,
        "source_url": error.url,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": records,
        "attribution_readiness": "unavailable",
    }
    (directory / "refusal.json").write_text(json.dumps(refusal, indent=2) + "\n")
    (directory / "handmade-fixture.json").write_text(
        json.dumps(
            {
                "synthetic": True,
                "table_names_only": list(TABLES),
                "rows": [],
                "note": "No downloaded columns or engineering attribution asserted.",
            },
            indent=2,
        )
        + "\n"
    )


def _export_tables(
    directory: Path, source_url: str, mdb_export: str
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    with zipfile.ZipFile(directory / "atlas-2023.zip") as archive:
        members = [n for n in archive.namelist() if n.endswith(".accdb")]
        if len(members) != 1:
            raise ValueError("expected one Access database in Atlas ZIP")
        (directory / "atlas-2023.accdb").write_bytes(archive.read(members[0]))
    records.append(file_record(directory / "atlas-2023.accdb", source_url))
    for table in TABLES:
        path = directory / f"{table}.csv"
        with path.open("x") as stream:
            subprocess.run(
                [
                    mdb_export,
                    "-D",
                    "%Y-%m-%d %H:%M:%S",
                    "-T",
                    "%Y-%m-%d %H:%M:%S",
                    str(directory / "atlas-2023.accdb"),
                    table,
                ],
                stdout=stream,
                check=True,
            )
        records.append(file_record(path, source_url))
    return records
