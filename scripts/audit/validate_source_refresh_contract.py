#!/usr/bin/env python3
"""Validate the source refresh acceptance contract."""

from __future__ import annotations

import argparse
import json
import re
from json import JSONDecodeError
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from source_refresh_contract_schema import (
    COMPLETENESS_BY_CATALOG_STATUS,
    REQUIRED_HIGH_VALUE_SOURCES,
    REQUIRED_ROW_FIELDS,
    REQUIRED_WILDCARD_SCORECARD_MAPPINGS,
    SCORECARD_PAIR_MAPPING,
)


class ValidationError(Exception):
    """Raised when the source refresh contract is invalid."""


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValidationError(f"Missing required file: {path}")
    try:
        return json.loads(path.read_text())
    except JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON in {path}") from exc


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def map_scorecard_status(freshness_status: str, catalog_status: str) -> tuple[str, str]:
    pair = f"{freshness_status}|{catalog_status}"
    if pair in SCORECARD_PAIR_MAPPING:
        mapped = SCORECARD_PAIR_MAPPING[pair]
        return mapped["freshness_status"], mapped["completeness_status"]
    completeness = COMPLETENESS_BY_CATALOG_STATUS.get(catalog_status)
    if completeness is None:
        raise ValidationError(f"Unknown catalog_status: {catalog_status}")
    if freshness_status in {"fresh", "stale"}:
        return freshness_status, completeness
    raise ValidationError(f"Unmapped scorecard status pair: {pair}")


def validate_contract(project_root: Path) -> dict[str, Any]:
    contract = load_json(
        project_root / "data" / "source-refresh-acceptance-contract.json"
    )
    _validate_top_level(contract)
    scheduler = _scheduler_jobs(project_root)
    _validate_sources(project_root, contract, scheduler)
    _validate_scorecard_pairs(project_root, contract)
    _validate_skill_reference(project_root)
    return contract


def _validate_top_level(contract: dict[str, Any]) -> None:
    required = (
        "schema_version freshness_status_values completeness_status_values "
        "source_data_latest_date_basis_values "
        "prohibited_source_data_latest_date_basis_values required_row_fields "
        "required_high_value_sources scorecard_pair_mapping sources"
    ).split()
    for key in required:
        if key not in contract:
            raise ValidationError(f"Missing top-level contract key: {key}")
    for field in REQUIRED_ROW_FIELDS:
        if field not in contract["required_row_fields"]:
            raise ValidationError(f"required_row_fields missing {field}")
    required_sources = set(contract["required_high_value_sources"])
    for module_id in REQUIRED_HIGH_VALUE_SOURCES:
        if module_id not in required_sources:
            raise ValidationError(f"required_high_value_sources missing {module_id}")
    for pair, expected in REQUIRED_WILDCARD_SCORECARD_MAPPINGS.items():
        if contract["scorecard_pair_mapping"].get(pair) != expected:
            raise ValidationError(f"scorecard_pair_mapping missing {pair}")


def _scheduler_jobs(project_root: Path) -> dict[str, dict[str, Any]]:
    config = load_yaml(project_root / "config" / "scheduler" / "scheduler_config.yml")
    jobs = config.get("jobs", []) or []
    return {job.get("name", ""): job for job in jobs if job.get("name")}


def _validate_sources(
    project_root: Path,
    contract: dict[str, Any],
    scheduler: dict[str, dict[str, Any]],
) -> None:
    seen: set[str] = set()
    for row in contract["sources"]:
        module_id = row.get("module_id", "<missing>")
        _validate_required_fields(row, contract["required_row_fields"], module_id)
        seen.add(module_id)
        _validate_enums(row, contract)
        _validate_source_date(row, contract)
        _validate_refresh_date(row)
        _validate_scheduler_source(project_root, row, scheduler)
        _validate_blocker_issue(row)
        if row["freshness_status"] == "fresh" and row["blocker_issue"] not in (
            "",
            "none",
            None,
        ):
            raise ValidationError(f"{module_id} cannot be fresh with blocker_issue")
        _validate_fresh_source_proof(row)
        _validate_data_location(project_root, row, scheduler)
        _validate_eia_mapping(row)
    missing = sorted(set(contract["required_high_value_sources"]) - seen)
    if missing:
        raise ValidationError(
            f"Missing required high-value sources: {', '.join(missing)}"
        )


def _validate_required_fields(
    row: dict[str, Any], fields: list[str], module_id: str
) -> None:
    for field in fields:
        if field not in row:
            raise ValidationError(f"{module_id} missing required field: {field}")


