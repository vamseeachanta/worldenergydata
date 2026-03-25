"""Tests for lng_terminals.reports.quality_dashboard QualityDashboard."""

import json
from unittest.mock import MagicMock, patch

import pytest

from worldenergydata.lng_terminals.reports.quality_dashboard import QualityDashboard


class TestScoreDistribution:
    def _make_dashboard(self):
        qd = QualityDashboard.__new__(QualityDashboard)
        qd.terminals = []
        return qd

    def test_all_buckets(self):
        qd = self._make_dashboard()
        result = qd._score_distribution([10, 30, 50, 70, 90])
        assert result == {"0-20": 1, "20-40": 1, "40-60": 1, "60-80": 1, "80-100": 1}

    def test_empty_list(self):
        qd = self._make_dashboard()
        result = qd._score_distribution([])
        assert result == {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}

    def test_all_high_scores(self):
        qd = self._make_dashboard()
        result = qd._score_distribution([80, 85, 90, 95, 100])
        assert result["80-100"] == 5
        assert result["0-20"] == 0

    def test_all_low_scores(self):
        qd = self._make_dashboard()
        result = qd._score_distribution([0, 5, 10, 15, 19])
        assert result["0-20"] == 5
        assert result["80-100"] == 0

    def test_boundary_values(self):
        qd = self._make_dashboard()
        result = qd._score_distribution([0, 20, 40, 60, 80])
        assert result["0-20"] == 1
        assert result["20-40"] == 1
        assert result["40-60"] == 1
        assert result["60-80"] == 1
        assert result["80-100"] == 1


class TestQualityDashboardInit:
    def test_init_stores_terminals(self):
        mock_terminals = [MagicMock(), MagicMock()]
        qd = QualityDashboard(mock_terminals)
        assert qd.terminals == mock_terminals
        assert len(qd.terminals) == 2

    def test_init_empty_list(self):
        qd = QualityDashboard([])
        assert qd.terminals == []


class TestExportJson:
    def test_export_writes_file(self, tmp_path):
        mock_score = MagicMock()
        mock_score.total_score = 75.0
        mock_score.required_fields_score = 90.0
        mock_score.optional_fields_score = 60.0
        mock_score.engineering_score = 50.0
        mock_score.source_count = 2

        mock_terminal = MagicMock()
        mock_terminal.data_quality_score = mock_score

        qd = QualityDashboard([mock_terminal])
        with patch.object(qd, "generate_report", return_value={"test": True}):
            outpath = tmp_path / "report.json"
            result = qd.export_json(outpath)
            assert outpath.exists()
            data = json.loads(outpath.read_text())
            assert data == {"test": True}
