"""Validate and summarize offline Arkansas source metadata.

Landing-page verification describes metadata evidence only. This module neither
fetches observations nor grants redistribution permission. See the source
inventory documentation for field meanings and the bounded discovery evidence.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from collections.abc import Iterable, Mapping
from datetime import datetime
from ipaddress import IPv4Address, IPv6Address
from urllib.parse import urlsplit

REQUIRED_FIELDS = frozenset(
    {
        "source_url",
        "source_category",
        "dataset_type",
        "access_method",
        "format",
        "rights_status",
        "verification_status",
        "verification_time",
    }
)
DATASET_TYPES = {
    "regulator": frozenset(
        {"wells", "production", "permits", "fields", "spacing_pooling_orders"}
    ),
    "county_title": frozenset({"county_directory", "recorded_leases", "mineral_title"}),
}
ACCESS_METHODS = frozenset(
    {
        "unknown",
        "landing_page",
        "interactive_lookup",
        "bulk_download",
        "api",
        "manual_request",
    }
)
# Permission qualification is outside this inventory. Public access alone
# cannot be represented as approval to redistribute source observations.
RIGHTS_STATUSES = frozenset({"unknown", "restricted"})
VERIFICATION_STATUSES = frozenset({"unverified", "landing_page_verified"})


def validate_inventory(rows: Iterable[Mapping[str, object]]) -> list[dict[str, str]]:
    """Return copied rows, rejecting incomplete or ambiguous metadata.

    Use the literal ``unknown`` for undetermined access, format or rights.
    ``verification_time`` is the timezone-aware time of the metadata check,
    including an unsuccessful attempt when the status is ``unverified``.
    Validation checks structure, not source authority, access or permissions.
    """
    if isinstance(rows, (str, bytes, Mapping)) or not isinstance(rows, Iterable):
        raise ValueError("inventory must be an iterable of metadata rows")
    validated = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("each metadata row must be a mapping")
        if REQUIRED_FIELDS - row.keys():
            raise ValueError("missing metadata fields")
        if row.keys() - REQUIRED_FIELDS:
            raise ValueError("unexpected metadata fields")
        if any(not isinstance(v, str) or not v.strip() for v in row.values()):
            raise ValueError("metadata fields must contain a nonempty string")
        # Inspect the original URL before normalization can discard controls.
        _validate_url(row["source_url"])
        clean = {key: value.strip() for key, value in row.items()}
        category = clean["source_category"]
        if category not in DATASET_TYPES:
            raise ValueError("unsupported source_category")
        if clean["dataset_type"] not in DATASET_TYPES[category]:
            raise ValueError("dataset_type does not belong to source_category")
        for field, allowed in (
            ("access_method", ACCESS_METHODS),
            ("rights_status", RIGHTS_STATUSES),
            ("verification_status", VERIFICATION_STATUSES),
        ):
            if clean[field] not in allowed:
                raise ValueError(f"unsupported {field}; use unknown when applicable")
        try:
            checked = datetime.fromisoformat(
                clean["verification_time"].replace("Z", "+00:00")
            )
        except ValueError:
            raise ValueError("verification_time must be an ISO timestamp") from None
        if checked.tzinfo is None or checked.utcoffset() is None:
            raise ValueError("verification_time must include a timezone")
        validated.append(clean)
    return validated


def _validate_url(value: str) -> None:
    value = value.strip(" ")
    try:
        if (
            any(not 0x21 <= ord(char) <= 0x7E for char in value)
            or "\\" in value
            or "?" in value
            or "#" in value
            or re.search(r"%(?![0-9a-fA-F]{2})", value)
        ):
            raise ValueError
        url = urlsplit(value)
        authority = re.fullmatch(r"(\[[^\[\]]+\]|[^:\[\]]+)(?::([0-9]+))?", url.netloc)
        valid = (
            url.scheme in {"http", "https"}
            and authority is not None
            and url.username is None
            and url.password is None
            and re.fullmatch(r"[a-zA-Z0-9._~!$&'()*+,;=:@/%-]*", url.path) is not None
        )
        if valid:
            _validate_host(authority.group(1))
            port = authority.group(2)
            if port is not None and int(port) > 65535:
                raise ValueError
    except ValueError:
        valid = False
    if not valid:
        raise ValueError(
            "source_url must be an HTTP(S) landing URL without credentials or query"
        )


def _validate_host(host: str) -> None:
    if host.startswith("["):
        if "%" in host:
            raise ValueError
        IPv6Address(host[1:-1])
        return
    dns_name = host.removesuffix(".")
    labels = dns_name.split(".")
    # Numeric final labels have alternative IP interpretations in URL parsers.
    if re.fullmatch(r"[0-9]+|0[xX][0-9a-fA-F]*", labels[-1]):
        IPv4Address(host)
        return
    if len(dns_name) > 253 or any(
        re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", label) is None
        for label in labels
    ):
        raise ValueError


def summarize_inventory(rows: Iterable[Mapping[str, object]]) -> dict[str, int]:
    """Count metadata records; totals are not distinct websites or datasets."""
    sources = validate_inventory(rows)
    return {
        "total_sources": len(sources),
        "regulator_sources": sum(s["source_category"] == "regulator" for s in sources),
        "county_title_sources": sum(
            s["source_category"] == "county_title" for s in sources
        ),
        "unverified_sources": sum(
            s["verification_status"] == "unverified" for s in sources
        ),
        "unknown_access_sources": sum(s["access_method"] == "unknown" for s in sources),
        "unknown_rights_sources": sum(s["rights_status"] == "unknown" for s in sources),
    }


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate metadata fields")
        result[key] = value
    return result


def main() -> None:
    """Read a JSON inventory from standard input and print its metadata summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        summary = summarize_inventory(
            json.load(
                io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8"),
                object_pairs_hook=_unique_object,
            )
        )
    except (ValueError, TypeError, RecursionError):
        # Avoid echoing supplied URLs or other potentially sensitive input.
        parser.error("invalid inventory: missing metadata or invalid field values")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
