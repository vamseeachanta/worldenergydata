"""CORES oil density audit validation for report inputs (#807)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

import pandas as pd

from worldenergydata.spain.production.cores_density import (
    CoresCrudeDensityFactor,
    normalize_field_key,
)


class CoresDensityAuditError(RuntimeError):
    """Raised when a normalized CORES density audit is not report-ready."""


def load_oil_conversion_audit(
    root: Path,
    metadata: dict[str, Any],
    oil_production: pd.DataFrame,
) -> dict[str, Any] | None:
    """Load and validate the density audit sidecar or metadata fallback."""
    sidecar_path = root / "normalized" / "cores_oil_density_factors.json"
    if sidecar_path.exists():
        audit = _validated_oil_conversion_audit(
            _read_json(sidecar_path),
            sidecar_path.name,
        )
        _validate_oil_conversion_coverage(audit, oil_production, sidecar_path.name)
        return audit
    metadata_audit = metadata.get("oil_conversion_audit")
    if metadata_audit is None:
        return None
    return _load_metadata_audit(metadata_audit, oil_production)


def oil_conversion_limitations(audit: dict[str, Any] | None) -> list[str]:
    """Return summary limitations for the loaded oil conversion audit."""
    if audit is None:
        return ["oil_tonnes_to_bbl_conversion_deferred_to_issue_807"]
    coverage_status = audit["coverage_status"]
    defaulted_fields = list(audit["defaulted_fields"])
    missing_fields = list(audit["missing_fields"])
    if coverage_status == "missing" or missing_fields:
        return [
            "oil_tonnes_to_bbl_conversion_deferred_to_issue_807",
            _field_list_limitation(
                "oil_tonnes_to_bbl_has_missing_fields", missing_fields
            ),
        ]
    if coverage_status == "defaulted" or defaulted_fields:
        return [
            "oil_tonnes_to_bbl_conversion_deferred_to_issue_807",
            _field_list_limitation(
                "oil_tonnes_to_bbl_has_defaulted_fields",
                defaulted_fields,
            ),
        ]
    if coverage_status == "complete" and not defaulted_fields and not missing_fields:
        return ["oil_tonnes_to_bbl_uses_cited_field_density_factors"]
    return ["oil_tonnes_to_bbl_conversion_deferred_to_issue_807"]


def _load_metadata_audit(
    metadata_audit: Any,
    oil_production: pd.DataFrame,
) -> dict[str, Any]:
    source_name = "_metadata.json oil_conversion_audit"
    audit = _validated_oil_conversion_audit(metadata_audit, source_name)
    _validate_oil_conversion_coverage(audit, oil_production, source_name)
    return audit


def _field_list_limitation(marker: str, fields: list[str]) -> str:
    if not fields:
        return marker
    return f"{marker}: {', '.join(str(field) for field in fields)}"


def _validated_oil_conversion_audit(audit: Any, source_name: str) -> dict[str, Any]:
    if not isinstance(audit, dict):
        raise CoresDensityAuditError(f"{source_name} must be an object")
    if audit.get("coverage_status") not in {"complete", "defaulted", "missing"}:
        raise CoresDensityAuditError(f"{source_name} missing valid coverage_status")
    _validate_oil_conversion_audit_provenance(audit, source_name)
    _validate_oil_conversion_factors(audit, source_name)
    _validate_oil_conversion_field_lists(audit, source_name)
    _validate_oil_conversion_status_fields(audit, source_name)
    _validate_oil_conversion_factor_links(audit, source_name)
    return audit


def _validate_oil_conversion_audit_provenance(
    audit: dict[str, Any],
    source_name: str,
) -> None:
    for key in ("generated_at", "registry_version", "registry_date"):
        if not isinstance(audit.get(key), str) or not audit[key].strip():
            raise CoresDensityAuditError(f"{source_name} missing {key}")
    if audit.get("conversion_basis") != "cited_field_density_factors":
        raise CoresDensityAuditError(f"{source_name} missing conversion_basis")
    for key in ("schema_version", "oil_field_count"):
        value = audit.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise CoresDensityAuditError(f"{source_name} missing {key}")


def _validate_oil_conversion_factors(
    audit: dict[str, Any],
    source_name: str,
) -> None:
    factors = audit.get("factors")
    if not isinstance(factors, list):
        raise CoresDensityAuditError(f"{source_name} missing factors")
    for index, factor in enumerate(factors):
        _validate_oil_conversion_factor(factor, source_name, index)


def _validate_oil_conversion_field_lists(
    audit: dict[str, Any],
    source_name: str,
) -> None:
    for key in ("used_fields", "defaulted_fields", "missing_fields"):
        if key not in audit:
            raise CoresDensityAuditError(f"{source_name} missing {key}")
        if not isinstance(audit[key], list):
            raise CoresDensityAuditError(f"{source_name} {key} must be a list")
        _validate_field_list(audit[key], source_name, key)


def _validate_field_list(values: list[Any], source_name: str, key: str) -> None:
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            raise CoresDensityAuditError(f"{source_name} {key}[{index}] must be text")


def _validate_oil_conversion_status_fields(
    audit: dict[str, Any],
    source_name: str,
) -> None:
    if audit["coverage_status"] == "complete":
        if audit["defaulted_fields"] or audit["missing_fields"]:
            raise CoresDensityAuditError(f"{source_name} complete coverage has gaps")
    if audit["coverage_status"] == "defaulted" and not audit["defaulted_fields"]:
        raise CoresDensityAuditError(f"{source_name} missing defaulted_fields")
    if audit["coverage_status"] == "missing" and not audit["missing_fields"]:
        raise CoresDensityAuditError(f"{source_name} missing missing_fields")
    _validate_default_bbl_per_tonne(audit, source_name)
    _validate_oil_field_count(audit, source_name)


def _validate_default_bbl_per_tonne(
    audit: dict[str, Any],
    source_name: str,
) -> None:
    if not audit["defaulted_fields"]:
        return
    value = audit.get("default_bbl_per_tonne")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise CoresDensityAuditError(f"{source_name} missing default_bbl_per_tonne")


def _validate_oil_field_count(audit: dict[str, Any], source_name: str) -> None:
    field_count = sum(
        len(audit[key]) for key in ("used_fields", "defaulted_fields", "missing_fields")
    )
    if audit["oil_field_count"] != field_count:
        raise CoresDensityAuditError(f"{source_name} oil_field_count mismatch")


def _validate_oil_conversion_factor_links(
    audit: dict[str, Any],
    source_name: str,
) -> None:
    factors = cast(list[dict[str, Any]], audit["factors"])
    factor_fields = [str(factor["field_name"]) for factor in factors]
    if len(set(factor_fields)) != len(factor_fields):
        raise CoresDensityAuditError(f"{source_name} duplicate density factor field")
    used_fields = [str(field) for field in audit["used_fields"]]
    _validate_matching_factors(used_fields, factors, source_name)


def _validate_matching_factors(
    used_fields: list[str],
    factors: list[dict[str, Any]],
    source_name: str,
) -> None:
    used_keys = {normalize_field_key(field) for field in used_fields}
    missing_factors = [
        field
        for field in used_fields
        if normalize_field_key(field) not in _accepted_factor_keys(factors)
    ]
    extra_factors = [
        str(factor["field_name"])
        for factor in factors
        if not _factor_matches_any_used_field(factor, used_keys)
    ]
    if missing_factors:
        names = ", ".join(missing_factors)
        raise CoresDensityAuditError(
            f"{source_name} missing accepted oil density factors for: {names}"
        )
    if extra_factors:
        names = ", ".join(extra_factors)
        raise CoresDensityAuditError(
            f"{source_name} has unreferenced oil density factors for: {names}"
        )


def _accepted_factor_keys(factors: list[dict[str, Any]]) -> set[str]:
    keys: set[str] = set()
    for factor in factors:
        for value in (factor["field_name"], *factor["aliases"]):
            keys.add(normalize_field_key(str(value)))
    return keys


def _factor_matches_any_used_field(
    factor: dict[str, Any],
    used_keys: set[str],
) -> bool:
    return any(
        normalize_field_key(str(value)) in used_keys
        for value in (factor["field_name"], *factor["aliases"])
    )


def _validate_oil_conversion_coverage(
    audit: dict[str, Any],
    oil_production: pd.DataFrame,
    source_name: str,
) -> None:
    oil_fields = _production_fields(oil_production)
    covered = {
        normalize_field_key(str(field)): str(field)
        for key in ("used_fields", "defaulted_fields", "missing_fields")
        for field in audit[key]
    }
    oil_field_keys = {normalize_field_key(field) for field in oil_fields}
    missing = [
        field for field in oil_fields if normalize_field_key(field) not in covered
    ]
    if missing:
        names = ", ".join(missing)
        raise CoresDensityAuditError(
            f"{source_name} missing oil density coverage for: {names}"
        )
    extra = [
        field for key, field in sorted(covered.items()) if key not in oil_field_keys
    ]
    if extra:
        names = ", ".join(extra)
        raise CoresDensityAuditError(
            f"{source_name} has oil density coverage outside CSV fields for: {names}"
        )
    if audit["coverage_status"] == "complete":
        _validate_complete_oil_coverage(audit, oil_fields, source_name)


def _validate_complete_oil_coverage(
    audit: dict[str, Any],
    oil_fields: list[str],
    source_name: str,
) -> None:
    used_fields = {normalize_field_key(str(field)) for field in audit["used_fields"]}
    missing = [
        field for field in oil_fields if normalize_field_key(field) not in used_fields
    ]
    if missing:
        names = ", ".join(missing)
        raise CoresDensityAuditError(
            f"{source_name} missing accepted oil density factors for: {names}"
        )


def _production_fields(frame: pd.DataFrame) -> list[str]:
    return sorted(frame["field_name"].dropna().astype(str).unique())


def _validate_oil_conversion_factor(
    factor: Any,
    source_name: str,
    index: int,
) -> None:
    if not isinstance(factor, dict):
        raise CoresDensityAuditError(
            f"{source_name} factors[{index}] must be an object"
        )
    _validate_factor_keys(factor, source_name, index)
    _validate_factor_scalar_fields(factor, source_name, index)
    _validate_factor_with_registry_rules(factor, source_name, index)


def _validate_factor_keys(factor: dict[str, Any], source_name: str, index: int) -> None:
    for key in _FACTOR_KEYS:
        if key not in factor:
            raise CoresDensityAuditError(
                f"{source_name} factors[{index}] missing {key}"
            )


def _validate_factor_scalar_fields(
    factor: dict[str, Any],
    source_name: str,
    index: int,
) -> None:
    for key in _REQUIRED_TEXT_KEYS:
        if not isinstance(factor[key], str) or not factor[key].strip():
            raise CoresDensityAuditError(
                f"{source_name} factors[{index}] missing {key}"
            )
    _validate_http_url(factor["source_url"], source_name, index)
    if not isinstance(factor["aliases"], list):
        raise CoresDensityAuditError(
            f"{source_name} factors[{index}] aliases must be a list"
        )
    if not isinstance(factor["accepted_for_conversion"], bool):
        raise CoresDensityAuditError(
            f"{source_name} factors[{index}] accepted_for_conversion must be boolean"
        )
    if not factor["accepted_for_conversion"]:
        raise CoresDensityAuditError(
            f"{source_name} factors[{index}] accepted_for_conversion must be true"
        )


def _validate_factor_with_registry_rules(
    factor: dict[str, Any],
    source_name: str,
    index: int,
) -> None:
    try:
        CoresCrudeDensityFactor(
            field_name=factor["field_name"],
            aliases=tuple(factor["aliases"]),
            api_gravity_deg=factor["api_gravity_deg"],
            api_gravity_min_deg=factor["api_gravity_min_deg"],
            api_gravity_max_deg=factor["api_gravity_max_deg"],
            bbl_per_tonne=factor["bbl_per_tonne"],
            measurement_basis=factor["measurement_basis"],
            source_title=factor["source_title"],
            source_url=factor["source_url"],
            source_class=factor["source_class"],
            evidence_note=factor["evidence_note"],
            confidence=factor["confidence"],
            accepted_for_conversion=factor["accepted_for_conversion"],
        )
    except (TypeError, ValueError) as exc:
        raise CoresDensityAuditError(f"{source_name} factors[{index}] {exc}") from exc


def _validate_http_url(value: str, source_name: str, index: int) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise CoresDensityAuditError(
            f"{source_name} factors[{index}] invalid source_url"
        )


def _read_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


_FACTOR_KEYS = (
    "field_name",
    "aliases",
    "api_gravity_deg",
    "api_gravity_min_deg",
    "api_gravity_max_deg",
    "bbl_per_tonne",
    "measurement_basis",
    "source_title",
    "source_url",
    "source_class",
    "evidence_note",
    "confidence",
    "accepted_for_conversion",
)
_REQUIRED_TEXT_KEYS = (
    "field_name",
    "measurement_basis",
    "source_title",
    "source_url",
    "source_class",
    "evidence_note",
    "confidence",
)
