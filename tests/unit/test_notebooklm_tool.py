"""Tests for NotebookLM tool wrapper."""
import subprocess
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.tools.notebooklm import (
    search_notebook,
    NotebookLMTool,
    ToolError,
    ToolResult
)
from src.config.settings import Config


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    return Config(
        notebook_id="test-notebook-123",
        notebook_url="https://notebooklm.google.com/notebook/test",
        retry_count=3,
        retry_delay_sec=0,  # No delay in tests
        timeout_sec=30,
        log_level="INFO"
    )


class TestSearchNotebook:
    """Test search_notebook function."""

    @patch("src.tools.notebooklm.subprocess.run")
    def test_returns_results_on_success(self, mock_run, mock_config):
        """search_notebook returns results when CLI succeeds."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="搜索结果：找到3篇相关文章...",
            stderr=""
        )

        result = search_notebook("AI产品经理", mock_config)

        assert result.success is True
        assert "搜索结果" in result.content
        assert result.error is None

    @patch("src.tools.notebooklm.subprocess.run")
    def test_calls_nlm_cli_with_correct_args(self, mock_run, mock_config):
        """search_notebook invokes nlm CLI with correct arguments."""
        mock_run.return_value = Mock(returncode=0, stdout="ok", stderr="")

        search_notebook("测试查询", mock_config)

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        cmd = call_args[0][0]  # First positional arg is the command list

        assert "nlm" in cmd[0] or "notebooklm" in cmd[0].lower()
        assert "notebook" in cmd
        assert "query" in cmd
        assert mock_config.notebook_id in cmd
        assert "测试查询" in cmd

    @patch("src.tools.notebooklm.subprocess.run")
    def test_retries_on_failure(self, mock_run, mock_config):
        """search_notebook retries configured number of times on failure."""
        # Fail twice, succeed on third
        mock_run.side_effect = [
            Mock(returncode=1, stdout="", stderr="Network error"),
            Mock(returncode=1, stdout="", stderr="Timeout"),
            Mock(returncode=0, stdout="成功", stderr="")
        ]

        result = search_notebook("测试", mock_config)

        assert result.success is True
        assert mock_run.call_count == 3

    @patch("src.tools.notebooklm.subprocess.run")
    def test_returns_error_after_all_retries_fail(self, mock_run, mock_config):
        """search_notebook returns error after exhausting retries."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Connection refused"
        )

        result = search_notebook("测试", mock_config)

        assert result.success is False
        assert result.error is not None
        assert "已重试" in result.error or "3" in result.error
        assert mock_run.call_count == mock_config.retry_count

    @patch("src.tools.notebooklm.subprocess.run")
    def test_respects_timeout(self, mock_run, mock_config):
        """search_notebook passes timeout to subprocess."""
        mock_run.return_value = Mock(returncode=0, stdout="ok", stderr="")

        search_notebook("测试", mock_config)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs.get("timeout") == mock_config.timeout_sec

    @patch("src.tools.notebooklm.subprocess.run")
    def test_handles_timeout_exception(self, mock_run, mock_config):
        """search_notebook handles subprocess timeout gracefully."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="nlm", timeout=30)

        result = search_notebook("测试", mock_config)

        assert result.success is False
        assert "超时" in result.error or "timeout" in result.error.lower()


class TestNotebookLMTool:
    """Test NotebookLMTool class for Claude integration."""

    def test_has_required_attributes(self, mock_config):
        """Tool has name, description for Claude SDK."""
        tool = NotebookLMTool(mock_config)

        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
        assert tool.name == "search_notebooklm"
        assert "NotebookLM" in tool.description or "搜索" in tool.description

    def test_has_input_schema(self, mock_config):
        """Tool defines input schema for Claude."""
        tool = NotebookLMTool(mock_config)

        assert hasattr(tool, "input_schema")
        schema = tool.input_schema
        assert "query" in str(schema) or "问题" in str(schema)

    @patch("src.tools.notebooklm.search_notebook")
    def test_execute_calls_search(self, mock_search, mock_config):
        """Tool execute method calls search_notebook."""
        mock_search.return_value = ToolResult(
            success=True,
            content="结果",
            error=None
        )
        tool = NotebookLMTool(mock_config)

        result = tool.execute(query="测试问题")

        mock_search.assert_called_once_with("测试问题", mock_config)


class TestToolResult:
    """Test ToolResult dataclass."""

    def test_success_result(self):
        """ToolResult correctly represents success."""
        result = ToolResult(success=True, content="内容", error=None)
        assert result.success is True
        assert result.content == "内容"
        assert result.error is None

    def test_failure_result(self):
        """ToolResult correctly represents failure."""
        result = ToolResult(success=False, content="", error="错误信息")
        assert result.success is False
        assert result.error == "错误信息"
