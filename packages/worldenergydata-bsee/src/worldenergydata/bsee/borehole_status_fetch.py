"""Serial, bounded public BSEE downloads and source provenance."""

from __future__ import annotations

import hashlib
import io
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from worldenergydata.bsee.borehole_status import load_boreholes

SOURCE_URL = "https://www.data.bsee.gov/Well/Files/5010delimit.zip"
TERMS_URL = "https://www.data.bsee.gov/Main/HtmlPage.aspx?page=Disclaimer"
TERMS = (
    "Working database; errors may exist; not a legal document; not for navigational use. "
    "No explicit licence stated on download page."
)
USER_AGENT = (
    "worldenergydata-public-borehole-curation/1.0 (public BSEE snapshot research)"
)
MAX_DOWNLOAD_BYTES = 20_000_000


def fetch_file(
    url: str,
    destination: Path,
    *,
    opener: Callable[..., Any] = urlopen,
    sleep: Callable[[float], Any] = time.sleep,
) -> dict[str, Any]:
    """One connection; timeout 60s; one retry for transient errors, none on refusal."""
    if not url.startswith("https://www.data.bsee.gov/"):
        raise ValueError("Only public BSEE HTTPS downloads are supported")
    if destination.exists():
        raise FileExistsError("Retain existing source; choose a new snapshot directory")
    request = Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(2):
        try:
            with opener(request, timeout=60) as response:
                raw = response.read(MAX_DOWNLOAD_BYTES + 1)
            break
        except (HTTPError, URLError, TimeoutError) as error:
            if isinstance(error, HTTPError) and error.code < 500:
                raise
            if attempt == 1:
                raise
            sleep(2)
    if len(raw) > MAX_DOWNLOAD_BYTES:
        raise ValueError("Download exceeds bounded source size")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        stream.write(raw)
    saved = destination.read_bytes()
    if saved != raw:
        raise OSError("Source readback differs from downloaded bytes")
    return {
        "file": destination.name,
        "source_url": url,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(saved).hexdigest(),
        "size_bytes": len(saved),
        "terms_url": TERMS_URL,
        "terms": TERMS,
    }


def load_archive(path: Path) -> list[dict[str, str]]:
    """Read the known member in memory; never extract ZIP paths to the filesystem."""
    with zipfile.ZipFile(path) as archive:
        if archive.namelist() != ["5010.txt"]:
            raise ValueError("Expected only documented 5010.txt member")
        if archive.getinfo("5010.txt").file_size > 100_000_000:
            raise ValueError("Uncompressed borehole source exceeds size bound")
        raw = archive.read("5010.txt")
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            offset = error.start + (3 if raw.startswith(b"\xef\xbb\xbf") else 0)
            raise ValueError(
                f"5010.txt: expected utf-8-sig; invalid byte at byte offset {offset}"
            ) from error
    return load_boreholes(io.StringIO(text))
