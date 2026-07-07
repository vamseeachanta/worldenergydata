"""Spain CORES crude density/API conversion registry (#807)."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping
from urllib.parse import urlparse

DEFAULT_OIL_BBL_PER_TONNE = 7.33

_ALLOWED_SOURCE_CLASSES = {
    "regulator_record",
    "operator_record",
    "securities_filing",
    "crude_assay",
    "technical_literature",
    "industry_technical_article",
    "secondary_article",
}
_CONVERSION_SOURCE_CLASSES = {
    "regulator_record",
    "operator_record",
    "securities_filing",
    "crude_assay",
    "technical_literature",
}
_ALLOWED_CONFIDENCE = {"low", "medium", "high"}


class CoresDensityCoverageError(ValueError):
    """Raised when strict oil conversion lacks accepted density coverage."""


def normalize_field_key(value: str) -> str:
    """Normalize CORES field names for density lookups."""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def bbl_per_tonne_from_api(api_gravity_deg: float) -> float:
    """Convert API gravity to barrels per metric tonne."""
    specific_gravity = 141.5 / (float(api_gravity_deg) + 131.5)
    return 1.0 / (specific_gravity * 0.158987294928)


@dataclass(frozen=True)
class CoresCrudeDensityFactor:
    """Cited crude density/API factor for one CORES oil field."""

    field_name: str
    aliases: tuple[str, ...]
    api_gravity_deg: float | None
    api_gravity_min_deg: float | None
    api_gravity_max_deg: float | None
    bbl_per_tonne: float | None
    measurement_basis: str
    source_title: str
    source_url: str
    source_class: str
    evidence_note: str
    confidence: str
    accepted_for_conversion: bool
    supporting_source_urls: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        validate_crude_density_factor(self)


@dataclass(frozen=True)
class CoresOilConversionAudit:
    """Resolved oil conversion factors for a parsed CORES frame."""

    used_factors: tuple[CoresCrudeDensityFactor, ...]
    defaulted_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]
    _accepted_entries: tuple[tuple[str, CoresCrudeDensityFactor], ...]
    _defaulted_field_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        for factor in [*self.used_factors, *(f for _, f in self._accepted_entries)]:
            validate_crude_density_factor(factor)

        for factor in self.used_factors:
            if factor.bbl_per_tonne is None:
                raise ValueError(f"{factor.field_name} missing bbl_per_tonne")
            if not factor.accepted_for_conversion:
                raise ValueError(f"{factor.field_name} is not accepted for conversion")

        accepted = {id(factor) for factor in self.used_factors}
        seen: set[str] = set()
        for key, factor in self._accepted_entries:
            if normalize_field_key(key) in seen:
                raise ValueError(f"duplicate density key: {key}")
            seen.add(normalize_field_key(key))
            if not factor.accepted_for_conversion:
                raise ValueError(f"{factor.field_name} is not accepted for conversion")
            if id(factor) not in accepted:
                raise ValueError(f"{factor.field_name} is not present in used_factors")
            if factor.bbl_per_tonne is None:
                raise ValueError(f"{factor.field_name} missing bbl_per_tonne")

        defaulted_keys = {normalize_field_key(name) for name in self.defaulted_fields}
        for key in self._defaulted_field_keys:
            if normalize_field_key(key) not in defaulted_keys:
                raise ValueError(
                    f"default key {key!r} not represented in defaulted_fields"
                )

    def bbl_per_tonne_for_field(self, field_name: str) -> float:
        """Return cited/default factor for a parsed CORES field."""
        key = normalize_field_key(field_name)
        for entry_key, factor in self._accepted_entries:
            if normalize_field_key(entry_key) == key:
                if factor.bbl_per_tonne is None:
                    raise ValueError(f"{factor.field_name} missing bbl_per_tonne")
                return factor.bbl_per_tonne
        if key in {normalize_field_key(name) for name in self.defaulted_fields}:
            return DEFAULT_OIL_BBL_PER_TONNE
        raise CoresDensityCoverageError(f"missing density factor for {field_name}")

    @property
    def used_field_names(self) -> tuple[str, ...]:
        """Parsed CORES display field names resolved to accepted factors."""
        names: dict[str, None] = {}
        for field_name, _factor in self._accepted_entries:
            names[str(field_name)] = None
        return tuple(names)


def validate_crude_density_factor(factor: CoresCrudeDensityFactor) -> None:
    """Validate one cited density factor regardless of construction path."""
    required = {
        "field_name": factor.field_name,
        "measurement_basis": factor.measurement_basis,
        "source_title": factor.source_title,
        "source_url": factor.source_url,
        "source_class": factor.source_class,
        "evidence_note": factor.evidence_note,
        "confidence": factor.confidence,
    }
    for name, value in required.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} is required")
    if not factor.aliases:
        raise ValueError("aliases are required")
    for alias in factor.aliases:
        if not isinstance(alias, str) or not alias.strip():
            raise ValueError("aliases must be non-empty strings")
    if not isinstance(factor.supporting_source_urls, tuple):
        raise ValueError("supporting_source_urls must be a tuple")
    for url in factor.supporting_source_urls:
        if not isinstance(url, str) or not url.strip():
            raise ValueError("supporting_source_urls must contain non-empty strings")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("supporting_source_urls must contain HTTP(S) URLs")
    if not isinstance(factor.accepted_for_conversion, bool):
        raise ValueError("accepted_for_conversion must be boolean")
    if factor.source_class not in _ALLOWED_SOURCE_CLASSES:
        raise ValueError(f"unsupported source_class: {factor.source_class}")
    if factor.confidence not in _ALLOWED_CONFIDENCE:
        raise ValueError(f"unsupported confidence: {factor.confidence}")

    has_range = (
        factor.api_gravity_min_deg is not None or factor.api_gravity_max_deg is not None
    )
    if factor.accepted_for_conversion:
        if factor.source_class not in _CONVERSION_SOURCE_CLASSES:
            raise ValueError(
                f"source_class {factor.source_class} cannot drive conversion"
            )
        if has_range and factor.api_gravity_deg is None:
            raise ValueError(
                "representative API gravity is required for range evidence"
            )
        if factor.bbl_per_tonne is None or factor.bbl_per_tonne <= 0:
            raise ValueError("bbl_per_tonne must be positive for accepted factors")
        if not 5.0 <= factor.bbl_per_tonne <= 9.5:
            raise ValueError("bbl_per_tonne outside conservative crude-oil range")
    elif has_range and factor.bbl_per_tonne is not None:
        raise ValueError("evidence-only range entries must not carry bbl_per_tonne")

    if factor.api_gravity_deg is not None and factor.bbl_per_tonne is not None:
        expected = bbl_per_tonne_from_api(factor.api_gravity_deg)
        if abs(factor.bbl_per_tonne - expected) > 0.01:
            raise ValueError("bbl_per_tonne does not match API gravity")


def load_crude_density_factors(
    path: Path | None = None,
) -> dict[str, CoresCrudeDensityFactor]:
    """Load, normalize, and validate cited crude density factors."""
    if path is None:
        path = _default_registry_path()
    with Path(path).open(encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        raise ValueError("registry_version is required")
    _validate_registry_metadata(payload)
    entries = payload.get("factors", [])
    if not isinstance(entries, list):
        raise ValueError("factors must be a list")
    factors: dict[str, CoresCrudeDensityFactor] = {}
    for entry in entries:
        if "accepted_for_conversion" not in entry:
            raise ValueError("accepted_for_conversion is required")
        supporting_source_urls = entry.get("supporting_source_urls", ())
        if not isinstance(supporting_source_urls, list | tuple):
            raise ValueError("supporting_source_urls must be a list")
        factor = CoresCrudeDensityFactor(
            field_name=entry.get("field_name"),
            aliases=tuple(entry.get("aliases", ())),
            api_gravity_deg=entry.get("api_gravity_deg"),
            api_gravity_min_deg=entry.get("api_gravity_min_deg"),
            api_gravity_max_deg=entry.get("api_gravity_max_deg"),
            bbl_per_tonne=entry.get("bbl_per_tonne"),
            measurement_basis=entry.get("measurement_basis"),
            source_title=entry.get("source_title"),
            source_url=entry.get("source_url"),
            source_class=entry.get("source_class"),
            evidence_note=entry.get("evidence_note"),
            confidence=entry.get("confidence"),
            accepted_for_conversion=entry.get("accepted_for_conversion", False),
            supporting_source_urls=tuple(supporting_source_urls),
        )
        factor_keys: set[str] = set()
        for key in (factor.field_name, *factor.aliases):
            normalized = normalize_field_key(key)
            if normalized in factor_keys:
                continue
            factor_keys.add(normalized)
            if normalized in factors:
                raise ValueError(f"duplicate density alias: {key}")
            factors[normalized] = factor
    return factors


def build_oil_conversion_audit(
    field_names: Iterable[str],
    factors: Mapping[str, CoresCrudeDensityFactor],
    *,
    allow_default_density: bool = False,
) -> CoresOilConversionAudit:
    """Resolve cited factors and exact missing/defaulted field lists."""
    if not isinstance(allow_default_density, bool):
        raise ValueError("allow_default_density must be boolean")
    normalized_factors = {normalize_field_key(k): v for k, v in factors.items()}
    used: list[CoresCrudeDensityFactor] = []
    entries: list[tuple[str, CoresCrudeDensityFactor]] = []
    defaulted: list[str] = []
    missing: list[str] = []

    for field_name in field_names:
        key = normalize_field_key(field_name)
        factor = normalized_factors.get(key)
        if factor is not None and factor.accepted_for_conversion:
            used.append(factor)
            entries.append((str(field_name), factor))
        elif allow_default_density:
            defaulted.append(str(field_name))
        else:
            missing.append(str(field_name))

    if missing:
        names = ", ".join(missing)
        raise CoresDensityCoverageError(f"missing density factors for: {names}")

    return CoresOilConversionAudit(
        used_factors=tuple(used),
        defaulted_fields=tuple(defaulted),
        missing_fields=tuple(missing),
        _accepted_entries=tuple(entries),
        _defaulted_field_keys=tuple(normalize_field_key(name) for name in defaulted),
    )


def _validate_registry_metadata(payload: Mapping[str, object]) -> None:
    for key in ("registry_version", "registry_date"):
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} is required")


def _default_registry_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "data"
        / "cores"
        / "crude_density_factors.json"
    )
