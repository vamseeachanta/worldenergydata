"""
Tests for worldenergydata.common.logging module.

Tests cover:
- get_logger() returns proper logger
- configure_logging() sets correct levels
- Structured output format works
- Log level from environment variable
"""

import json
import logging
import os
from io import StringIO
from unittest.mock import patch

import pytest


class TestStructuredFormatter:
    """Tests for StructuredFormatter class."""

    def test_format_text_basic_message(self):
        """Test text formatting with basic message."""
        from worldenergydata.common.logging import StructuredFormatter

        formatter = StructuredFormatter(json_output=False)
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        assert "INFO" in output
        assert "test.logger" in output
        assert "Test message" in output
        assert "42" in output

    def test_format_text_with_extras(self):
        """Test text formatting includes extra fields."""
        from worldenergydata.common.logging import StructuredFormatter

        formatter = StructuredFormatter(json_output=False)
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.record_count = 1000
        record.source = "BSEE"

        output = formatter.format(record)

        assert "record_count=1000" in output
        assert "source=BSEE" in output

    def test_format_json_basic_message(self):
        """Test JSON formatting with basic message."""
        from worldenergydata.common.logging import StructuredFormatter

        formatter = StructuredFormatter(json_output=True)
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert data["message"] == "Test message"
        assert data["line"] == 42
        assert "timestamp" in data

    def test_format_json_with_extras(self):
        """Test JSON formatting includes extra fields in context."""
        from worldenergydata.common.logging import StructuredFormatter

        formatter = StructuredFormatter(json_output=True)
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.record_count = 1000
        record.source = "BSEE"

        output = formatter.format(record)
        data = json.loads(output)

        assert "context" in data
        assert data["context"]["record_count"] == 1000
        assert data["context"]["source"] == "BSEE"

    def test_format_json_with_exception(self):
        """Test JSON formatting includes exception info."""
        from worldenergydata.common.logging import StructuredFormatter

        formatter = StructuredFormatter(json_output=True)

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert "exception" in data
        assert "ValueError" in data["exception"]

    def test_format_text_with_exception(self):
        """Test text formatting includes exception info."""
        from worldenergydata.common.logging import StructuredFormatter

        formatter = StructuredFormatter(json_output=False)

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        output = formatter.format(record)

        assert "ValueError" in output
        assert "Test error" in output


class TestLoggerAdapter:
    """Tests for LoggerAdapter class."""

    def test_adapter_merges_context(self):
        """Test adapter merges persistent context with call context."""
        from worldenergydata.common.logging import LoggerAdapter

        base_logger = logging.getLogger("test.adapter")
        adapter = LoggerAdapter(base_logger, {"module": "bsee"})

        msg, kwargs = adapter.process("Test", {"extra": {"source": "api"}})

        assert kwargs["extra"]["module"] == "bsee"
        assert kwargs["extra"]["source"] == "api"

    def test_adapter_without_extra(self):
        """Test adapter works when no extra provided in call."""
        from worldenergydata.common.logging import LoggerAdapter

        base_logger = logging.getLogger("test.adapter2")
        adapter = LoggerAdapter(base_logger, {"module": "sodir"})

        msg, kwargs = adapter.process("Test", {})

        assert kwargs["extra"]["module"] == "sodir"

    def test_adapter_empty_context(self):
        """Test adapter works with empty context."""
        from worldenergydata.common.logging import LoggerAdapter

        base_logger = logging.getLogger("test.adapter3")
        adapter = LoggerAdapter(base_logger, {})

        msg, kwargs = adapter.process("Test", {"extra": {"key": "value"}})

        assert kwargs["extra"]["key"] == "value"


