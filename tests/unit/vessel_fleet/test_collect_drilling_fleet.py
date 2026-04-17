"""Tests for extended drilling fleet collection with multi-source fallback.

Verifies the fallback chain: web scrape → scrape JSON → KNOWN_VESSELS.
"""

from __future__ import annotations

# Import will be from the module-level function, not the script
# The testable logic is extracted into collect_operator_fleet()
import importlib
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_PROJECT_ROOT / "scripts" / "vessel_fleet"))

# Re-import after path setup
from collect_drilling_fleet import (
    _collect_from_scrape_json,
    _load_known_vessels,
    collect_operator_fleet,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_config_module(tmp_path: Path) -> str:
    """Create a temporary config module with known vessels."""
    pkg = tmp_path / "test_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")

    (pkg / "test_config.py").write_text(
        """
from worldenergydata.vessel_fleet.collectors.fleet_page_collector import ContractorConfig

CONFIG = ContractorConfig(
    name="test_operator",
    fleet_url="https://example.com/fleet",
    vessel_category="drilling_rig",
    vessel_type="drilling_rig",
    owner="Test Corp",
    rate_limit=0.5,
)

KNOWN_VESSELS = [
    {"VESSEL_NAME": "Test Rig Alpha", "RIG_TYPE": "drillship"},
    {"VESSEL_NAME": "Test Rig Beta", "RIG_TYPE": "jack_up"},
]
"""
    )
    sys.path.insert(0, str(tmp_path))
    return "test_pkg.test_config"


@pytest.fixture
def scrape_dir_with_json(tmp_path: Path) -> Path:
    """Create a scrape directory with a test operator JSON file."""
    scrape_dir = tmp_path / "contractor_scrape"
    scrape_dir.mkdir(parents=True)

    # Minimal Noble-like scrape JSON
    noble_data = {
        "name": "noble",
        "owner": "Noble Corporation plc",
        "links": [],
        "rawHtml": "",
    }
    (scrape_dir / "noble.json").write_text(json.dumps(noble_data))
    return scrape_dir


# ---------------------------------------------------------------------------
# _load_known_vessels
# ---------------------------------------------------------------------------
class TestLoadKnownVessels:
    """Known vessel loading from configs."""

    def test_loads_real_noble_config(self):
        records = _load_known_vessels(
            "worldenergydata.vessel_fleet.config.drilling.noble"
        )
        assert len(records) >= 25  # Noble has 31 KNOWN_VESSELS

    def test_sets_default_fields(self):
        records = _load_known_vessels(
            "worldenergydata.vessel_fleet.config.drilling.noble"
        )
        for rec in records:
            assert rec.get("OWNER") == "Noble Corporation plc"
            assert rec.get("VESSEL_CATEGORY") == "drilling_rig"
            assert rec.get("DATA_SOURCE") == "contractor_fleet_page"

    def test_nonexistent_module_returns_empty(self):
        records = _load_known_vessels("nonexistent.module.path")
        assert records == []


# ---------------------------------------------------------------------------
# _collect_from_scrape_json
# ---------------------------------------------------------------------------
class TestCollectFromScrapeJson:
    """Scrape JSON parsing as intermediate source."""

    def test_noble_real_json(self):
        scrape_dir = _PROJECT_ROOT / "data/modules/vessel_fleet/raw/contractor_scrape"
        if not (scrape_dir / "noble.json").exists():
            pytest.skip("Noble scrape JSON not found")
        records = _collect_from_scrape_json("noble", scrape_dir)
        assert len(records) == 31

    def test_seadrill_real_json(self):
        scrape_dir = _PROJECT_ROOT / "data/modules/vessel_fleet/raw/contractor_scrape"
        if not (scrape_dir / "seadrill.json").exists():
            pytest.skip("Seadrill scrape JSON not found")
        records = _collect_from_scrape_json("seadrill", scrape_dir)
        assert len(records) == 17

    def test_unknown_operator_returns_empty(self, tmp_path):
        records = _collect_from_scrape_json("nonexistent", tmp_path)
        assert records == []

    def test_empty_json_returns_empty(self, scrape_dir_with_json):
        records = _collect_from_scrape_json("noble", scrape_dir_with_json)
        assert records == []


