"""Tests for WebSearchTool (Tavily API integration)."""
import pytest
from unittest.mock import Mock, patch
from src.tools.web_search import WebSearchTool, ToolResult
from src.config.settings import Config


class TestToolResult:
    """Test ToolResult dataclass."""

    def test_tool_result_success(self):
        """ToolResult with success=True."""
        result = ToolResult(success=True, content="搜索结果", error=None)
        assert result.success is True
        assert result.content == "搜索结果"
        assert result.error is None

    def test_tool_result_failure(self):
        """ToolResult with success=False."""
        result = ToolResult(success=False, content="", error="API错误")
        assert result.success is False
        assert result.content == ""
        assert result.error == "API错误"


class TestWebSearchToolSchema:
    """Test WebSearchTool interface definition."""

    def test_tool_has_required_attributes(self):
        """WebSearchTool has name, description, input_schema."""
        tool = WebSearchTool(Mock())

        assert hasattr(tool, 'name')
        assert hasattr(tool, 'description')
        assert hasattr(tool, 'input_schema')

        assert tool.name == "search_web"
        assert isinstance(tool.description, str)
        assert isinstance(tool.input_schema, dict)

    def test_input_schema_format(self):
        """input_schema follows JSON Schema format."""
        tool = WebSearchTool(Mock())
        schema = tool.input_schema

        assert schema['type'] == 'object'
        assert 'properties' in schema
        assert 'query' in schema['properties']
        assert 'required' in schema
        assert 'query' in schema['required']


class TestWebSearchExecution:
    """Test WebSearchTool execution with mocked HTTP."""

    @patch('src.tools.web_search.requests.post')
    def test_search_success(self, mock_post):
        """Successful Tavily API call returns results."""
        # Mock Tavily API response
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                'results': [
                    {
                        'title': 'AI行业报告',
                        'content': '2026年AI行业发展迅速...',
                        'url': 'https://example.com/1'
                    },
                    {
                        'title': '产品经理技能',
                        'content': 'AI产品经理需要技术理解能力...',
                        'url': 'https://example.com/2'
                    }
                ]
            }
        )

        config = Mock()
        tool = WebSearchTool(config, api_key="test_key")

        result = tool.execute("AI产品经理")

        assert result.success is True
        assert len(result.content) > 0
        assert "AI行业报告" in result.content or "产品经理" in result.content

    @patch('src.tools.web_search.requests.post')
    def test_search_api_error(self, mock_post):
        """API error returns ToolResult with error."""
        mock_post.return_value = Mock(
            status_code=401,
            json=lambda: {'error': 'Invalid API key'}
        )

        config = Mock()
        config.tavily_api_key = "invalid_key"
        tool = WebSearchTool(config, api_key="test_key")

        result = tool.execute("test query")

        assert result.success is False
        assert result.error is not None
        assert "API" in result.error or "401" in result.error

    @patch('src.tools.web_search.requests.post')
    def test_search_timeout(self, mock_post):
        """Timeout returns error."""
        import requests
        mock_post.side_effect = requests.Timeout("Request timeout")

        config = Mock()
        # Mock config
        tool = WebSearchTool(config, api_key="test_key")

        result = tool.execute("test query")

        assert result.success is False
        assert "timeout" in result.error.lower() or "超时" in result.error

    @patch('src.tools.web_search.requests.post')
    def test_search_network_error(self, mock_post):
        """Network error returns error."""
        import requests
        mock_post.side_effect = requests.RequestException("Network error")

        config = Mock()
        # Mock config
        tool = WebSearchTool(config, api_key="test_key")

        result = tool.execute("test query")

        assert result.success is False
        assert result.error is not None


class TestWebSearchResultFormatting:
    """Test result formatting and truncation."""

    @patch('src.tools.web_search.requests.post')
    def test_result_truncation_500_chars(self, mock_post):
        """Results are truncated to ≤500 chars."""
        # Mock long content
        long_content = "详细内容" * 200  # Much longer than 500 chars

        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                'results': [
                    {
                        'title': '标题',
                        'content': long_content,
                        'url': 'https://example.com'
                    }
                ]
            }
        )

        config = Mock()
        # Mock config
        tool = WebSearchTool(config, api_key="test_key")

        result = tool.execute("test")

        assert result.success is True
        # Should be truncated to around 500 chars
        assert len(result.content) <= 550  # Allow some margin for formatting

    @patch('src.tools.web_search.requests.post')
    def test_result_format_includes_title_and_url(self, mock_post):
        """Formatted result includes title, content, and URL."""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                'results': [
                    {
                        'title': 'Test Title',
                        'content': 'Test content here',
                        'url': 'https://example.com/article'
                    }
                ]
            }
        )

        config = Mock()
        # Mock config
        tool = WebSearchTool(config, api_key="test_key")

        result = tool.execute("test")

        assert result.success is True
        assert "Test Title" in result.content
        assert "example.com" in result.content or "https" in result.content

    @patch('src.tools.web_search.requests.post')
    def test_empty_results(self, mock_post):
        """Empty search results handled gracefully."""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'results': []}
        )

        config = Mock()
        # Mock config
        tool = WebSearchTool(config, api_key="test_key")

        result = tool.execute("nonexistent query")

        assert result.success is True
        assert "未找到" in result.content or "没有" in result.content or len(result.content) == 0


class TestWebSearchConfiguration:
    """Test configuration and API key handling."""

    def test_missing_api_key(self):
        """Missing API key returns error."""
        config = Mock()
        config.tavily_api_key = None

        # Don't pass api_key parameter, and mock empty env
        with patch.dict('os.environ', {}, clear=True):
            tool = WebSearchTool(config)
            result = tool.execute("test")

            assert result.success is False
            assert ("API" in result.error or "key" in result.error.lower())

    def test_empty_query(self):
        """Empty query returns error."""
        config = Mock()
        # Mock config

        tool = WebSearchTool(config, api_key="test_key")
        result = tool.execute("")

        assert result.success is False
        assert "query" in result.error.lower() or "查询" in result.error


class TestWebSearchToolIntegration:
    """Test WebSearchTool integration."""

    def test_tool_definition_for_llm_backend(self):
        """Tool definition can be converted to LLM backend format."""
        config = Mock()
        # Mock config
        tool = WebSearchTool(config, api_key="test_key")

        # Should be able to generate tool definition dict
        tool_def = {
            'name': tool.name,
            'description': tool.description,
            'parameters': tool.input_schema
        }

        assert tool_def['name'] == 'search_web'
        assert len(tool_def['description']) > 10
        assert 'properties' in tool_def['parameters']
