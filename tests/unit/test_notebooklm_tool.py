"""Tests for NotebookLM tool wrapper (Skill-based)."""
import subprocess
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.tools.notebooklm import (
    search_notebook,
    NotebookLMTool,
    ToolError,
    ToolResult,
    _parse_answer_from_stdout,
    _skill_python,
)
from src.config.settings import Config


@pytest.fixture
def mock_config(tmp_path):
    """Create a mock configuration; tmp_path has scripts/ask_question.py for script-exists tests."""
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "ask_question.py").touch()
    return Config(
        notebook_id="test-notebook-123",
        notebook_url="https://notebooklm.google.com/notebook/test",
        retry_count=3,
        retry_delay_sec=0,
        timeout_sec=30,
        log_level="INFO",
        notebooklm_skill_dir=str(tmp_path),
        llm_provider="anthropic",
    )


@pytest.fixture
def mock_config_with_venv(tmp_path):
    """Skill dir with scripts/ask_question.py and .venv/bin/python (use Skill's venv)."""
    (tmp_path / "scripts").mkdir(parents=True)
    (tmp_path / "scripts" / "ask_question.py").touch()
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").touch()
    return Config(
        notebook_id="test-notebook-123",
        notebook_url="https://notebooklm.google.com/notebook/test",
        retry_count=3,
        retry_delay_sec=0,
        timeout_sec=30,
        log_level="INFO",
        notebooklm_skill_dir=str(tmp_path),
        llm_provider="anthropic",
    )


@pytest.fixture
def mock_config_no_script(tmp_path):
    """Config with skill dir that has no ask_question.py."""
    return Config(
        notebook_id="test-notebook-123",
        notebook_url="https://notebooklm.google.com/notebook/test",
        retry_count=3,
        retry_delay_sec=0,
        timeout_sec=30,
        log_level="INFO",
        notebooklm_skill_dir=str(tmp_path),
        llm_provider="anthropic",
    )


class TestParseAnswerFromStdout:
    """Test _parse_answer_from_stdout."""

    def test_extracts_middle_block(self):
        sep = "=" * 60
        stdout = f"\n{sep}\nQuestion: q\n{sep}\n\n答案内容\n\n{sep}\n"
        assert _parse_answer_from_stdout(stdout) == "答案内容"

    def test_returns_full_stdout_if_fewer_than_three_seps(self):
        assert _parse_answer_from_stdout("short") == "short"

    def test_returns_empty_for_empty(self):
        assert _parse_answer_from_stdout("") == ""
        assert _parse_answer_from_stdout("   ") == ""


class TestSearchNotebook:
    """Test search_notebook function."""

    @patch("src.tools.notebooklm.subprocess.run")
    def test_returns_results_on_success(self, mock_run, mock_config):
        """search_notebook returns parsed answer when script succeeds."""
        sep = "=" * 60
        mock_run.return_value = Mock(
            returncode=0,
            stdout=f"\n{sep}\nQuestion: x\n{sep}\n\n搜索结果：找到3篇相关文章...\n\n{sep}\n",
            stderr="",
        )
        result = search_notebook("AI产品经理", mock_config)
        assert result.success is True
        assert "搜索结果" in result.content
        assert result.error is None

    @patch("src.tools.notebooklm.subprocess.run")
    def test_calls_skill_script_with_correct_args(self, mock_run, mock_config):
        """search_notebook invokes ask_question.py with --question and --notebook-url."""
        mock_run.return_value = Mock(returncode=0, stdout="=" * 60 + "\n\nok\n\n" + "=" * 60, stderr="")
        search_notebook("测试查询", mock_config)
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "ask_question.py" in cmd[1]
        assert "--question" in cmd
        assert "测试查询" in cmd
        assert "--notebook-url" in cmd
        assert mock_config.notebook_url in cmd
        assert call_args[1].get("cwd") == mock_config.notebooklm_skill_dir

    @patch("src.tools.notebooklm.subprocess.run")
    def test_retries_on_failure(self, mock_run, mock_config):
        """search_notebook retries configured number of times on failure."""
        sep = "=" * 60
        mock_run.side_effect = [
            Mock(returncode=1, stdout="", stderr="Network error"),
            Mock(returncode=1, stdout="", stderr="Timeout"),
            Mock(returncode=0, stdout=f"{sep}\n\n{sep}\n\n成功\n\n{sep}", stderr=""),
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
            stderr="Not authenticated",
        )
        result = search_notebook("测试", mock_config)
        assert result.success is False
        assert result.error is not None
        assert "已重试" in result.error or "3" in result.error
        assert mock_run.call_count == mock_config.retry_count

    @patch("src.tools.notebooklm.subprocess.run")
    def test_respects_timeout(self, mock_run, mock_config):
        """search_notebook passes timeout to subprocess."""
        sep = "=" * 60
        mock_run.return_value = Mock(returncode=0, stdout=f"{sep}\n\n{sep}\n\nok\n\n{sep}", stderr="")
        search_notebook("测试", mock_config)
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs.get("timeout") == mock_config.timeout_sec

    @patch("src.tools.notebooklm.subprocess.run")
    def test_handles_timeout_exception(self, mock_run, mock_config):
        """search_notebook handles subprocess timeout gracefully."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="python", timeout=30)
        result = search_notebook("测试", mock_config)
        assert result.success is False
        assert "超时" in result.error or "timeout" in result.error.lower()

    def test_returns_error_when_script_not_found(self, mock_config_no_script):
        """search_notebook returns error when ask_question.py is missing."""
        result = search_notebook("测试", mock_config_no_script)
        assert result.success is False
        assert "未找到" in result.error or "Skill" in result.error

    @patch("src.tools.notebooklm.subprocess.run")
    def test_uses_skill_venv_python_when_present(self, mock_run, mock_config_with_venv):
        """search_notebook uses Skill's .venv/bin/python when it exists."""
        sep = "=" * 60
        mock_run.return_value = Mock(returncode=0, stdout=f"{sep}\n\nok\n\n{sep}", stderr="")
        search_notebook("测试", mock_config_with_venv)
        cmd = mock_run.call_args[0][0]
        assert ".venv" in cmd[0] and "python" in cmd[0]
        assert "ask_question.py" in cmd[1]


class TestSkillPython:
    """Test _skill_python helper."""

    def test_returns_venv_bin_python_when_present(self, tmp_path):
        (tmp_path / ".venv" / "bin").mkdir(parents=True)
        (tmp_path / ".venv" / "bin" / "python").touch()
        assert ".venv" in _skill_python(tmp_path)
        assert _skill_python(tmp_path).endswith("python")

    def test_falls_back_to_sys_executable_without_venv(self, tmp_path):
        import sys
        result = _skill_python(tmp_path)
        assert result == sys.executable


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
            error=None,
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
