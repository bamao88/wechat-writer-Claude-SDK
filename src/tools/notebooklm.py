"""NotebookLM tool wrapper for Claude SDK integration."""
import subprocess
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any

from src.config.settings import Config


class ToolError(Exception):
    """Raised when tool execution fails unrecoverably."""
    pass


@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    content: str
    error: Optional[str]


def search_notebook(query: str, config: Config) -> ToolResult:
    """Search NotebookLM using the nlm CLI tool.

    Args:
        query: Search query string.
        config: Application configuration with notebook settings.

    Returns:
        ToolResult with search results or error message.
    """
    last_error = None

    for attempt in range(config.retry_count):
        try:
            # Build command: nlm notebook query <notebook_id> "query"
            cmd = [
                "nlm",
                "notebook",
                "query",
                config.notebook_id,
                query
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.timeout_sec
            )

            if result.returncode == 0:
                return ToolResult(
                    success=True,
                    content=result.stdout,
                    error=None
                )

            # Non-zero return code - prepare for retry
            last_error = result.stderr or f"命令返回错误码: {result.returncode}"

        except subprocess.TimeoutExpired:
            last_error = f"工具调用超时（{config.timeout_sec}秒）"

        except FileNotFoundError:
            # nlm CLI not installed - don't retry
            return ToolResult(
                success=False,
                content="",
                error="错误：未找到 nlm 命令。请先安装 notebooklm-mcp-cli: pip install notebooklm-mcp-cli"
            )

        except Exception as e:
            last_error = f"工具调用异常: {str(e)}"

        # Wait before retry (if not last attempt)
        if attempt < config.retry_count - 1 and config.retry_delay_sec > 0:
            time.sleep(config.retry_delay_sec)

    # All retries exhausted
    return ToolResult(
        success=False,
        content="",
        error=f"NotebookLM搜索失败，已重试{config.retry_count}次。最后一次错误: {last_error}"
    )


class NotebookLMTool:
    """NotebookLM search tool for Claude SDK integration.

    This class wraps the search functionality in a format compatible
    with Claude's tool use API.
    """

    def __init__(self, config: Config):
        """Initialize the tool with configuration.

        Args:
            config: Application configuration.
        """
        self.config = config
        self.name = "search_notebooklm"
        self.description = "搜索NotebookLM笔记本中的资料。用于查找与写作主题相关的参考内容、案例和素材。"

    @property
    def input_schema(self) -> Dict[str, Any]:
        """JSON Schema for tool input.

        Returns:
            Schema dictionary for Claude SDK.
        """
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索问题，用于在NotebookLM中查找相关资料"
                }
            },
            "required": ["query"]
        }

    def execute(self, query: str) -> ToolResult:
        """Execute the search tool.

        Args:
            query: Search query string.

        Returns:
            ToolResult with search results or error.
        """
        return search_notebook(query, self.config)

    def to_claude_tool(self) -> Dict[str, Any]:
        """Convert to Claude SDK tool format.

        Returns:
            Dictionary compatible with Claude messages API.
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema
        }
