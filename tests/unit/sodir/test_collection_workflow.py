"""Tests for sodir.workflows.collection CollectionWorkflow."""

from datetime import datetime, timedelta

import pytest

from worldenergydata.sodir.workflows.collection import CollectionWorkflow


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

class TestCollectionWorkflowInit:
    def test_default_config(self):
        wf = CollectionWorkflow({"name": "test"})
        assert wf.name == "test"
        assert wf.datasets == []
        assert wf.schedule == "daily"
        assert wf.validation_enabled is True
        assert wf.validation_strict is False
        assert wf.api_client is None
        assert wf.sodir_data is None
        assert wf.last_execution is None
        assert wf.execution_history == []

    def test_full_config(self):
        cfg = {
            "name": "full_workflow",
            "datasets": ["blocks", "fields"],
            "schedule": "weekly",
            "filters": {"status": "active"},
            "validation": {"enabled": False, "strict": True},
            "storage": {"path": "/tmp/data"},
        }
        wf = CollectionWorkflow(cfg)
        assert wf.name == "full_workflow"
        assert wf.datasets == ["blocks", "fields"]
        assert wf.schedule == "weekly"
        assert wf.filters == {"status": "active"}
        assert wf.validation_enabled is False
        assert wf.validation_strict is True
        assert wf.storage_config == {"path": "/tmp/data"}

    def test_missing_name_uses_default(self):
        wf = CollectionWorkflow({})
        assert wf.name == "default_workflow"


# ---------------------------------------------------------------------------
# _get_datasets_to_collect
# ---------------------------------------------------------------------------

class TestGetDatasetsToCollect:
    def test_configured_datasets(self):
        wf = CollectionWorkflow({"datasets": ["blocks", "fields"]})
        result = wf._get_datasets_to_collect()
        assert result == ["blocks", "fields"]

    def test_default_datasets(self):
        wf = CollectionWorkflow({"datasets": []})
        result = wf._get_datasets_to_collect()
        assert "blocks" in result
        assert "wellbores" in result
        assert "fields" in result
        assert "discoveries" in result
        assert "surveys" in result


# ---------------------------------------------------------------------------
# _prepare_filters
# ---------------------------------------------------------------------------

class TestPrepareFilters:
    def test_static_filters(self):
        wf = CollectionWorkflow({"filters": {"status": "active", "region": "north"}})
        result = wf._prepare_filters()
        assert result["status"] == "active"
        assert result["region"] == "north"

    def test_yesterday_filter(self):
        wf = CollectionWorkflow({"filters": {"updated_since": "yesterday"}})
        result = wf._prepare_filters()
        # Should be an ISO datetime string, not "yesterday"
        assert result["updated_since"] != "yesterday"
        assert "T" in result["updated_since"]

    def test_last_week_filter(self):
        wf = CollectionWorkflow({"filters": {"updated_since": "last_week"}})
        result = wf._prepare_filters()
        assert result["updated_since"] != "last_week"
        assert "T" in result["updated_since"]

    def test_no_filters(self):
        wf = CollectionWorkflow({})
        result = wf._prepare_filters()
        assert result == {}


# ---------------------------------------------------------------------------
# get_execution_history
# ---------------------------------------------------------------------------

class TestGetExecutionHistory:
    def test_empty_history(self):
        wf = CollectionWorkflow({})
        assert wf.get_execution_history() == []

    def test_with_entries(self):
        wf = CollectionWorkflow({})
        wf.execution_history.append({"timestamp": datetime.utcnow(), "success": True})
        assert len(wf.get_execution_history()) == 1


# ---------------------------------------------------------------------------
# get_next_execution_time
# ---------------------------------------------------------------------------

class TestGetNextExecutionTime:
    def test_no_last_execution(self):
        wf = CollectionWorkflow({"schedule": "daily"})
        result = wf.get_next_execution_time()
        assert result is not None

    def test_hourly_schedule(self):
        wf = CollectionWorkflow({"schedule": "hourly"})
        now = datetime.utcnow()
        wf.last_execution = now
        result = wf.get_next_execution_time()
        expected = now + timedelta(hours=1)
        assert abs((result - expected).total_seconds()) < 1

    def test_daily_schedule(self):
        wf = CollectionWorkflow({"schedule": "daily"})
        now = datetime.utcnow()
        wf.last_execution = now
        result = wf.get_next_execution_time()
        expected = now + timedelta(days=1)
        assert abs((result - expected).total_seconds()) < 1

    def test_weekly_schedule(self):
        wf = CollectionWorkflow({"schedule": "weekly"})
        now = datetime.utcnow()
        wf.last_execution = now
        result = wf.get_next_execution_time()
        expected = now + timedelta(weeks=1)
        assert abs((result - expected).total_seconds()) < 1

    def test_unknown_schedule_returns_none(self):
        wf = CollectionWorkflow({"schedule": "monthly"})
        wf.last_execution = datetime.utcnow()
        result = wf.get_next_execution_time()
        assert result is None
