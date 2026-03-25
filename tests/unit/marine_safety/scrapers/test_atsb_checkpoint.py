"""Tests for ATSBCheckpointManager init, add/check, save/load, clear, stats."""

import json

import pytest

from worldenergydata.marine_safety.scrapers.atsb_checkpoint import (
    ATSBCheckpointManager,
)


class TestInit:
    def test_creates_directory(self, tmp_path):
        cp_dir = tmp_path / "checkpoints"
        mgr = ATSBCheckpointManager(cp_dir)
        assert cp_dir.exists()

    def test_empty_processed_ids(self, tmp_path):
        mgr = ATSBCheckpointManager(tmp_path)
        assert mgr.processed_ids == set()

    def test_last_checkpoint_time_none(self, tmp_path):
        mgr = ATSBCheckpointManager(tmp_path)
        assert mgr.last_checkpoint_time is None


class TestAddAndCheck:
    def test_add_processed_id(self, tmp_path):
        mgr = ATSBCheckpointManager(tmp_path)
        mgr.add_processed_id("MO-2022-001")
        assert "MO-2022-001" in mgr.processed_ids

    def test_is_processed_true(self, tmp_path):
        mgr = ATSBCheckpointManager(tmp_path)
        mgr.add_processed_id("MO-2022-001")
        assert mgr.is_processed("MO-2022-001") is True

    def test_is_processed_false(self, tmp_path):
        mgr = ATSBCheckpointManager(tmp_path)
        assert mgr.is_processed("MO-2022-999") is False

    def test_add_multiple(self, tmp_path):
        mgr = ATSBCheckpointManager(tmp_path)
        mgr.add_processed_id("MO-2022-001")
        mgr.add_processed_id("MO-2022-002")
        assert len(mgr.processed_ids) == 2

    def test_add_duplicate(self, tmp_path):
        mgr = ATSBCheckpointManager(tmp_path)
        mgr.add_processed_id("MO-2022-001")
        mgr.add_processed_id("MO-2022-001")
        assert len(mgr.processed_ids) == 1


class TestSaveAndLoad:
    def test_save_force(self, tmp_path):
        mgr = ATSBCheckpointManager(tmp_path)
        mgr.add_processed_id("MO-2022-001")
        mgr.save(force=True)
        assert mgr.last_checkpoint_time is not None
        cp_file = tmp_path / "atsb_scraper_checkpoint.json"
        assert cp_file.exists()

    def test_load_after_save(self, tmp_path):
        mgr = ATSBCheckpointManager(tmp_path)
        mgr.add_processed_id("MO-2022-001")
        mgr.add_processed_id("MO-2022-002")
        mgr.save(force=True)

        mgr2 = ATSBCheckpointManager(tmp_path)
        mgr2.load()
        assert mgr2.is_processed("MO-2022-001")
        assert mgr2.is_processed("MO-2022-002")
        assert len(mgr2.processed_ids) == 2

    def test_load_no_file(self, tmp_path):
        mgr = ATSBCheckpointManager(tmp_path)
        mgr.load()
        assert mgr.processed_ids == set()

    def test_load_corrupt_file(self, tmp_path):
        cp_file = tmp_path / "atsb_scraper_checkpoint.json"
        cp_file.write_text("not valid json")
        mgr = ATSBCheckpointManager(tmp_path)
        mgr.load()
        assert mgr.processed_ids == set()

    def test_save_throttle(self, tmp_path):
        mgr = ATSBCheckpointManager(tmp_path)
        mgr.add_processed_id("MO-2022-001")
        mgr.save(force=True)
        first_time = mgr.last_checkpoint_time
        mgr.add_processed_id("MO-2022-002")
        mgr.save(force=False)
        assert mgr.last_checkpoint_time == first_time


class TestClear:
    def test_clear_ids(self, tmp_path):
        mgr = ATSBCheckpointManager(tmp_path)
        mgr.add_processed_id("MO-2022-001")
        mgr.save(force=True)
        mgr.clear()
        assert len(mgr.processed_ids) == 0
        assert mgr.last_checkpoint_time is None

    def test_clear_removes_file(self, tmp_path):
        mgr = ATSBCheckpointManager(tmp_path)
        mgr.add_processed_id("MO-2022-001")
        mgr.save(force=True)
        cp_file = tmp_path / "atsb_scraper_checkpoint.json"
        assert cp_file.exists()
        mgr.clear()
        assert not cp_file.exists()


class TestGetStatistics:
    def test_empty_stats(self, tmp_path):
        mgr = ATSBCheckpointManager(tmp_path)
        stats = mgr.get_statistics()
        assert stats["total_processed_ids"] == 0
        assert stats["last_checkpoint"] is None
        assert "checkpoint_file" in stats

    def test_stats_after_processing(self, tmp_path):
        mgr = ATSBCheckpointManager(tmp_path)
        mgr.add_processed_id("MO-2022-001")
        mgr.save(force=True)
        stats = mgr.get_statistics()
        assert stats["total_processed_ids"] == 1
        assert stats["last_checkpoint"] is not None
