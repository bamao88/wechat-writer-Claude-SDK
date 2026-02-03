"""Tests for CLI argument parsing."""
import pytest
from src.cli.parser import parse_args, CLIError


class TestParseArgs:
    """Test parse_args function."""

    def test_accepts_topic_positional_arg(self):
        """parse_args accepts topic as positional argument."""
        result = parse_args(["python", "main.py", "AI产品经理职业发展"])
        assert result.topic == "AI产品经理职业发展"

    def test_accepts_topic_with_spaces(self):
        """parse_args accepts topic containing spaces."""
        result = parse_args(["python", "main.py", "如何成为 AI 产品经理"])
        assert result.topic == "如何成为 AI 产品经理"

    def test_accepts_english_topic(self):
        """parse_args accepts English topics."""
        result = parse_args(["python", "main.py", "How to become a PM"])
        assert result.topic == "How to become a PM"

    def test_rejects_empty_topic(self):
        """parse_args raises CLIError for empty string topic."""
        with pytest.raises(CLIError) as exc_info:
            parse_args(["python", "main.py", ""])
        assert "选题" in str(exc_info.value)  # Chinese error message

    def test_rejects_whitespace_only_topic(self):
        """parse_args raises CLIError for whitespace-only topic."""
        with pytest.raises(CLIError) as exc_info:
            parse_args(["python", "main.py", "   "])
        assert "选题" in str(exc_info.value)

    def test_rejects_missing_topic(self):
        """parse_args raises CLIError when no topic provided."""
        with pytest.raises(CLIError) as exc_info:
            parse_args(["python", "main.py"])
        assert "选题" in str(exc_info.value) or "必需" in str(exc_info.value)

    def test_strips_whitespace_from_topic(self):
        """parse_args strips leading/trailing whitespace from topic."""
        result = parse_args(["python", "main.py", "  AI写作  "])
        assert result.topic == "AI写作"


class TestCLIHelp:
    """Test CLI help functionality."""

    def test_help_flag_short(self):
        """CLI supports -h for help."""
        # -h should raise SystemExit with code 0
        with pytest.raises(SystemExit) as exc_info:
            parse_args(["python", "main.py", "-h"])
        assert exc_info.value.code == 0

    def test_help_flag_long(self):
        """CLI supports --help for help."""
        with pytest.raises(SystemExit) as exc_info:
            parse_args(["python", "main.py", "--help"])
        assert exc_info.value.code == 0


class TestCLIResult:
    """Test CLIResult structure."""

    def test_result_has_topic_attribute(self):
        """Result object has topic attribute."""
        result = parse_args(["python", "main.py", "测试选题"])
        assert hasattr(result, "topic")
        assert isinstance(result.topic, str)
