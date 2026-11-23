"""Tests for SODIR collection workflow."""

from datetime import datetime, timedelta

from worldenergydata.sodir.workflows.collection import CollectionWorkflow


class TestCollectionWorkflowInit:
    def test_defaults(self):
        wf = CollectionWorkflow({})
        assert wf.name == "default_workflow"
        assert wf.datasets == []
        assert wf.schedule == "daily"
        assert wf.filters == {}
        assert wf.validation_enabled is True
        assert wf.validation_strict is False
        assert wf.storage_config == {}
        assert wf.api_client is None
        assert wf.sodir_data is None
        assert wf.last_execution is None
        assert wf.execution_history == []

    def test_custom_config(self):
        cfg = {
            "name": "test_workflow",
            "datasets": ["blocks", "fields"],
            "schedule": "weekly",
            "filters": {"status": "active"},
            "validation": {"enabled": False, "strict": True},
            "storage": {"path": "/tmp"},
        }
        wf = CollectionWorkflow(cfg)
        assert wf.name == "test_workflow"
        assert wf.datasets == ["blocks", "fields"]
        assert wf.schedule == "weekly"
        assert wf.filters == {"status": "active"}
        assert wf.validation_enabled is False
        assert wf.validation_strict is True
        assert wf.storage_config == {"path": "/tmp"}

    def test_partial_validation_config(self):
        wf = CollectionWorkflow({"validation": {"enabled": True}})
        assert wf.validation_enabled is True
        assert wf.validation_strict is False


class TestGetDatasetsToCollect:
    def test_configured_datasets(self):
        wf = CollectionWorkflow({"datasets": ["blocks", "fields"]})
        result = wf._get_datasets_to_collect()
        assert result == ["blocks", "fields"]

    def test_default_datasets(self):
        wf = CollectionWorkflow({})
        result = wf._get_datasets_to_collect()
        assert result == ["blocks", "wellbores", "fields", "discoveries", "surveys"]


class TestPrepareFilters:
    def test_empty_filters(self):
        wf = CollectionWorkflow({})
        result = wf._prepare_filters()
        assert result == {}

    def test_static_filters_preserved(self):
        wf = CollectionWorkflow({"filters": {"status": "active"}})
        result = wf._prepare_filters()
        assert result["status"] == "active"

    def test_yesterday_filter(self):
        wf = CollectionWorkflow({"filters": {"updated_since": "yesterday"}})
        result = wf._prepare_filters()
        # Should have been replaced with an ISO date string
        assert result["updated_since"] != "yesterday"
        assert "T" in result["updated_since"]  # ISO format

    def test_last_week_filter(self):
        wf = CollectionWorkflow({"filters": {"updated_since": "last_week"}})
        result = wf._prepare_filters()
        assert result["updated_since"] != "last_week"
        assert "T" in result["updated_since"]

    def test_other_filter_unchanged(self):
        wf = CollectionWorkflow({"filters": {"updated_since": "2024-01-01"}})
        result = wf._prepare_filters()
        assert result["updated_since"] == "2024-01-01"


class TestGetExecutionHistory:
    def test_empty(self):
        wf = CollectionWorkflow({})
        assert wf.get_execution_history() == []

    def test_with_history(self):
        wf = CollectionWorkflow({})
        entry = {"timestamp": datetime.utcnow(), "success": True}
        wf.execution_history.append(entry)
        history = wf.get_execution_history()
        assert len(history) == 1
        assert history[0] is entry


class TestGetNextExecutionTime:
    def test_no_last_execution(self):
        wf = CollectionWorkflow({})
        result = wf.get_next_execution_time()
        assert result is not None
        # Should be approximately now
        assert abs((result - datetime.utcnow()).total_seconds()) < 2

    def test_hourly(self):
        wf = CollectionWorkflow({"schedule": "hourly"})
        last = datetime(2024, 6, 15, 10, 0, 0)
        wf.last_execution = last
        result = wf.get_next_execution_time()
        assert result == last + timedelta(hours=1)

    def test_daily(self):
        wf = CollectionWorkflow({"schedule": "daily"})
        last = datetime(2024, 6, 15, 10, 0, 0)
        wf.last_execution = last
        result = wf.get_next_execution_time()
        assert result == last + timedelta(days=1)

    def test_weekly(self):
        wf = CollectionWorkflow({"schedule": "weekly"})
        last = datetime(2024, 6, 15, 10, 0, 0)
        wf.last_execution = last
        result = wf.get_next_execution_time()
        assert result == last + timedelta(weeks=1)

    def test_unknown_schedule(self):
        wf = CollectionWorkflow({"schedule": "yearly"})
        wf.last_execution = datetime(2024, 1, 1)
        result = wf.get_next_execution_time()
        assert result is None
