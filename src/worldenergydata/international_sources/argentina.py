"""Argentina CKAN resource discovery without bulk production downloads.

Protocol basis: CKAN Action API, package_show; source investigation in
the country-source readiness note in docs/data-sources/.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Resource:
    """A catalogue locator; size is publisher-declared bytes, not measured."""

    resource_id: str
    url: str
    size_bytes: int | None


@dataclass(frozen=True)
class Discovery:
    """Unknown rights/frequency remain None; no readiness is inferred."""

    dataset_id: str
    license: str | None
    update_frequency: str | None
    source_modified: str | None
    resources: tuple[Resource, ...]
    production_status: str = "NOT_EVALUATED"


def discover_resources(payload: dict) -> Discovery:
    """Read a package_show response and rank CSVs by known declared size.

    Unknown sizes sort last. No remote URL is fetched or trusted as executable
    input. Catalogue metadata alone never establishes permission to redistribute.
    """
    if payload.get("success") is not True or not isinstance(
        payload.get("result"), dict
    ):
        raise ValueError("CKAN package_show did not return a successful package")
    package = payload["result"]
    if not isinstance(package.get("id"), str) or not package["id"].strip():
        raise ValueError("CKAN package id is required")
    resources = []
    for item in package.get("resources", []):
        if str(item.get("format", "")).casefold() != "csv":
            continue
        url = item.get("url", "")
        if urlsplit(url).scheme not in {"http", "https"} or not urlsplit(url).hostname:
            raise ValueError("CSV resource requires an HTTP(S) URL")
        size = item.get("size")
        if type(size) is not int or size < 0:
            size = None
        if not item.get("id"):
            raise ValueError("CSV resource id is required")
        resources.append(Resource(item["id"], url, size))
    resources.sort(
        key=lambda r: (r.size_bytes is None, r.size_bytes or 0, r.resource_id)
    )
    extras = {item["key"]: item.get("value") for item in package.get("extras", [])}
    return Discovery(
        dataset_id=package["id"],
        license=package.get("license_id") or None,
        update_frequency=package.get("accrualPeriodicity")
        or extras.get("accrualPeriodicity"),
        source_modified=package.get("metadata_modified") or None,
        resources=tuple(resources),
    )