# ---------------------------------------------------------------------------
# collect_operator_fleet
# ---------------------------------------------------------------------------
class TestCollectOperatorFleet:
    """Multi-source fallback chain."""

    def test_known_vessels_as_fallback(self, sample_config_module):
        """With no web or scrape data, returns KNOWN_VESSELS."""
        records = collect_operator_fleet(
            config_path=sample_config_module,
            scrape_dir=Path("/nonexistent"),
            try_web=False,
        )
        assert len(records) == 2
        names = {r["VESSEL_NAME"] for r in records}
        assert "Test Rig Alpha" in names
        assert "Test Rig Beta" in names

    def test_known_vessels_have_source_fields(self, sample_config_module):
        records = collect_operator_fleet(
            config_path=sample_config_module,
            scrape_dir=Path("/nonexistent"),
            try_web=False,
        )
        for rec in records:
            assert rec.get("DATA_SOURCE") == "contractor_fleet_page"
            assert rec.get("OWNER") == "Test Corp"

    def test_scrape_json_preferred_over_known_vessels(self):
        """Scrape JSON is selected when it ties with KNOWN_VESSELS count.

        Noble has 31 in both sources; max() returns first candidate
        (insertion order: scrape_json before known_vessels). Verify by
        checking a field that only the scrape parser produces.
        """
        scrape_dir = _PROJECT_ROOT / "data/modules/vessel_fleet/raw/contractor_scrape"
        if not (scrape_dir / "noble.json").exists():
            pytest.skip("Noble scrape JSON not found")

        records = collect_operator_fleet(
            config_path="worldenergydata.vessel_fleet.config.drilling.noble",
            scrape_dir=scrape_dir,
            try_web=False,
        )
        assert len(records) >= 31
        # Scrape parser adds WATER_DEPTH_RATING_FT for some rigs;
        # KNOWN_VESSELS don't have this field. If any record has it,
        # the scrape_json source was selected.
        has_wd = any(r.get("WATER_DEPTH_RATING_FT") for r in records)
        assert has_wd, (
            "Expected WATER_DEPTH_RATING_FT from scrape parser, "
            "but none found — KNOWN_VESSELS may have been selected instead"
        )

    def test_best_source_wins_by_count(self, sample_config_module):
        """Source with the most records wins, not insertion order.

        Mock _collect_from_scrape_json to return 5 records (more than
        KNOWN_VESSELS' 2), verify we get 5 back.
        """
        mock_scrape = [
            {"VESSEL_NAME": f"Scrape Rig {i}", "RIG_TYPE": "drillship"}
            for i in range(5)
        ]
        with patch(
            "collect_drilling_fleet._collect_from_scrape_json",
            return_value=mock_scrape,
        ):
            records = collect_operator_fleet(
                config_path=sample_config_module,
                scrape_dir=Path("/fake"),
                try_web=False,
            )
        assert len(records) == 5
        assert records[0]["VESSEL_NAME"] == "Scrape Rig 0"

    def test_web_scrape_disabled_by_default(self, sample_config_module):
        """Web scraping should not be attempted when try_web=False."""
        with patch("collect_drilling_fleet.FleetPageCollector") as mock_collector:
            collect_operator_fleet(
                config_path=sample_config_module,
                scrape_dir=Path("/nonexistent"),
                try_web=False,
            )
            mock_collector.assert_not_called()

    def test_web_scrape_failure_falls_back(self, sample_config_module):
        """Failed web scrape should fall back to KNOWN_VESSELS."""
        with patch("collect_drilling_fleet.FleetPageCollector") as mock_cls:
            mock_cls.return_value.collect.side_effect = Exception("403 Forbidden")
            records = collect_operator_fleet(
                config_path=sample_config_module,
                scrape_dir=Path("/nonexistent"),
                try_web=True,
            )
            assert len(records) == 2  # Falls back to KNOWN_VESSELS


class TestCollectionSummary:
    """Integration test with real configs."""

    def test_all_configs_load_without_error(self):
        """Every drilling config should load without exceptions."""
        from collect_drilling_fleet import _DRILLING_CONFIGS

        for config_path in _DRILLING_CONFIGS:
            records = _load_known_vessels(config_path)
            # All should succeed (may return 0 records for sparse configs)
            assert isinstance(records, list), f"Failed: {config_path}"

    def test_total_known_vessels_reasonable(self):
        """Combined KNOWN_VESSELS across all operators should be substantial."""
        from collect_drilling_fleet import _DRILLING_CONFIGS

        total = 0
        for config_path in _DRILLING_CONFIGS:
            records = _load_known_vessels(config_path)
            total += len(records)
        # Should have at least 50 rigs across all operators
        assert total >= 50, f"Only {total} known vessels across all configs"
