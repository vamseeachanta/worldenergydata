from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "audit"))

from validate_source_refresh_contract import (  # noqa: E402
    REQUIRED_HIGH_VALUE_SOURCES,
    REQUIRED_ROW_FIELDS,
    REQUIRED_WILDCARD_SCORECARD_MAPPINGS,
    ValidationError,
    map_scorecard_status,
    validate_contract,
)

FRESHNESS_VALUES = (
    "fresh stale missing blocked unknown reference_data not_applicable".split()
)
COMPLETENESS_VALUES = (
    "full sample empty missing runtime_fetched reference_data blocked unknown "
    "not_applicable"
).split()
OBSERVED_RESULTS = {
    "empty|empty": ("missing", "empty"),
    "full|full": ("unknown", "full"),
    "missing|not_applicable": ("not_applicable", "not_applicable"),
    "missing|runtime_fetched": ("missing", "runtime_fetched"),
    "not_applicable|not_applicable": ("not_applicable", "not_applicable"),
    "reference_data|reference_data": ("reference_data", "reference_data"),
    "sample|sample": ("stale", "sample"),
    "unknown|unknown": ("unknown", "unknown"),
}
OBSERVED_PAIRS = {
    pair: {"freshness_status": freshness, "completeness_status": completeness}
    for pair, (freshness, completeness) in OBSERVED_RESULTS.items()
}


def _source(module_id: str, **overrides: Any) -> dict[str, Any]:
    source = {
        "module_id": module_id,
        "materialized_module_id": module_id,
        "aliases": [],
        "display_name": module_id.replace("_", " ").title(),
        "source_authority": "unknown",
        "source_url_or_api": "unknown",
        "source_data_latest_date": None,
        "source_data_latest_date_basis": "unknown",
        "source_data_latest_date_unknown_reason": "source data vintage not inspected",
        "last_successful_refresh": None,
        "last_successful_refresh_basis": "none",
        "data_location": f"data/modules/{module_id}",
        "external_data_root_required": False,
        "scheduler_job": "none",
        "scheduler_output_dir": "",
        "refresh_command": "none",
        "record_count": None,
        "artifact_count": None,
        "refresh_cadence": "none",
        "freshness_grace_days": None,
        "freshness_status": "missing",
        "completeness_status": "missing",
        "credential_requirement": "none",
        "blocker_issue": "none",
        "downstream_consumers": [],
    }
    source.update(overrides)
    return source


def _contract(sources: list[dict[str, Any]]) -> dict[str, Any]:
    scorecard_pair_mapping = {k: dict(v) for k, v in OBSERVED_PAIRS.items()}
    scorecard_pair_mapping.update(REQUIRED_WILDCARD_SCORECARD_MAPPINGS)
    return {
        "schema_version": "1.0",
        "freshness_status_values": FRESHNESS_VALUES,
        "completeness_status_values": COMPLETENESS_VALUES,
        "source_data_latest_date_basis_values": (
            "dataset_field source_api_metadata source_publication_date "
            "source_version unknown"
        ).split(),
        "prohibited_source_data_latest_date_basis_values": (
            "metadata_refresh newest_file_modified scheduler_success manifest_timestamp"
        ).split(),
        "required_row_fields": REQUIRED_ROW_FIELDS,
        "required_high_value_sources": REQUIRED_HIGH_VALUE_SOURCES,
        "scorecard_pair_mapping": scorecard_pair_mapping,
        "sources": sources,
    }


def _write_project(root: Path, contract: dict[str, Any]) -> None:
    (root / "data").mkdir(parents=True)
    (root / "data" / "source-refresh-acceptance-contract.json").write_text(
        json.dumps(contract, indent=2) + "\n"
    )
    (root / "config" / "scheduler").mkdir(parents=True)
    (root / "config" / "scheduler" / "scheduler_config.yml").write_text(
        yaml.safe_dump(
            {
                "jobs": [
                    {
                        "name": "bsee_refresh",
                        "enabled": True,
                        "output_dir": "data/modules/bsee",
                    },
                    {
                        "name": "eia_us_refresh",
                        "enabled": True,
                        "output_dir": "data/modules/eia",
                    },
                ]
            }
        )
    )
    skill_dir = root / ".claude" / "skills" / "worldenergydata-source-readiness"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "Use docs/data/source-refresh-acceptance-criteria.md for acceptance decisions.\n"
    )
    (root / "data" / "freshness-scorecard.json").write_text(
        json.dumps(
            {
                "modules": {
                    f"pair_{idx}": {
                        "freshness_status": pair.split("|")[0],
                        "catalog_status": pair.split("|")[1],
                    }
                    for idx, pair in enumerate(OBSERVED_PAIRS)
                }
            },
            indent=2,
        )
        + "\n"
    )
    for source in contract["sources"]:
        data_location = source["data_location"]
        if data_location and not source.get("external_data_root_required"):
            if source.get("module_id") == "eia_us":
                (root / "data" / "modules" / "eia").mkdir(parents=True, exist_ok=True)
            else:
                (root / data_location).mkdir(parents=True, exist_ok=True)


