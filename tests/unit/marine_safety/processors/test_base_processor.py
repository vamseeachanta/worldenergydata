"""Tests for base processor."""

from worldenergydata.marine_safety.processors.base_processor import BaseProcessor


class ConcreteProcessor(BaseProcessor):
    """Concrete implementation for testing the abstract base class."""

    def process(self, data):
        if data is None:
            return None
        self.stats["processed"] += 1
        return {"processed": True, **data}


class TestBaseProcessor:
    def test_init_defaults(self):
        p = ConcreteProcessor()
        assert p.config == {}
        assert p.stats == {"processed": 0, "errors": 0, "warnings": 0}

    def test_init_with_config(self):
        p = ConcreteProcessor(config={"key": "value"})
        assert p.config["key"] == "value"

    def test_validate_none(self):
        p = ConcreteProcessor()
        assert p.validate(None) is False

    def test_validate_data(self):
        p = ConcreteProcessor()
        assert p.validate({"key": "value"}) is True

    def test_validate_empty_dict(self):
        p = ConcreteProcessor()
        assert p.validate({}) is True

    def test_get_stats(self):
        p = ConcreteProcessor()
        stats = p.get_stats()
        assert stats == {"processed": 0, "errors": 0, "warnings": 0}

    def test_get_stats_returns_copy(self):
        p = ConcreteProcessor()
        stats = p.get_stats()
        stats["processed"] = 999
        assert p.stats["processed"] == 0

    def test_reset_stats(self):
        p = ConcreteProcessor()
        p.stats["processed"] = 10
        p.stats["errors"] = 2
        p.reset_stats()
        assert p.stats == {"processed": 0, "errors": 0, "warnings": 0}

    def test_process(self):
        p = ConcreteProcessor()
        result = p.process({"name": "test"})
        assert result["processed"] is True
        assert result["name"] == "test"

    def test_process_updates_stats(self):
        p = ConcreteProcessor()
        p.process({"name": "test"})
        assert p.stats["processed"] == 1
