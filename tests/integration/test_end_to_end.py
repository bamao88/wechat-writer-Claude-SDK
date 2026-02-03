"""Integration tests for end-to-end workflow.

These tests verify the complete flow from CLI to agent.
Some tests require real API keys and network access.
"""
import subprocess
import sys
import pytest
from unittest.mock import patch, Mock

from src.cli import parse_args
from src.config import load_config
from src.agent import create_agent, run_agent


class TestCLIToConfig:
    """Test CLI parsing flows into config loading."""

    def test_cli_and_config_work_together(self):
        """CLI result can be used with loaded config."""
        cli_result = parse_args(["py", "main.py", "测试选题"])
        config = load_config()  # Uses .env

        assert cli_result.topic == "测试选题"
        assert config.notebook_id is not None


class TestAgentCreation:
    """Test agent can be created with config."""

    def test_agent_creates_with_config(self):
        """Agent can be instantiated with loaded config."""
        config = load_config()
        agent = create_agent(config)

        assert agent is not None
        assert agent.tool.name == "search_notebooklm"

    def test_agent_has_claude_client(self):
        """Agent has Claude client configured."""
        config = load_config()
        agent = create_agent(config)

        assert agent.client is not None


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


# Mark real API tests to skip by default
@pytest.mark.skipif(
    "SKIP_REAL_API" in __import__("os").environ,
    reason="Skipping real API tests"
)
class TestRealAPI:
    """Tests that require real API access.

    Run with: pytest tests/integration/ -v
    Skip with: SKIP_REAL_API=1 pytest tests/integration/ -v
    """

    def test_agent_can_call_tool(self):
        """Agent can make real tool call (requires nlm CLI)."""
        config = load_config()

        # This test requires nlm CLI to be installed and authenticated
        # It will fail gracefully if not available
        progress_messages = []

        def capture_progress(msg):
            progress_messages.append(msg)

        result = run_agent(
            topic="测试选题",
            config=config,
            on_progress=capture_progress
        )

        # Even if tool fails, agent should handle gracefully
        assert result is not None
        assert isinstance(result.tool_calls, int)