def _valid_sources() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for module_id in REQUIRED_HIGH_VALUE_SOURCES:
        rows.append(_source(module_id))
    by_id = {row["module_id"]: row for row in rows}
    by_id["bsee"].update(
        {
            "scheduler_job": "bsee_refresh",
            "scheduler_output_dir": "data/modules/bsee",
            "refresh_command": "python -m worldenergydata.scheduler run-job bsee_refresh",
            "refresh_cadence": "weekly",
            "freshness_grace_days": 7,
            "freshness_status": "stale",
            "completeness_status": "sample",
            "blocker_issue": "#267",
        }
    )
    by_id["eia_us"].update(
        {
            "materialized_module_id": "eia",
            "aliases": ["eia"],
            "scheduler_job": "eia_us_refresh",
            "scheduler_output_dir": "data/modules/eia",
            "refresh_command": "python -m worldenergydata.scheduler run-job eia_us_refresh",
            "refresh_cadence": "monthly",
            "freshness_grace_days": 31,
            "freshness_status": "missing",
            "completeness_status": "runtime_fetched",
            "credential_requirement": "EIA_API_KEY",
            "blocker_issue": "#266",
        }
    )
    by_id["brazil_anp"].update(
        {
            "freshness_status": "blocked",
            "completeness_status": "runtime_fetched",
            "blocker_issue": "#459",
        }
    )
    by_id["lng_terminals"].update(
        {
            "freshness_status": "unknown",
            "completeness_status": "full",
            "blocker_issue": "#458",
        }
    )
    by_id["vessel_hull_models"].update(
        {"freshness_status": "reference_data", "completeness_status": "reference_data"}
    )
    by_id["metocean"].update(
        {
            "source_data_latest_date": "2026-06-09",
            "source_data_latest_date_basis": "source_api_metadata",
            "source_data_latest_date_unknown_reason": "",
            "last_successful_refresh": datetime.now(timezone.utc).isoformat(),
            "last_successful_refresh_basis": "source_api_metadata",
            "freshness_grace_days": 2,
            "freshness_status": "fresh",
            "external_data_root_required": True,
        }
    )
    return rows


def test_valid_minimal_contract_passes(tmp_path: Path) -> None:
    contract = _contract(_valid_sources())
    _write_project(tmp_path, contract)

    validate_contract(tmp_path)


def test_source_row_missing_required_field_fails(tmp_path: Path) -> None:
    sources = _valid_sources()
    sources[0].pop("source_authority")
    _write_project(tmp_path, _contract(sources))

    with pytest.raises(ValidationError, match="source_authority"):
        validate_contract(tmp_path)


def test_invalid_freshness_status_fails(tmp_path: Path) -> None:
    sources = _valid_sources()
    sources[0]["freshness_status"] = "sample"
    _write_project(tmp_path, _contract(sources))

    with pytest.raises(ValidationError, match="freshness_status"):
        validate_contract(tmp_path)


def test_invalid_completeness_status_fails(tmp_path: Path) -> None:
    sources = _valid_sources()
    sources[0]["completeness_status"] = "fresh"
    _write_project(tmp_path, _contract(sources))

    with pytest.raises(ValidationError, match="completeness_status"):
        validate_contract(tmp_path)


def test_required_high_value_sources_present(tmp_path: Path) -> None:
    sources = [s for s in _valid_sources() if s["module_id"] != "wind"]
    _write_project(tmp_path, _contract(sources))

    with pytest.raises(ValidationError, match="wind"):
        validate_contract(tmp_path)


def test_scheduler_source_requires_known_job(tmp_path: Path) -> None:
    sources = _valid_sources()
    sources[0]["scheduler_job"] = "missing_refresh"
    _write_project(tmp_path, _contract(sources))

    with pytest.raises(ValidationError, match="missing_refresh"):
        validate_contract(tmp_path)