def _validate_enums(row: dict[str, Any], contract: dict[str, Any]) -> None:
    freshness = row["freshness_status"]
    if freshness not in contract["freshness_status_values"]:
        raise ValidationError(
            f"{row['module_id']} has invalid freshness_status: {freshness}"
        )
    completeness = row["completeness_status"]
    if completeness not in contract["completeness_status_values"]:
        raise ValidationError(
            f"{row['module_id']} has invalid completeness_status: {completeness}"
        )


def _validate_source_date(row: dict[str, Any], contract: dict[str, Any]) -> None:
    value = row["source_data_latest_date"]
    basis = row["source_data_latest_date_basis"]
    if value is None:
        _validate_unknown_source_date(row, basis)
        return
    prohibited = set(contract["prohibited_source_data_latest_date_basis_values"])
    if basis in prohibited:
        raise ValidationError(f"{row['module_id']} rejects source date basis {basis}")
    allowed = set(contract["source_data_latest_date_basis_values"]) - {"unknown"}
    if basis not in allowed:
        raise ValidationError(
            f"{row['module_id']} invalid source_data_latest_date_basis"
        )
    _parse_iso_date(value, row["module_id"], "source_data_latest_date")


def _validate_unknown_source_date(row: dict[str, Any], basis: str) -> None:
    if basis != "unknown":
        raise ValidationError(
            f"{row['module_id']} source_data_latest_date_basis must be unknown"
        )
    reason = row["source_data_latest_date_unknown_reason"]
    if not isinstance(reason, str) or not reason.strip():
        raise ValidationError(
            f"{row['module_id']} missing source data latest date reason"
        )


def _validate_refresh_date(row: dict[str, Any]) -> None:
    value = row["last_successful_refresh"]
    if value in (None, ""):
        return
    _parse_iso_datetime_or_date(value, row["module_id"], "last_successful_refresh")


def _validate_scheduler_source(
    project_root: Path,
    row: dict[str, Any],
    scheduler: dict[str, dict[str, Any]],
) -> None:
    job_name = row["scheduler_job"]
    if job_name in ("", "none", None):
        return
    if job_name not in scheduler:
        raise ValidationError(
            f"{row['module_id']} references unknown scheduler job {job_name}"
        )
    configured_output = scheduler[job_name].get("output_dir", "")
    if row["scheduler_output_dir"] != configured_output:
        raise ValidationError(f"{row['module_id']} scheduler_output_dir mismatch")
    if row["freshness_status"] == "fresh":
        _validate_fresh_manifest(project_root, row)


def _validate_fresh_source_proof(row: dict[str, Any]) -> None:
    if row["freshness_status"] != "fresh" or row["scheduler_job"] not in (
        "",
        "none",
        None,
    ):
        return
    if row["source_data_latest_date"] in (None, ""):
        raise ValidationError(f"{row['module_id']} missing fresh source proof")
    if row["last_successful_refresh"] in (None, ""):
        raise ValidationError(f"{row['module_id']} missing fresh source proof")
    if row["last_successful_refresh_basis"] in ("", "none", None):
        raise ValidationError(f"{row['module_id']} missing fresh source proof")
    grace_days = row.get("freshness_grace_days")
    if not isinstance(grace_days, int):
        raise ValidationError(f"{row['module_id']} missing fresh source proof")
    refresh_time = _parse_iso_datetime_or_date(
        row["last_successful_refresh"], row["module_id"], "last_successful_refresh"
    )
    if datetime.now(timezone.utc) - refresh_time > timedelta(days=grace_days):
        raise ValidationError(f"{row['module_id']} fresh source proof is stale")


def _validate_fresh_manifest(project_root: Path, row: dict[str, Any]) -> None:
    manifest = project_root / row["scheduler_output_dir"] / "manifest.json"
    if not manifest.exists():
        raise ValidationError(
            f"{row['module_id']} fresh scheduler source missing manifest"
        )
    payload = load_json(manifest)
    if payload.get("status") != "success":
        raise ValidationError(f"{row['module_id']} scheduler manifest is not success")
    last_success = _parse_datetime(payload.get("last_success_ts"), row["module_id"])
    grace_days = row.get("freshness_grace_days")
    if not isinstance(grace_days, int):
        raise ValidationError(
            f"{row['module_id']} fresh source missing freshness_grace_days"
        )
    if datetime.now(timezone.utc) - last_success > timedelta(days=grace_days):
        raise ValidationError(f"{row['module_id']} scheduler manifest is stale")


