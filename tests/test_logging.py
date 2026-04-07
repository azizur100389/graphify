"""Tests for graphify.log — centralized logging configuration."""
from __future__ import annotations
import logging

import pytest

from graphify.log import logger, set_level, set_verbosity, _GraphifyFormatter


class TestGraphifyFormatter:
    """Test the custom log formatter."""

    def test_info_format_has_prefix(self):
        record = logging.LogRecord(
            name="graphify", level=logging.INFO, pathname="", lineno=0,
            msg="hello world", args=(), exc_info=None,
        )
        fmt = _GraphifyFormatter()
        assert fmt.format(record) == "[graphify] hello world"

    def test_warning_format_includes_level(self):
        record = logging.LogRecord(
            name="graphify", level=logging.WARNING, pathname="", lineno=0,
            msg="something odd", args=(), exc_info=None,
        )
        fmt = _GraphifyFormatter()
        result = fmt.format(record)
        assert "[graphify] WARNING:" in result
        assert "something odd" in result

    def test_error_format_includes_level(self):
        record = logging.LogRecord(
            name="graphify", level=logging.ERROR, pathname="", lineno=0,
            msg="failure", args=(), exc_info=None,
        )
        fmt = _GraphifyFormatter()
        result = fmt.format(record)
        assert "[graphify] ERROR:" in result
        assert "failure" in result

    def test_debug_format_includes_level(self):
        record = logging.LogRecord(
            name="graphify", level=logging.DEBUG, pathname="", lineno=0,
            msg="trace info", args=(), exc_info=None,
        )
        fmt = _GraphifyFormatter()
        result = fmt.format(record)
        assert "[graphify] DEBUG:" in result
        assert "trace info" in result


class TestLoggerSetup:
    """Test the logger is correctly configured."""

    def test_logger_name(self):
        assert logger.name == "graphify"

    def test_logger_has_handler(self):
        assert len(logger.handlers) >= 1

    def test_default_level_is_info(self):
        set_verbosity()  # reset to default
        assert logger.level == logging.INFO


class TestSetLevel:
    """Test set_level() and set_verbosity()."""

    def test_set_level_debug(self):
        set_level(logging.DEBUG)
        assert logger.level == logging.DEBUG
        set_level(logging.INFO)  # restore

    def test_set_level_warning(self):
        set_level(logging.WARNING)
        assert logger.level == logging.WARNING
        set_level(logging.INFO)  # restore

    def test_set_verbosity_verbose(self):
        set_verbosity(verbose=True)
        assert logger.level == logging.DEBUG
        set_verbosity()  # restore

    def test_set_verbosity_quiet(self):
        set_verbosity(quiet=True)
        assert logger.level == logging.WARNING
        set_verbosity()  # restore

    def test_set_verbosity_verbose_overrides_quiet(self):
        set_verbosity(verbose=True, quiet=True)
        assert logger.level == logging.DEBUG
        set_verbosity()  # restore

    def test_set_verbosity_default(self):
        set_verbosity()
        assert logger.level == logging.INFO


class TestLoggerOutput:
    """Test that logger actually produces output."""

    def test_info_message_captured(self, caplog):
        with caplog.at_level(logging.INFO, logger="graphify"):
            logger.info("test info message")
        assert "test info message" in caplog.text

    def test_warning_message_captured(self, caplog):
        with caplog.at_level(logging.WARNING, logger="graphify"):
            logger.warning("test warning")
        assert "test warning" in caplog.text

    def test_debug_hidden_at_info_level(self, caplog):
        set_verbosity()  # INFO level
        with caplog.at_level(logging.INFO, logger="graphify"):
            logger.debug("hidden debug")
        assert "hidden debug" not in caplog.text

    def test_debug_shown_at_debug_level(self, caplog):
        with caplog.at_level(logging.DEBUG, logger="graphify"):
            logger.debug("visible debug")
        assert "visible debug" in caplog.text
        set_verbosity()  # restore

    def test_format_string_args(self, caplog):
        with caplog.at_level(logging.INFO, logger="graphify"):
            logger.info("node count: %d, edge count: %d", 42, 15)
        assert "node count: 42" in caplog.text
        assert "edge count: 15" in caplog.text