def test_scheduler_source_requires_exact_configured_output_dir(tmp_path: Path) -> None:
    sources = _valid_sources()
    sources[0]["scheduler_output_dir"] = "data/modules/not_bsee"
    _write_project(tmp_path, _contract(sources))

    with pytest.raises(ValidationError, match="scheduler_output_dir"):
        validate_contract(tmp_path)


def test_fresh_scheduler_source_requires_success_manifest(tmp_path: Path) -> None:
    sources = _valid_sources()
    sources[0]["freshness_status"] = "fresh"
    _write_project(tmp_path, _contract(sources))

    with pytest.raises(ValidationError, match="manifest"):
        validate_contract(tmp_path)


def test_fresh_scheduler_source_accepts_in_cadence_success_manifest(
    tmp_path: Path,
) -> None:
    sources = _valid_sources()
    sources[0]["freshness_status"] = "fresh"
    sources[0]["blocker_issue"] = "none"
    _write_project(tmp_path, _contract(sources))
    manifest_path = tmp_path / "data" / "modules" / "bsee" / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "status": "success",
                "last_success_ts": datetime.now(timezone.utc).isoformat(),
            }
        )
    )

    validate_contract(tmp_path)


def test_observed_scorecard_pairs_map_to_contract_statuses() -> None:
    assert map_scorecard_status("missing", "runtime_fetched") == (
        "missing",
        "runtime_fetched",
    )
    assert map_scorecard_status("missing", "not_applicable") == (
        "not_applicable",
        "not_applicable",
    )
    for pair, expected in OBSERVED_PAIRS.items():
        freshness, catalog = pair.split("|")
        assert map_scorecard_status(freshness, catalog) == (
            expected["freshness_status"],
            expected["completeness_status"],
        )


def test_unknown_source_date_requires_basis_and_reason(tmp_path: Path) -> None:
    sources = _valid_sources()
    sources[0]["source_data_latest_date_basis"] = "dataset_field"
    _write_project(tmp_path, _contract(sources))

    with pytest.raises(ValidationError, match="source_data_latest_date_basis"):
        validate_contract(tmp_path)


def test_non_null_source_date_rejects_metadata_file_scheduler_basis(
    tmp_path: Path,
) -> None:
    sources = _valid_sources()
    sources[0]["source_data_latest_date"] = "2026-06-01"
    sources[0]["source_data_latest_date_basis"] = "metadata_refresh"
    sources[0]["source_data_latest_date_unknown_reason"] = ""
    _write_project(tmp_path, _contract(sources))

    with pytest.raises(ValidationError, match="metadata_refresh"):
        validate_contract(tmp_path)


def test_source_date_and_refresh_date_are_distinct_fields(tmp_path: Path) -> None:
    sources = _valid_sources()
    sources[0]["source_data_latest_date"] = "2026-06-01"
    sources[0]["source_data_latest_date_basis"] = "dataset_field"
    sources[0]["source_data_latest_date_unknown_reason"] = ""
    sources[0]["last_successful_refresh"] = "2026-06-01"
    sources[0]["last_successful_refresh_basis"] = "scheduler_success"
    _write_project(tmp_path, _contract(sources))

    validate_contract(tmp_path)


def test_eia_us_alias_materialization_mapping_is_explicit(tmp_path: Path) -> None:
    sources = _valid_sources()
    eia = next(source for source in sources if source["module_id"] == "eia_us")
    eia["materialized_module_id"] = ""
    eia["aliases"] = []
    _write_project(tmp_path, _contract(sources))

    with pytest.raises(ValidationError, match="eia_us"):
        validate_contract(tmp_path)


def test_contract_fixture_covers_required_lanes() -> None:
    statuses = {source["freshness_status"] for source in _valid_sources()}
    assert {"fresh", "stale", "missing", "blocked", "reference_data"} <= statuses
    completeness = {source["completeness_status"] for source in _valid_sources()}
    assert {"sample", "runtime_fetched", "reference_data", "full"} <= completeness


def test_skill_references_contract(tmp_path: Path) -> None:
    contract = _contract(_valid_sources())
    _write_project(tmp_path, contract)
    skill = (
        tmp_path
        / ".claude"
        / "skills"
        / "worldenergydata-source-readiness"
        / "SKILL.md"
    )
    skill.write_text("No contract reference.\n")

    with pytest.raises(ValidationError, match="source-refresh-acceptance-criteria"):
        validate_contract(tmp_path)
