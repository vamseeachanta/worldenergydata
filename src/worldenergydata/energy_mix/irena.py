"""Validate user-normalized offshore wind CSVs; live IRENA access is refused.

The input schema is a repository contract, not a verified IRENASTAT export
format. Blank measurements mean unavailable; zero means a reported zero.
"""

import csv
import hashlib
import io
import json
import math
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

SOURCE_PAGE = "https://www.irena.org/Data/Downloads/IRENASTAT"
ROBOTS_URL = "https://www.irena.org/robots.txt"
COLUMNS = (
    "country",
    "iso_code",
    "year",
    "technology",
    "capacity_mw",
    "generation_gwh",
    "source_url",
    "citation",
)
MAX_EXPORT_BYTES = 5_000_000


class AccessRefused(RuntimeError):
    """Live access cannot proceed until source restrictions are resolved."""


def fetch_irena() -> bytes:
    """Fail closed without transport, retries, guessed URLs or credentials."""
    raise AccessRefused(
        "IRENA robots request returned HTTP 403 with a WAF challenge on "
        "2026-10-11 UTC; automated fetching stopped. Supply a permitted export."
    )


def _measurement(value: str) -> float | None:
    if value == "":
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError("Measurements must be finite and nonnegative")
    return number


def _validate_row(row: dict[str, str], max_year: int) -> dict[str, Any]:
    if any(value is None for value in row.values()) or None in row:
        raise ValueError("CSV row width does not match header")
    if any(value != value.strip() for value in row.values()):
        raise ValueError("Whitespace around field values is not permitted")
    if not row["country"] or not row["citation"]:
        raise ValueError("Country and citation are required")
    iso = row["iso_code"]
    if iso and not re.fullmatch(r"[A-Z]{3}", iso):
        raise ValueError("ISO code must be blank or three uppercase letters")
    if not re.fullmatch(r"[0-9]{4}", row["year"]):
        raise ValueError("Year must be an integer with four digits")
    year = int(row["year"])
    if not 1960 <= year <= max_year:
        raise ValueError("Year outside supported historical range")
    if row["technology"] != "offshore wind":
        raise ValueError("Technology must be offshore wind")
    url = urlsplit(row["source_url"])
    if url.scheme != "https" or not url.netloc or url.username or url.password:
        raise ValueError("Source URL must be public HTTPS without credentials")
    capacity = _measurement(row["capacity_mw"])
    generation = _measurement(row["generation_gwh"])
    if capacity is None and generation is None:
        raise ValueError("At least one measurement is required")
    return {**row, "year": year, "capacity_mw": capacity, "generation_gwh": generation}


def load_export(raw: bytes) -> list[dict[str, Any]]:
    """Return a tidy table, preserving supplied citations and optional ISO codes.

    Units are fixed by the header: MW for capacity, GWh for generation.
    The maximum year is the current UTC year; no country codes are inferred.
    """
    if len(raw) > MAX_EXPORT_BYTES:
        raise ValueError("Export exceeds 5,000,000-byte limit")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), strict=True)
    if reader.fieldnames != list(COLUMNS):
        raise ValueError(
            "CSV header must match the documented ordered schema and units"
        )
    records = []
    seen = set()
    countries: dict[str, str] = {}
    codes: dict[str, str] = {}
    max_year = datetime.now(timezone.utc).year
    for row in reader:
        record = _validate_row(row, max_year)
        country, iso = row["country"].casefold(), row["iso_code"]
        if country in countries and countries[country] != iso:
            raise ValueError(
                "Inconsistent country key: country has different ISO codes"
            )
        if iso and iso in codes and codes[iso] != country:
            raise ValueError(
                "Inconsistent country key: ISO code has different countries"
            )
        countries[country] = iso
        if iso:
            codes[iso] = country
        key = (country.casefold(), record["year"])
        if key in seen:
            raise ValueError("Duplicate country/year key")
        seen.add(key)
        records.append(record)
    if not records:
        raise ValueError("Export contains no observations")
    return records


def write_table(records: list[dict[str, Any]]) -> bytes:
    """Serialize a tidy table to the same CSV contract and validate it."""
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    raw = out.getvalue().encode("utf-8")
    load_export(raw)
    return raw


def _validate_provenance(
    synthetic: bool,
    retrieved_at_utc: str | None,
    terms_quote: str | None,
    terms_url: str | None,
) -> None:
    if not synthetic and not all(
        value and value.strip() for value in (retrieved_at_utc, terms_quote, terms_url)
    ):
        raise ValueError("Real exports require retrieval and terms provenance")
    if not synthetic:
        timestamp = datetime.fromisoformat(str(retrieved_at_utc).replace("Z", "+00:00"))
        offset = timestamp.utcoffset()
        if offset is None or offset.total_seconds() != 0:
            raise ValueError("Retrieval timestamp must be UTC")
        if timestamp > datetime.now(timezone.utc):
            raise ValueError("Retrieval timestamp cannot be in the future")
        url = urlsplit(str(terms_url))
        if url.scheme != "https" or not url.hostname or url.username or url.password:
            raise ValueError(
                "Terms provenance requires public HTTPS without credentials"
            )


def emit_manifest(
    raw: bytes,
    *,
    synthetic: bool = False,
    retrieved_at_utc: str | None = None,
    terms_quote: str | None = None,
    terms_url: str | None = None,
) -> bytes:
    """Emit deterministic JSON with caller-supplied, unverified provenance.

    Synthetic fixtures qualify testing only, never engineering use.
    """
    records = load_export(raw)
    _validate_provenance(synthetic, retrieved_at_utc, terms_quote, terms_url)
    manifest = {
        "schema_version": 1,
        "dataset_id": "irena-offshore-wind-normalized",
        "synthetic": synthetic,
        "retrieved_at_utc": None if synthetic else retrieved_at_utc,
        "retrieval_state": (
            "not applicable: authored synthetic fixture"
            if synthetic
            else "caller supplied"
        ),
        "source_urls": sorted({record["source_url"] for record in records}),
        "citations": sorted({record["citation"] for record in records}),
        "terms": {
            "quote": (
                "Synthetic test fixture; no source data reproduced."
                if synthetic
                else terms_quote
            ),
            "url": None if synthetic else terms_url,
        },
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "rows": len(records),
        "units": {"capacity_mw": "MW", "generation_gwh": "GWh"},
        "readiness": (
            "synthetic testing only"
            if synthetic
            else "format validated; source rights and intended use require independent verification"
        ),
        "live_access": "refused: HTTP 403 WAF challenge at robots statement, 2026-10-11 UTC",
        "robots_url": ROBOTS_URL,
        "source_page": SOURCE_PAGE,
    }
    return (
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode()
