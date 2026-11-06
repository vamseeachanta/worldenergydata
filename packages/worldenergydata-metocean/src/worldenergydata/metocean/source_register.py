"""Read the packaged publisher register without network or filesystem writes."""

import json
from importlib.resources import files

MISSING_TERMS_EVIDENCE = "NOT_EVALUATED; no terms statement found"


def load_register() -> dict:
    resource = files("worldenergydata.metocean").joinpath("data/source_register.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def get_source(identifier: str) -> dict:
    for source in load_register()["sources"]:
        if source["id"] == identifier:
            return source
    raise ValueError(f"Unknown registered source: {identifier}")


def _https_url(value: object) -> bool:
    from urllib.parse import urlsplit

    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    return bool(
        parsed.scheme == "https"
        and parsed.hostname
        and not parsed.username
        and not parsed.password
        and not parsed.fragment
    )


def _not_evaluated(value: object) -> bool:
    return isinstance(value, str) and value.startswith("NOT_EVALUATED")


def validate_register(register: dict) -> None:
    """Reject incomplete access evidence without promoting legacy eligibility.

    ``unconfirmed`` preserves access uncertainty without asserting an account
    requirement. Account/key categories require a documented evidence locator.
    Missing terms URLs require explicit NOT_EVALUATED evidence; a present terms
    URL is an evidence locator, not an assertion of reuse permission.
    """
    seen = set()
    for source in register["sources"]:
        identifier = source["id"]
        if identifier in seen:
            raise ValueError("duplicate source identifier")
        seen.add(identifier)
        for field in ("base_url", "docs_url"):
            if not _https_url(source.get(field)):
                raise ValueError(f"{identifier}: invalid or missing {field}")
        if "terms_url" not in source or (
            source["terms_url"] is None
            and source.get("terms_evaluation") != MISSING_TERMS_EVIDENCE
        ):
            raise ValueError(
                f"{identifier}: missing terms_url or NOT_EVALUATED evidence"
            )
        if source["terms_url"] is not None and not _https_url(source["terms_url"]):
            raise ValueError(f"{identifier}: invalid terms_url")
        requirement = source.get("auth_requirement")
        if requirement not in {"none", "free key", "account", "unconfirmed"}:
            raise ValueError(f"{identifier}: invalid or missing auth_requirement")
        if requirement == "unconfirmed" and not _not_evaluated(
            source.get("auth_evaluation")
        ):
            raise ValueError(f"{identifier}: missing NOT_EVALUATED auth_evaluation")
        if requirement in {"account", "free key"} and (
            not _https_url(source.get("auth_evidence_url"))
            or _not_evaluated(source.get("auth_evaluation"))
        ):
            raise ValueError(f"{identifier}: missing confirmed auth_evidence")
        endpoints = source.get("endpoints")
        if not isinstance(endpoints, list) or not endpoints:
            raise ValueError(f"{identifier}: missing endpoints")
        if not all(_https_url(endpoint) for endpoint in endpoints):
            raise ValueError(f"{identifier}: invalid endpoints")


def registered_url(url: str, register: dict | None = None) -> bool:
    """Match a registered origin and path prefix, never a hostname substring.

    Configurable ERDDAP servers supplied by callers need their own register row
    before an audited workflow can use them. This is an inventory check, not an
    HTTP security boundary or permission to ingest any dataset on that server.
    """
    from urllib.parse import urlsplit

    if not _https_url(url):
        return False
    candidate = urlsplit(url)
    for source in (register if register is not None else load_register())["sources"]:
        for endpoint in source["endpoints"]:
            base = urlsplit(endpoint)
            prefix = base.path.rstrip("/")
            if candidate.netloc == base.netloc and (
                candidate.path == prefix or candidate.path.startswith(prefix + "/")
            ):
                return True
    return False
