"""Pure v1 run records: supplied evidence, never publication authorization."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import date, datetime
from typing import get_args, get_origin, get_type_hints
from urllib.parse import urlsplit

import yaml


class _UniqueLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        pairs = self.construct_pairs(node, deep=deep)
        mapping = dict(pairs)
        if len(mapping) != len(pairs):
            raise ValueError("duplicate YAML key")
        return mapping


STATES = frozenset(
    {"real", "empty", "stale", "missing_module_dir", "external_only", "lfs_stub"}
)


def _instant(value):
    if not re.fullmatch(
        r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)", value
    ):
        raise ValueError("timestamp requires a timezone and seconds")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _typed(value, hint):
    args = get_args(hint)
    if type(None) in args:
        return value is None or _typed(
            value, next(t for t in args if t is not type(None))
        )
    if get_origin(hint) is tuple:
        return type(value) is tuple and all(_typed(v, args[0]) for v in value)
    return type(value) is hint and (
        hint is not str or bool(value.strip()) and value.isprintable()
    )


def _validate(record):
    for name, hint in get_type_hints(type(record)).items():
        value = getattr(record, name)
        if not _typed(value, hint):
            raise ValueError(f"invalid field: {name}")
        if value is not None and name.endswith("_sha256"):
            if not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError("invalid SHA-256")
        if value is not None and name.endswith("_at"):
            _instant(value)
        if value is not None and name.endswith("_as_of"):
            if date.fromisoformat(value).isoformat() != value:
                raise ValueError("date requires YYYY-MM-DD")
        if value is not None and (name.endswith("_id") or name == "code_ref"):
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", value):
                raise ValueError("identity requires an opaque reference")


def _evidence(record):
    _validate(record)
    if any(
        getattr(record, f.name) is None
        for f in fields(record)
        if f.name != "unavailable_reason"
    ):
        if record.unavailable_reason is None:
            raise ValueError("unavailable evidence requires a reason")


def _build(cls, value):
    if type(value) is not dict or set(value) != {f.name for f in fields(cls)}:
        raise ValueError("record keys must match the schema exactly")

    def convert(hint, item):
        args = get_args(hint)
        if type(None) in args:
            return (
                None
                if item is None
                else convert(next(t for t in args if t is not type(None)), item)
            )
        if get_origin(hint) is tuple:
            if type(item) not in (list, tuple):
                raise ValueError("expected an array")
            return tuple(convert(args[0], v) for v in item)
        return _build(hint, item) if is_dataclass(hint) else item

    return cls(
        **{k: convert(hint, value[k]) for k, hint in get_type_hints(cls).items()}
    )


@dataclass(frozen=True)
class CatalogRef:
    catalog_id: str
    catalog_version: str | None
    generated_at: str | None
    content_sha256: str | None
    unavailable_reason: str | None

    def __post_init__(self):
        _evidence(self)


@dataclass(frozen=True)
class SourceDatasetRef:
    dataset_id: str
    dataset_version: str | None
    state: str
    domain: str | None
    source_authority: str | None
    source_url: str | None
    license: str | None
    source_class: str | None
    retrieved_at: str | None
    data_as_of: str | None
    content_sha256: str | None
    derivation_path: tuple[str, ...] | None
    freshness_criteria: str | None
    unavailable_reason: str | None

    def __post_init__(self):
        _evidence(self)
        if self.state not in STATES:
            raise ValueError("unsupported dataset state")
        if self.source_url is not None:
            url = urlsplit(self.source_url)
            if (
                url.scheme != "https"
                or not url.hostname
                or url.username is not None
                or url.password is not None
                or url.port is not None
                or url.query
                or url.fragment
                or any(c.isspace() for c in self.source_url)
            ):
                raise ValueError("source URL requires an uncredentialed HTTPS citation")
        if self.derivation_path is not None:
            if any(
                not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", ref)
                for ref in self.derivation_path
            ):
                raise ValueError("derivation requires opaque references")
        if self.retrieved_at and self.data_as_of:
            if date.fromisoformat(self.data_as_of) > _instant(self.retrieved_at).date():
                raise ValueError("data vintage postdates retrieval")


@dataclass(frozen=True)
class OutputRef:
    path: str
    content_sha256: str | None
    unavailable_reason: str | None

    def __post_init__(self):
        _evidence(self)
        if (
            self.path.startswith("/")
            or "\\" in self.path
            or ":" in self.path
            or any(p in ("", ".", "..") for p in self.path.split("/"))
        ):
            raise ValueError("output path requires a canonical relative path")


@dataclass(frozen=True)
class RunManifest:
    schema_version: int
    run_id: str
    attempt_id: str
    created_at: str
    code_ref: str
    scope: str
    catalog_ref: CatalogRef
    probe_set: tuple[str, ...]
    datasets: tuple[SourceDatasetRef, ...]
    outputs: tuple[OutputRef, ...]
    limitations: tuple[str, ...]
    rerun_of_attempt_id: str | None
    supersedes_run_id: str | None

    def __post_init__(self):
        _validate(self)
        if self.schema_version != 1 or not all(
            (self.probe_set, self.datasets, self.outputs, self.limitations)
        ):
            raise ValueError("v1 requires probes, datasets, outputs and limitations")
        for values in (
            self.probe_set,
            tuple(s.dataset_id for s in self.datasets),
            tuple(o.path for o in self.outputs),
        ):
            if len(values) != len(set(values)):
                raise ValueError("duplicate identity")
        if (
            self.rerun_of_attempt_id == self.attempt_id
            or self.supersedes_run_id == self.run_id
        ):
            raise ValueError("lineage cannot reference itself")
        generated = _instant(self.created_at)
        timestamps = [self.catalog_ref.generated_at] + [
            s.retrieved_at for s in self.datasets
        ]
        if any(t is not None and _instant(t) > generated for t in timestamps):
            raise ValueError("evidence postdates run creation")

    @classmethod
    def from_dict(cls, value: dict) -> RunManifest:
        return _build(cls, value)

    def to_dict(self) -> dict:
        return json.loads(json.dumps(asdict(self)))

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.to_dict(), sort_keys=False, allow_unicode=True)

    @classmethod
    def from_yaml(cls, text: str) -> RunManifest:
        loader = _UniqueLoader(text)
        try:
            return cls.from_dict(loader.get_single_data())
        finally:
            loader.dispose()

    def readiness(self) -> str:
        """Screen declarations only; no bytes, freshness or approval are verified."""
        evidence = (self.catalog_ref, *self.datasets, *self.outputs)
        if self.scope != "bsee-well-operations" or any(
            e.unavailable_reason for e in evidence
        ):
            return "blocked"
        for source in self.datasets:
            host = urlsplit(source.source_url).hostname
            if (
                source.state != "real"
                or source.domain != "bsee"
                or source.source_class != "public-federal-bsee"
                or source.source_authority
                not in (
                    "BSEE",
                    "Bureau of Safety and Environmental Enforcement (US DOI)",
                )
                or source.license != "public-domain"
                or not source.derivation_path
                or not (host == "bsee.gov" or host.endswith(".bsee.gov"))
            ):
                return "blocked"
        return "declared-eligible"
