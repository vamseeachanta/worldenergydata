"""Validate and list the offline HSE source registry.

Rules: issue 1325 (2026), Sources and Never collect; schema and migration
semantics are documented in docs/hse/source-registry.md. Validation checks
recorded assertions only: it neither fetches sources nor grants reuse rights.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Licence = Literal[
    "OGL-3.0",
    "US-federal-work",
    "attribution-permitted",
    "all-rights-reserved",
    "unverified",
]
AccessStatus = Literal[
    "public",
    "public_landing_only",
    "blocked",
    "unavailable",
    "unverified",
    "not_recollected",
]


class SourceEntry(BaseModel):
    """A source's stated terms, verification evidence and storage restriction."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    url: str
    licence: Licence
    licence_statement: str = Field(min_length=1)
    access_status: AccessStatus
    terms_verification: Literal["verified", "unverified"]
    terms_check_date: date | None
    terms_url: str | None
    terms_status: str = Field(min_length=1)
    storage_policy: Literal["metadata_only", "text_permitted"]
    alternate_urls: list[str] = Field(default_factory=list)
    access_date: date | None = None
    access_detail: str | None = None
    robots_status: str | None = None
    notes: str | None = None
    collection_policy: str | None = None
    verification_basis: str | None = None

    @field_validator("terms_check_date", "access_date", mode="before")
    @classmethod
    def calendar_date(cls, value):
        # Registry task (2026), slice 3: date-only YYYY-MM-DD, not timestamps.
        if value is None:
            return None
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("expected a date in YYYY-MM-DD format or null")
        return date.fromisoformat(value)

    @field_validator("url", "terms_url", "alternate_urls")
    @classmethod
    def public_url(cls, value):
        values = value if isinstance(value, list) else [value]
        for item in values:
            if item is None:
                continue
            try:
                parsed = urlsplit(item)
                _ = parsed.port  # Reject malformed ports as well as malformed hosts.
            except ValueError:
                raise ValueError("invalid public URL") from None
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or any(
                    character.isspace() or not character.isprintable()
                    for character in item
                )
            ):
                raise ValueError("expected a public HTTPS URL without credentials")
        return value

    @model_validator(mode="after")
    def evidence_and_storage(self):
        # Issue 1325 (2026), Sources: unclear terms allow metadata only.
        if self.terms_verification == "verified" and (
            self.licence == "unverified"
            or self.terms_check_date is None
            or self.terms_url is None
        ):
            raise ValueError(
                "verified terms require a licence, evidence URL and check date"
            )
        if self.storage_policy == "text_permitted" and (
            self.terms_verification != "verified"
            or self.access_status != "public"
            or self.licence in {"unverified", "all-rights-reserved"}
        ):
            raise ValueError(
                "text storage requires verified reuse terms and public access"
            )
        return self


class SourceRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Registry revision, defined by docs/hse/source-registry.md; not a data limit.
    schema_version: int = Field(strict=True)
    sources: list[SourceEntry] = Field(min_length=1)

    @field_validator("schema_version")
    @classmethod
    def supported_version(cls, value):
        if value != 2:
            raise ValueError("unsupported source registry schema version")
        return value

    @model_validator(mode="after")
    def unique_sources(self):
        names = [row.source for row in self.sources]
        if len(names) != len(set(names)):
            raise ValueError("duplicate source")
        return self


def _unique_json_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def default_registry_path() -> Path:
    """Find repository data; installed distributions must supply --registry."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "data/modules/hse/offshore/source_registry.json"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("supply --registry for an installed distribution")


def load_registry(path: Path | None = None) -> SourceRegistry:
    selected = Path(path) if path is not None else default_registry_path()
    payload = json.loads(
        selected.read_text(encoding="utf-8"), object_pairs_hook=_unique_json_keys
    )
    return SourceRegistry.model_validate(payload)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("list", "validate"))
    parser.add_argument(
        "--registry", type=Path, help="registry JSON; defaults to repository data"
    )
    parser.add_argument(
        "--json", action="store_true", help="emit the normalized registry as JSON"
    )
    args = parser.parse_args(argv)
    try:
        registry = load_registry(args.registry)
    except (OSError, ValueError):
        # Never echo untrusted values, credentials or local paths in diagnostics.
        print(
            "Invalid source registry; check fields, dates, evidence and storage policies.",
            file=sys.stderr,
        )
        return 2
    if args.json:
        payload = registry.model_dump(mode="json")
        payload["sources"].sort(key=lambda row: row["source"])
        print(json.dumps(payload, indent=2))
    elif args.command == "validate":
        print(f"Source registry valid: {len(registry.sources)} sources")
    else:
        columns = (
            "source",
            "licence",
            "access_status",
            "terms_check_date",
            "storage_policy",
            "url",
        )
        print("\t".join(columns))
        for row in sorted(registry.sources, key=lambda row: row.source):
            data = row.model_dump(mode="json")
            print(
                "\t".join(
                    str(data[key]) if data[key] is not None else "unverified"
                    for key in columns
                )
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
