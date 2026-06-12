from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "audit"))

from test_source_refresh_contract import _contract, _valid_sources, _write_project
from validate_source_refresh_contract import (  # noqa: E402
    REQUIRED_HIGH_VALUE_SOURCES,
    ValidationError,
    validate_contract,
)


def test_non_scheduler_fresh_source_requires_source_proof(tmp_path: Path) -> None:
    sources = _valid_sources()
    metocean = next(source for source in sources if source["module_id"] == "metocean")
    metocean["scheduler_job"] = "none"
    metocean["scheduler_output_dir"] = ""
    metocean["source_data_latest_date"] = None
    metocean["source_data_latest_date_basis"] = "unknown"
    metocean["source_data_latest_date_unknown_reason"] = "source proof missing"
    metocean["last_successful_refresh"] = None
    _write_project(tmp_path, _contract(sources))

    with pytest.raises(ValidationError, match="fresh source proof"):
        validate_contract(tmp_path)


def test_scorecard_fresh_sample_pair_is_accepted(tmp_path: Path) -> None:
    contract = _contract(_valid_sources())
    _write_project(tmp_path, contract)
    (tmp_path / "data" / "freshness-scorecard.json").write_text(
        json.dumps(
            {
                "modules": {
                    "bsee": {"freshness_status": "fresh", "catalog_status": "sample"}
                }
            }
        )
    )

    validate_contract(tmp_path)


def test_scorecard_stale_full_pair_is_accepted(tmp_path: Path) -> None:
    contract = _contract(_valid_sources())
    _write_project(tmp_path, contract)
    (tmp_path / "data" / "freshness-scorecard.json").write_text(
        json.dumps(
            {
                "modules": {
                    "lng": {"freshness_status": "stale", "catalog_status": "full"}
                }
            }
        )
    )

    validate_contract(tmp_path)


def test_contract_requires_wildcard_scorecard_mappings(tmp_path: Path) -> None:
    contract = _contract(_valid_sources())
    del contract["scorecard_pair_mapping"]["fresh|*"]
    _write_project(tmp_path, contract)

    with pytest.raises(ValidationError, match=r"fresh\|\*"):
        validate_contract(tmp_path)


def test_malformed_manifest_reports_validation_error(tmp_path: Path) -> None:
    sources = _valid_sources()
    bsee = sources[0]
    bsee["freshness_status"] = "fresh"
    bsee["blocker_issue"] = "none"
    _write_project(tmp_path, _contract(sources))
    (tmp_path / "data" / "modules" / "bsee" / "manifest.json").write_text("{bad json")

    with pytest.raises(ValidationError, match="Invalid JSON"):
        validate_contract(tmp_path)


def test_source_with_blocker_cannot_be_fresh(tmp_path: Path) -> None:
    sources = _valid_sources()
    brazil = next(source for source in sources if source["module_id"] == "brazil_anp")
    brazil["freshness_status"] = "fresh"
    _write_project(tmp_path, _contract(sources))

    with pytest.raises(ValidationError, match="blocker"):
        validate_contract(tmp_path)


def test_non_scheduler_fresh_source_requires_refresh_basis(tmp_path: Path) -> None:
    sources = _valid_sources()
    metocean = next(source for source in sources if source["module_id"] == "metocean")
    metocean["last_successful_refresh_basis"] = "none"
    _write_project(tmp_path, _contract(sources))

    with pytest.raises(ValidationError, match="fresh source proof"):
        validate_contract(tmp_path)


def test_required_high_value_source_list_cannot_drop_known_source(
    tmp_path: Path,
) -> None:
    contract = _contract(_valid_sources())
    contract["required_high_value_sources"] = [
        source for source in REQUIRED_HIGH_VALUE_SOURCES if source != "wind"
    ]
    _write_project(tmp_path, contract)

    with pytest.raises(ValidationError, match="wind"):
        validate_contract(tmp_path)
