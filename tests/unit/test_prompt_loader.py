"""Tests for prompt loader utility."""
import pytest
import tempfile
from pathlib import Path

from src.utils.prompt_loader import load_prompt, PromptError


class TestLoadPrompt:
    """Test prompt loading functionality."""

    def test_load_existing_prompt(self):
        """Can load prompt_run.txt from default location."""
        content = load_prompt("prompt_run.txt")
        assert len(content) > 0
        assert "写作" in content or "Agent" in content

    def test_load_from_custom_dir(self, tmp_path):
        """Can load from custom prompts directory."""
        prompt_file = tmp_path / "test.txt"
        prompt_file.write_text("测试prompt内容", encoding="utf-8")

        content = load_prompt("test.txt", prompts_dir=str(tmp_path))
        assert content == "测试prompt内容"

    def test_missing_prompt_raises_error(self, tmp_path):
        """Missing prompt file raises PromptError."""
        with pytest.raises(PromptError) as exc_info:
            load_prompt("不存在.txt", prompts_dir=str(tmp_path))
        assert "不存在" in str(exc_info.value)

    def test_prompt_content_is_utf8(self):
        """Prompt content preserves Chinese characters."""
        content = load_prompt("prompt_run.txt")
        # The production prompt contains Chinese
        assert any(ord(c) > 127 for c in content)
