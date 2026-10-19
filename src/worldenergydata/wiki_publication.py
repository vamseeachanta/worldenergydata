# ABOUTME: Fail-closed well-operations wiki routing and dry-run contract.
"""Issue #453 publication boundary, independent of analysis and filesystem I/O.

Policy source: issue #453, tightened decisions dated 2026-06-08, items
1–5 and 7. Reviews and safety outcomes here are caller-supplied evidence
claims. This contract does not authenticate approvals or execute safety scans.
Only a subsequent reviewed publisher may act on a proposed route.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import Enum
from urllib.parse import urlsplit


class Target(str, Enum):
    """Exactly one logical destination; blocked differs from private."""

    PUBLIC = "public-federal-data"
    PRIVATE_GENERIC = "private-generic"
    PRIVATE_RESTRICTED = "private-restricted"
    NO_PUBLISH = "no-publish"


@dataclass(frozen=True)
class Review:
    """Declared decisions plus an evidence reference; never proof of approval."""

    publisher: Target
    reviewer: Target
    evidence_ref: str


@dataclass(frozen=True)
class Source:
    """One classified input from an upstream insight run, without raw data."""

    source_id: str
    dataset_version: str
    domain: str
    source_class: str
    terms_class: str
    source_authority: str
    source_url: str
    retrieved_at: str
    data_as_of: str
    content_sha256: str
    derivation_path: tuple[str, ...]
    review: Review


@dataclass(frozen=True)
class Bundle:
    """Generated findings and publication evidence, not an upstream run schema.

    ``safety_status='passed'`` declares completed extraction, citation,
    contamination, link, legal/security and generated-diff checks from #453.
    Missing or NOT_EVALUATED evidence blocks publication. No refresh age is
    assumed: the caller must assess freshness in that review.
    """

    run_id: str
    attempt_id: str
    code_ref: str
    catalog_ref: str
    slug: str
    title: str
    findings: str
    sources: tuple[Source, ...]
    data_as_of: str
    generated_at: str
    last_license_check: str
    limitations: tuple[str, ...]
    scope: str
    content_kind: str
    review: Review
    safety_status: str


@dataclass(frozen=True)
class RoutingDecision:
    """Safe diagnostic codes; restricted input values are never echoed."""

    target: Target
    reason: str


def _text(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _texts(value: object) -> bool:
    return isinstance(value, tuple) and bool(value) and all(map(_text, value))


def _date(value: str) -> date:
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("non-canonical date")
    return parsed


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if "T" not in value or parsed.utcoffset() is None:
        raise ValueError("timezone required")
    return parsed


def _url(value: str, *, federal: bool = False) -> bool:
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        return (
            parsed.scheme == "https"
            and bool(host)
            and parsed.username is None
            and parsed.password is None
            and parsed.port is None
            and not parsed.query
            and not parsed.fragment
            and value.isprintable()
            and not any(char.isspace() for char in value)
            and (not federal or host == "bsee.gov" or host.endswith(".bsee.gov"))
        )
    except ValueError:
        return False


def _review(value: object, target: Target) -> bool:
    return (
        isinstance(value, Review)
        and value.publisher is target
        and value.reviewer is target
        and _text(value.evidence_ref)
    )


def _complete_bundle(bundle: Bundle) -> bool:
    if not all(
        _text(getattr(bundle, name))
        for name in (
            "run_id",
            "attempt_id",
            "code_ref",
            "catalog_ref",
            "title",
            "findings",
            "scope",
        )
    ):
        return False
    if not isinstance(bundle.slug, str) or not re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*", bundle.slug
    ):
        return False
    if bundle.content_kind not in ("insight", "dataset-summary", "methodology"):
        return False
    if bundle.safety_status != "passed" or not _texts(bundle.limitations):
        return False
    if not isinstance(bundle.sources, tuple) or not bundle.sources:
        return False
    generated = _timestamp(bundle.generated_at)
    return (
        _date(bundle.data_as_of) <= generated.date()
        and _date(bundle.last_license_check) <= generated.date()
    )


def _complete_source(source: Source, bundle: Bundle) -> bool:
    if not isinstance(source, Source) or not all(
        _text(getattr(source, name))
        for name in (
            "source_id",
            "dataset_version",
            "domain",
            "source_class",
            "terms_class",
            "source_authority",
            "source_url",
        )
    ):
        return False
    # SHA-256 hex syntax: agent data handling contract, Descriptor v1 (2026-09-14).
    if not isinstance(source.content_sha256, str) or not re.fullmatch(
        r"[0-9a-f]{64}", source.content_sha256
    ):
        return False
    if not _texts(source.derivation_path) or not _url(source.source_url):
        return False
    retrieved = _timestamp(source.retrieved_at)
    return (
        _date(source.data_as_of) <= retrieved.date()
        and _date(source.data_as_of) <= _date(bundle.data_as_of)
        and retrieved <= _timestamp(bundle.generated_at)
    )


def _public_references(bundle: Bundle) -> bool:
    """Public projections contain opaque references, never local file locators."""
    values = [bundle.run_id, bundle.attempt_id, bundle.code_ref, bundle.catalog_ref]
    values.append(bundle.review.evidence_ref)
    for source in bundle.sources:
        values.extend(
            (source.source_id, source.dataset_version, source.review.evidence_ref)
        )
        values.extend(source.derivation_path)
    return all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]*", value) for value in values)


def route_bundle(bundle: Bundle) -> RoutingDecision:
    """Map a complete bundle to one target; ambiguity always blocks.

    First public scope and the universal-input gate are from #453 tightened
    decisions 2–5 (2026-06-08). No private fallback is inferred from a failed
    public gate. Uniform private inputs need explicit restricted reuse terms
    and matching decisions before they are even proposed for private routing.
    """
    blocked = RoutingDecision(Target.NO_PUBLISH, "incomplete-or-blocked-contract")
    try:
        if not isinstance(bundle, Bundle) or not _complete_bundle(bundle):
            return blocked
        if not all(_complete_source(source, bundle) for source in bundle.sources):
            return blocked
        source_ids = [source.source_id for source in bundle.sources]
        if len(source_ids) != len(set(source_ids)):
            return blocked
        if not isinstance(bundle.review, Review):
            return blocked
        target = bundle.review.publisher
        if not isinstance(target, Target) or target is Target.NO_PUBLISH:
            return blocked
        if not _review(bundle.review, target) or not all(
            _review(source.review, target) for source in bundle.sources
        ):
            return blocked
        if target is Target.PUBLIC:
            if (
                bundle.scope != "all-public-bsee-available-data-summary"
                or not _public_references(bundle)
            ):
                return blocked
            if not all(
                source.domain == "bsee"
                and source.source_class == "public-federal-data"
                and source.terms_class == "public-domain"
                and source.source_authority
                == "Bureau of Safety and Environmental Enforcement (US DOI)"
                and _url(source.source_url, federal=True)
                for source in bundle.sources
            ):
                return blocked
            return RoutingDecision(target, "eligible-public-contract")
        if all(
            source.source_class == "private"
            and source.terms_class == "restricted-publication-permitted"
            for source in bundle.sources
        ):
            return RoutingDecision(target, "eligible-private-contract")
    except (ValueError, TypeError, AttributeError):
        # Malformed input is a denial, without echoing the submitted value.
        return blocked
    return blocked


@dataclass(frozen=True)
class ProposedWrite:
    """UTF-8 content and a repository-relative path, for review only."""

    repository: str
    path: str
    content: str


@dataclass(frozen=True)
class PublicationPlan:
    """In-memory dry run. No method applies these writes to a repository."""

    decision: RoutingDecision
    writes: tuple[ProposedWrite, ...] = ()


def _yaml_mapping(record: dict) -> str:
    """YAML mapping with JSON-encoded values (a YAML-compatible subset).

    Escaping every value prevents injected frontmatter delimiters, keys or
    YAML tags. Ordering is fixed here; nested keys use canonical JSON ordering.
    """
    return "".join(
        f"{key}: {json.dumps(value, ensure_ascii=True, sort_keys=True, allow_nan=False)}\n"
        for key, value in record.items()
    )


def plan_publication(bundle: Bundle) -> PublicationPlan:
    """Propose public page + sanitized manifest without reading or writing files.

    Public path/frontmatter: #453 body and tightened decisions 1, 2 and 5
    (2026-06-08). Private destinations remain logical routes: no private
    paths, content or full ledgers are placed in a public plan. This function
    does not schedule refreshes, authenticate reviews or publish anything.
    """
    decision = route_bundle(bundle)
    if decision.target is not Target.PUBLIC:
        return PublicationPlan(decision)

    repository = "worldenergydata-wiki"
    folder = "wiki/bsee/well-operations"
    page_name = f"{bundle.slug}.md"
    manifest_name = f"{bundle.slug}.manifest.yaml"
    sources = sorted(bundle.sources, key=lambda source: source.source_id)
    metadata = {
        "visibility": "public-federal-data",
        "license": "public-domain",
        "domain": "bsee",
        "source_authority": "Bureau of Safety and Environmental Enforcement (US DOI)",
        "contribution_status": "us_federal_only",
        "last_license_check": bundle.last_license_check,
        "sources": sorted({source.source_url for source in sources}),
        "data_as_of": bundle.data_as_of,
        "generated_at": bundle.generated_at,
        "limitations": list(bundle.limitations),
        "run_manifest": manifest_name,
    }
    page = (
        f"---\n{_yaml_mapping(metadata)}---\n\n"
        f"# {bundle.title}\n\n{bundle.findings}\n\n"
        f"[Run manifest]({manifest_name})\n"
    )
    # This is a publication-side projection, not a copy of the upstream manifest.
    # The source records contain metadata only, never input bytes or local paths.
    manifest = {
        "schema_version": "well-operations-publication-v1",
        "run_id": bundle.run_id,
        "attempt_id": bundle.attempt_id,
        "code_ref": bundle.code_ref,
        "catalog_ref": bundle.catalog_ref,
        "scope": bundle.scope,
        "content_kind": bundle.content_kind,
        "data_as_of": bundle.data_as_of,
        "generated_at": bundle.generated_at,
        "last_license_check": bundle.last_license_check,
        "limitations": list(bundle.limitations),
        "review": asdict(bundle.review),
        "safety_status": bundle.safety_status,
        "source_records": [asdict(source) for source in sources],
        "output_path": f"{folder}/{page_name}",
        "output_sha256": hashlib.sha256(page.encode("utf-8")).hexdigest(),
    }
    return PublicationPlan(
        decision,
        (
            ProposedWrite(repository, f"{folder}/{page_name}", page),
            ProposedWrite(
                repository, f"{folder}/{manifest_name}", _yaml_mapping(manifest)
            ),
        ),
    )
