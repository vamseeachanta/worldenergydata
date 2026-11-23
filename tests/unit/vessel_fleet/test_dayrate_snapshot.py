# ABOUTME: Tests for the public day-rate snapshot (#596): YAML loader, per-class
# ABOUTME: median/band rollup, confidence labels, and catalog attach helper.
"""Tests for ``dayrate_snapshot``.

CI-safe: the rollup logic is exercised against a tiny synthetic snapshot written
to ``tmp_path`` (no network, no off-repo data). One test loads the committed
real YAML and asserts the drillship + intervention classes are present with
sources.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from worldenergydata.vessel_fleet import dayrate_snapshot as ds

# --- Synthetic fixture ------------------------------------------------------

_SNAPSHOT_DOC = {
    "snapshot": "public_dayrate_snapshot",
    "as_of": "2026-02-19",
    "caveat": "PUBLIC SNAPSHOT, NOT A SUBSCRIPTION FEED.",
    "records": [
        {
            "asset_class": "modu_drillship",
            "name": "Rig A",
            "rate_usd_per_day": 460000,
            "region": "US GoM",
            "as_of_date": "2026-02-19",
            "source_url": "https://example.com/fsr",
            "confidence": "on_record",
        },
        {
            "asset_class": "modu_drillship",
            "name": "Rig B",
            "rate_usd_per_day": 500000,
            "region": "US GoM",
            "as_of_date": "2026-02-19",
            "source_url": "https://example.com/fsr",
            "confidence": "on_record",
        },
        {
            "asset_class": "modu_drillship",
            "name": "Market band",
            "rate_low_usd_per_day": 400000,
            "rate_high_usd_per_day": 420000,
            "region": "global",
            "as_of_date": "2026-01-01",
            "source_url": "https://example.com/analyst",
            "confidence": "analyst",
        },
        {
            "asset_class": "heavy_intervention_semi",
            "name": "Helix Q-class",
            "rate_usd_per_day": None,
            "rate_disclosed": False,
            "region": "US GoM",
            "as_of_date": "2025-12-31",
            "source_url": "https://example.com/helix",
            "confidence": "not_public",
        },
        {
            "asset_class": "mpsv_osv",
            "name": "North Sea PSV",
            "rate_low_usd_per_day": 22000,
            "rate_high_usd_per_day": 32000,
            "region": "North Sea",
            "as_of_date": "2026-05-06",
            "source_url": "https://example.com/osv",
            "confidence": "reported",
        },
    ],
}


def _write_snapshot(tmp_path: Path) -> Path:
    snap = tmp_path / "dayrate_snapshot.yml"
    snap.write_text(yaml.safe_dump(_SNAPSHOT_DOC, sort_keys=False), encoding="utf-8")
    return snap


# --- load_dayrate_snapshot --------------------------------------------------


class TestLoadDayrateSnapshot:
    def test_loads_records_and_as_of(self, tmp_path):
        snap_path = _write_snapshot(tmp_path)
        doc = ds.load_dayrate_snapshot(snap_path)
        assert doc["as_of"] == "2026-02-19"
        assert len(doc["records"]) == 5

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ds.load_dayrate_snapshot(tmp_path / "nope.yml")


# --- summary_by_asset_class -------------------------------------------------


class TestSummaryByAssetClass:
    def test_drillship_median_and_band(self, tmp_path):
        snap = ds.load_dayrate_snapshot(_write_snapshot(tmp_path))
        summary = ds.summary_by_asset_class(snap)
        ds_summary = summary["modu_drillship"]
        # Representatives: 460000, 500000, midpoint(400000,420000)=410000.
        # Median of [460000, 500000, 410000] = 460000.
        assert ds_summary["median_usd_per_day"] == 460000
        # Band spans the lowest low (400000) to highest point (500000).
        assert ds_summary["band_low_usd_per_day"] == 400000
        assert ds_summary["band_high_usd_per_day"] == 500000
        assert ds_summary["rate_count"] == 3
        assert ds_summary["rate_disclosed"] is True

    def test_confidence_labels_collected(self, tmp_path):
        snap = ds.load_dayrate_snapshot(_write_snapshot(tmp_path))
        summary = ds.summary_by_asset_class(snap)
        labels = summary["modu_drillship"]["confidence_labels"]
        assert labels == ["analyst", "on_record"]

    def test_not_public_class_has_null_band(self, tmp_path):
        snap = ds.load_dayrate_snapshot(_write_snapshot(tmp_path))
        summary = ds.summary_by_asset_class(snap)
        heavy = summary["heavy_intervention_semi"]
        assert heavy["rate_disclosed"] is False
        assert heavy["median_usd_per_day"] is None
        assert heavy["band_low_usd_per_day"] is None
        assert heavy["confidence_labels"] == ["not_public"]

    def test_mpsv_band_from_range_only(self, tmp_path):
        snap = ds.load_dayrate_snapshot(_write_snapshot(tmp_path))
        summary = ds.summary_by_asset_class(snap)
        mpsv = summary["mpsv_osv"]
        assert mpsv["band_low_usd_per_day"] == 22000
        assert mpsv["band_high_usd_per_day"] == 32000
        # Midpoint 27000 is the only representative -> median 27000.
        assert mpsv["median_usd_per_day"] == 27000


# --- attach_dayrates_to_catalog ---------------------------------------------


class TestAttachDayratesToCatalog:
    def test_attaches_band_to_priced_classes_only(self, tmp_path):
        snap = ds.load_dayrate_snapshot(_write_snapshot(tmp_path))
        catalog = {
            "by_asset_class": {
                "modu_drillship": {"count": 10},
                "modu_jackup": {"count": 50},
            }
        }
        enriched = ds.attach_dayrates_to_catalog(catalog, snap)
        assert "indicative_dayrate" in enriched["by_asset_class"]["modu_drillship"]
        # modu_jackup is not a priced snapshot class -> no band attached.
        assert "indicative_dayrate" not in enriched["by_asset_class"]["modu_jackup"]
        assert enriched["dayrate_snapshot_as_of"] == "2026-02-19"

    def test_input_catalog_not_mutated(self, tmp_path):
        snap = ds.load_dayrate_snapshot(_write_snapshot(tmp_path))
        catalog = {"by_asset_class": {"modu_drillship": {"count": 10}}}
        ds.attach_dayrates_to_catalog(catalog, snap)
        assert "indicative_dayrate" not in catalog["by_asset_class"]["modu_drillship"]


# --- Real committed YAML integration ----------------------------------------

_REAL_SNAPSHOT = (
    Path(__file__).resolve().parents[3]
    / "packages/worldenergydata-vessel_fleet/src/worldenergydata"
    / "vessel_fleet/data/dayrate_snapshot.yml"
)


@pytest.mark.skipif(
    not _REAL_SNAPSHOT.is_file(), reason="committed dayrate_snapshot.yml not found"
)
def test_real_snapshot_classes_and_sources():
    doc = ds.load_dayrate_snapshot(_REAL_SNAPSHOT)
    summary = ds.summary_by_asset_class(doc)
    # Drillship class is priced on_record; intervention classes are present.
    assert summary["modu_drillship"]["rate_disclosed"] is True
    assert summary["modu_drillship"]["band_high_usd_per_day"] >= 500000
    assert "heavy_intervention_semi" in summary
    assert "rlwi_monohull" in summary
    # Every record carries a source_url and a known confidence label.
    for rec in doc["records"]:
        assert rec["source_url"].startswith("http")
        assert rec["confidence"] in ds.CONFIDENCE_LABELS
    # Top-level public-snapshot caveat is present.
    assert "NOT A SUBSCRIPTION FEED" in doc["caveat"]
    assert len(doc["sources"]) >= 5
