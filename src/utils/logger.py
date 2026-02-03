"""Logging utilities for the application."""
import logging
import sys
from typing import Optional

# Module-level logger instance
_root_logger: Optional[logging.Logger] = None


def setup_logger(level: str = "INFO") -> logging.Logger:
    """Setup and configure the root application logger.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR).
               Defaults to INFO if invalid.

    Returns:
        Configured Logger instance.
    """
    global _root_logger

    # Get numeric level, default to INFO if invalid
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO

    # Create or get the root logger for our app
    logger = logging.getLogger("writing_assistant")
    logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console handler with simple format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    # Simple format: [LEVEL] message
    formatter = logging.Formatter("[%(levelname)s] %(message)s")
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    _root_logger = logger
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a named child logger.

    Args:
        name: Name for the logger (typically module name).

    Returns:
        Logger instance that inherits root configuration.
    """
    return logging.getLogger(name)
