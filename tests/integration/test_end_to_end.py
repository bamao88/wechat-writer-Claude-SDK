"""Integration tests for end-to-end workflow.

These tests verify the complete flow from CLI to config.
Some tests require real API keys and network access.
"""
import subprocess
import sys
import pytest

from src.cli import parse_args
from src.config import load_config


class TestCLIToConfig:
    """Test CLI parsing flows into config loading."""

    def test_cli_and_config_work_together(self):
        """CLI result can be used with loaded config."""
        cli_result = parse_args(["py", "main.py", "测试选题"])
        config = load_config()  # Uses .env

        assert cli_result.topic == "测试选题"
        assert config.notebook_id is not None


class TestMainScript:
    """Test main.py script execution."""

    def test_help_flag_works(self):
        """main.py -h shows help and exits 0."""
        result = subprocess.run(
            [sys.executable, "main.py", "-h"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "选题" in result.stdout or "usage" in result.stdout.lower()

    def test_empty_topic_fails(self):
        """main.py with empty topic fails gracefully."""
        result = subprocess.run(
            [sys.executable, "main.py", ""],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1
        assert "错误" in result.stderr or "error" in result.stderr.lower()
