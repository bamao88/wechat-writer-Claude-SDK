"""Web search tool using Tavily API.

This module provides WebSearchTool for searching public web content
to gather real-time information, industry data, and external cases.

Uses Tavily API (https://tavily.com) for high-quality search results.
"""
import os
import requests
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from src.config.settings import Config
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Result truncation limit (chars)
MAX_RESULT_LENGTH = 500

# Tavily API endpoint
TAVILY_API_URL = "https://api.tavily.com/search"


@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    content: str
    error: Optional[str]


def _format_search_results(results: List[Dict[str, Any]], max_length: int = MAX_RESULT_LENGTH) -> str:
    """Format Tavily search results into compact text.

    Args:
        results: List of search result dicts from Tavily API
        max_length: Maximum total length in characters

    Returns:
        Formatted string with title, content, and URL for each result
    """
    if not results:
        return "未找到相关搜索结果。"

    formatted_parts = []
    total_length = 0

    for i, result in enumerate(results, 1):
        title = result.get('title', '无标题')
        content = result.get('content', '')
        url = result.get('url', '')

        # Format single result
        result_text = f"{i}. {title}\n{content}\n来源: {url}\n"

        # Check if adding this result would exceed max_length
        if total_length + len(result_text) > max_length:
            # Truncate this result to fit
            remaining = max_length - total_length
            if remaining > 50:  # Only add if there's meaningful space
                result_text = result_text[:remaining] + "...\n"
                formatted_parts.append(result_text)
            break

        formatted_parts.append(result_text)
        total_length += len(result_text)

    return "\n".join(formatted_parts)


def search_web_tavily(query: str, api_key: str, max_results: int = 3) -> ToolResult:
    """Search the web using Tavily API.

    Args:
        query: Search query string
        api_key: Tavily API key
        max_results: Maximum number of results to return (default 3)

    Returns:
        ToolResult with search results or error
    """
    if not api_key:
        return ToolResult(
            success=False,
            content="",
            error="Tavily API key未配置。请在.env中设置TAVILY_API_KEY。"
        )

    if not query or not query.strip():
        return ToolResult(
            success=False,
            content="",
            error="搜索查询不能为空。"
        )

    try:
        # Prepare Tavily API request
        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": "basic",  # "basic" or "advanced"
            "max_results": max_results,
            "include_answer": False,  # We format results ourselves
            "include_raw_content": False,  # Don't need full HTML
        }

        # Make API request
        response = requests.post(
            TAVILY_API_URL,
            json=payload,
            timeout=30
        )

        # Check response status
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])

            # Format results with truncation
            formatted_content = _format_search_results(results, max_length=MAX_RESULT_LENGTH)

            logger.info(f"Web search successful: {len(results)} results for query '{query[:50]}...'")

            return ToolResult(
                success=True,
                content=formatted_content,
                error=None
            )

        else:
            # API error
            error_msg = f"Tavily API错误 (状态码: {response.status_code})"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_msg += f": {error_data['error']}"
            except:
                pass

            logger.error(f"Web search failed: {error_msg}")

            return ToolResult(
                success=False,
                content="",
                error=error_msg
            )

    except requests.Timeout:
        error_msg = "Web搜索超时（30秒）"
        logger.error(error_msg)
        return ToolResult(
            success=False,
            content="",
            error=error_msg
        )

    except requests.RequestException as e:
        error_msg = f"Web搜索网络错误: {str(e)}"
        logger.error(error_msg)
        return ToolResult(
            success=False,
            content="",
            error=error_msg
        )

    except Exception as e:
        error_msg = f"Web搜索未知错误: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return ToolResult(
            success=False,
            content="",
            error=error_msg
        )


class WebSearchTool:
    """Web search tool for Claude SDK integration.

    Uses Tavily API for high-quality, real-time web search results.
    Results are formatted and truncated to ≤500 chars.
    """

    def __init__(self, config: Config, api_key: Optional[str] = None):
        """Initialize WebSearchTool.

        Args:
            config: Application configuration
            api_key: Optional Tavily API key (for testing). If not provided, reads from env.
        """
        self.config = config
        self.name = "search_web"
        self.description = (
            "搜索全网实时热点、行业数据与外部案例。"
            "用于获取最新信息、权威报告、产品评测等公开内容。"
            "返回结果包含标题、摘要和来源URL。"
        )

        # Get Tavily API key: prioritize parameter > config attribute > environment
        if api_key:
            self.api_key = api_key
        elif hasattr(config, 'tavily_api_key') and config.tavily_api_key:
            self.api_key = config.tavily_api_key
        else:
            self.api_key = os.getenv("TAVILY_API_KEY") or os.getenv("WECHAT_WRITER_TAVILY_API_KEY")

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Input schema for the tool (JSON Schema format)."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询，用于在全网查找相关信息、数据和案例"
                }
            },
            "required": ["query"]
        }

    def execute(self, query: str) -> ToolResult:
        """Execute web search.

        Args:
            query: Search query string

        Returns:
            ToolResult with search results (≤500 chars) or error
        """
        return search_web_tavily(query, self.api_key)

    def to_claude_tool(self) -> Dict[str, Any]:
        """Convert to Claude tool definition format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema
        }