def _validate_data_location(
    project_root: Path,
    row: dict[str, Any],
    scheduler: dict[str, dict[str, Any]],
) -> None:
    if row.get("external_data_root_required") is True:
        return
    data_location = row["data_location"]
    if data_location and (project_root / data_location).exists():
        return
    if _configured_output_matches_data_location(row, scheduler):
        return
    if _materialized_location_is_configured(project_root, row, scheduler):
        return
    raise ValidationError(f"{row['module_id']} data_location is not materialized")


def _configured_output_matches_data_location(
    row: dict[str, Any],
    scheduler: dict[str, dict[str, Any]],
) -> bool:
    job = scheduler.get(row["scheduler_job"])
    return bool(job and row["data_location"] == job.get("output_dir"))


def _materialized_location_is_configured(
    project_root: Path,
    row: dict[str, Any],
    scheduler: dict[str, dict[str, Any]],
) -> bool:
    materialized = row.get("materialized_module_id")
    aliases = row.get("aliases") or []
    if not materialized or (materialized == row["module_id"] and not aliases):
        return False
    if (project_root / "data" / "modules" / materialized).exists():
        return True
    job = scheduler.get(row["scheduler_job"])
    return bool(job and row["scheduler_output_dir"] == job.get("output_dir"))


def _validate_blocker_issue(row: dict[str, Any]) -> None:
    value = row["blocker_issue"]
    if value in ("", "none", None):
        return
    if re.fullmatch(r"#\d+", str(value)):
        return
    if re.fullmatch(r"https://github\.com/[^/]+/[^/]+/issues/\d+", str(value)):
        return
    raise ValidationError(f"{row['module_id']} invalid blocker_issue: {value}")


def _validate_eia_mapping(row: dict[str, Any]) -> None:
    if row["module_id"] != "eia_us":
        return
    aliases = row.get("aliases") or []
    if row.get("materialized_module_id") != "eia" or "eia" not in aliases:
        raise ValidationError(
            "eia_us must declare materialized_module_id eia and alias eia"
        )
    if row.get("scheduler_output_dir") != "data/modules/eia":
        raise ValidationError("eia_us must use scheduler output data/modules/eia")


def _validate_scorecard_pairs(project_root: Path, contract: dict[str, Any]) -> None:
    scorecard_path = project_root / "data" / "freshness-scorecard.json"
    if not scorecard_path.exists():
        return
    declared = contract["scorecard_pair_mapping"]
    scorecard = load_json(scorecard_path)
    for entry in scorecard.get("modules", {}).values():
        freshness = entry.get("freshness_status")
        catalog = entry.get("catalog_status")
        pair = f"{freshness}|{catalog}"
        expected = declared.get(pair) or declared.get(f"{freshness}|*")
        if not expected:
            raise ValidationError(f"Missing scorecard_pair_mapping for {pair}")
        actual = map_scorecard_status(freshness, catalog)
        expected_status = (
            expected["freshness_status"],
            _expected_completeness(expected, catalog),
        )
        if actual != expected_status:
            raise ValidationError(f"scorecard_pair_mapping mismatch for {pair}")


def _expected_completeness(expected: dict[str, str], catalog_status: str) -> str:
    if expected["completeness_status"] == "mapped_from_catalog_status":
        return COMPLETENESS_BY_CATALOG_STATUS[catalog_status]
    return expected["completeness_status"]


def _validate_skill_reference(project_root: Path) -> None:
    skill = project_root / ".claude/skills/worldenergydata-source-readiness/SKILL.md"
    if "source-refresh-acceptance-criteria.md" not in skill.read_text():
        raise ValidationError(
            "Skill missing source-refresh-acceptance-criteria reference"
        )


def _parse_iso_date(value: str, module_id: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{module_id} invalid {field}: {value}") from exc


def _parse_iso_datetime_or_date(value: str, module_id: str, field: str) -> datetime:
    try:
        return _parse_datetime(value, module_id)
    except ValidationError:
        parsed_date = _parse_iso_date(value, module_id, field)
        return datetime.combine(parsed_date, datetime.min.time(), tzinfo=timezone.utc)


def _parse_datetime(value: str | None, module_id: str) -> datetime:
    if not value:
        raise ValidationError(f"{module_id} scheduler manifest missing last_success_ts")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{module_id} invalid last_success_ts: {value}") from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)

    try:
        validate_contract(args.project_root.resolve())
    except ValidationError as exc:
        print(f"source refresh contract invalid: {exc}")
        return 1
    print("source refresh contract valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