class TestConfigureLogging:
    """Tests for configure_logging() function."""

    def setup_method(self):
        """Reset logging configuration before each test."""
        from worldenergydata.common import logging as wed_logging
        wed_logging._log_config["configured"] = False
        wed_logging._log_config["level"] = None
        wed_logging._log_config["json_output"] = False

    def test_configure_logging_default_level(self):
        """Test default log level is INFO."""
        from worldenergydata.common.logging import configure_logging, _log_config

        with patch.dict(os.environ, {}, clear=True):
            configure_logging()

        assert _log_config["level"] == logging.INFO
        assert _log_config["configured"] is True

    def test_configure_logging_explicit_level(self):
        """Test explicit log level setting."""
        from worldenergydata.common.logging import configure_logging, _log_config

        configure_logging(level="DEBUG")

        assert _log_config["level"] == logging.DEBUG

    def test_configure_logging_from_environment(self):
        """Test log level from environment variable."""
        from worldenergydata.common.logging import configure_logging, _log_config

        with patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}):
            configure_logging()

        assert _log_config["level"] == logging.WARNING

    def test_configure_logging_json_output_explicit(self):
        """Test JSON output can be enabled explicitly."""
        from worldenergydata.common.logging import configure_logging, _log_config

        configure_logging(json_output=True)

        assert _log_config["json_output"] is True

    def test_configure_logging_json_from_environment(self):
        """Test JSON output from environment variable."""
        from worldenergydata.common.logging import configure_logging, _log_config

        with patch.dict(os.environ, {"LOG_JSON": "true"}):
            configure_logging()

        assert _log_config["json_output"] is True

    def test_configure_logging_json_env_values(self):
        """Test various environment values for LOG_JSON."""
        from worldenergydata.common.logging import configure_logging, _log_config

        for value in ["true", "1", "yes"]:
            _log_config["configured"] = False
            with patch.dict(os.environ, {"LOG_JSON": value}):
                configure_logging()
            assert _log_config["json_output"] is True

    def test_configure_logging_custom_handlers(self):
        """Test custom handlers are used when provided."""
        from worldenergydata.common.logging import configure_logging

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.INFO)

        configure_logging(level="INFO", handlers=[handler])

        root_logger = logging.getLogger("worldenergydata")
        assert handler in root_logger.handlers

    def test_configure_logging_clears_existing_handlers(self):
        """Test existing handlers are cleared on reconfiguration."""
        from worldenergydata.common.logging import configure_logging

        configure_logging(level="INFO")
        root_logger = logging.getLogger("worldenergydata")
        initial_handlers = len(root_logger.handlers)

        configure_logging(level="DEBUG")
        assert len(root_logger.handlers) == initial_handlers


class TestGetLogger:
    """Tests for get_logger() function."""

    def setup_method(self):
        """Reset logging configuration before each test."""
        from worldenergydata.common import logging as wed_logging
        wed_logging._log_config["configured"] = False

    def test_get_logger_returns_adapter(self):
        """Test get_logger returns LoggerAdapter instance."""
        from worldenergydata.common.logging import get_logger, LoggerAdapter

        logger = get_logger("test.module")

        assert isinstance(logger, LoggerAdapter)

    def test_get_logger_with_context(self):
        """Test get_logger includes provided context."""
        from worldenergydata.common.logging import get_logger

        logger = get_logger("test.module", context={"module": "bsee"})

        assert logger.extra["module"] == "bsee"

    def test_get_logger_auto_configures(self):
        """Test get_logger automatically configures logging if needed."""
        from worldenergydata.common.logging import get_logger, _log_config

        _log_config["configured"] = False
        _ = get_logger("test.module")

        assert _log_config["configured"] is True

    def test_get_logger_uses_correct_name(self):
        """Test logger uses the provided name."""
        from worldenergydata.common.logging import get_logger

        logger = get_logger("worldenergydata.modules.bsee")

        assert logger.logger.name == "worldenergydata.modules.bsee"


class TestGetModuleLogger:
    """Tests for get_module_logger() function."""

    def test_get_module_logger_naming(self):
        """Test module logger has correct naming convention."""
        from worldenergydata.common.logging import get_module_logger

        logger = get_module_logger("bsee")

        assert logger.logger.name == "worldenergydata.modules.bsee"

    def test_get_module_logger_with_component(self):
        """Test module logger with component has correct naming."""
        from worldenergydata.common.logging import get_module_logger

        logger = get_module_logger("bsee", "data")

        assert logger.logger.name == "worldenergydata.modules.bsee.data"

    def test_get_module_logger_context(self):
        """Test module logger has module context set."""
        from worldenergydata.common.logging import get_module_logger

        logger = get_module_logger("sodir", "analysis")

        assert logger.extra["module"] == "sodir"
        assert logger.extra["component"] == "analysis"


class TestLoggingIntegration:
    """Integration tests for logging functionality."""

    def test_log_message_captured(self):
        """Test log messages are captured with correct format."""
        from worldenergydata.common.logging import (
            configure_logging,
            get_logger,
            StructuredFormatter,
        )

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(StructuredFormatter(json_output=False))

        configure_logging(level="DEBUG", json_output=False, handlers=[handler])
        # Use worldenergydata namespace so messages propagate through configured handlers
        logger = get_logger("worldenergydata.test.integration")

        logger.info("Test message", extra={"key": "value"})

        output = stream.getvalue()
        assert "INFO" in output
        assert "Test message" in output
        assert "key=value" in output

    def test_json_log_output(self):
        """Test JSON log output is valid JSON."""
        from worldenergydata.common.logging import (
            configure_logging,
            get_logger,
            StructuredFormatter,
        )

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(StructuredFormatter(json_output=True))

        configure_logging(level="DEBUG", handlers=[handler])
        # Use worldenergydata namespace so messages propagate through configured handlers
        logger = get_logger("worldenergydata.test.json")

        logger.warning("JSON test", extra={"count": 42})

        output = stream.getvalue()
        data = json.loads(output.strip())

        assert data["level"] == "WARNING"
        assert data["message"] == "JSON test"
        assert data["context"]["count"] == 42
