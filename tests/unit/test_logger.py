"""Tests for logging utilities."""
import logging
import pytest
from src.utils.logger import setup_logger, get_logger


class TestSetupLogger:
    """Test setup_logger function."""

    def test_returns_logger_instance(self):
        """setup_logger returns a Logger instance."""
        logger = setup_logger("INFO")
        assert isinstance(logger, logging.Logger)

    def test_sets_correct_level_info(self):
        """Logger level is set to INFO when specified."""
        logger = setup_logger("INFO")
        assert logger.level == logging.INFO

    def test_sets_correct_level_debug(self):
        """Logger level is set to DEBUG when specified."""
        logger = setup_logger("DEBUG")
        assert logger.level == logging.DEBUG

    def test_sets_correct_level_warning(self):
        """Logger level is set to WARNING when specified."""
        logger = setup_logger("WARNING")
        assert logger.level == logging.WARNING

    def test_has_console_handler(self):
        """Logger has a StreamHandler for console output."""
        logger = setup_logger("INFO")
        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "StreamHandler" in handler_types

    def test_invalid_level_defaults_to_info(self):
        """Invalid log level defaults to INFO."""
        logger = setup_logger("INVALID")
        assert logger.level == logging.INFO


class TestGetLogger:
    """Test get_logger function."""

    def test_returns_named_logger(self):
        """get_logger returns logger with specified name."""
        logger = get_logger("test_module")
        assert logger.name == "test_module"

    def test_child_logger_inherits_config(self):
        """Child logger inherits from root configuration."""
        # Setup root logger first
        setup_logger("DEBUG")
        child = get_logger("child_module")
        assert isinstance(child, logging.Logger)
