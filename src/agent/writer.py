"""Writing assistant agent using Claude SDK with tool support."""
import os
from typing import Optional, Callable
from dataclasses import dataclass

from anthropic import Anthropic

from src.config.settings import Config
from src.tools.notebooklm import NotebookLMTool, ToolResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AgentResult:
    """Result of agent execution."""
    success: bool
    output: str
    tool_calls: int
    error: Optional[str] = None


class WritingAgent:
    """Writing assistant agent that uses Claude with NotebookLM tool."""

    def __init__(
        self,
        config: Config,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        """Initialize the agent.

        Args:
            config: Application configuration.
            api_key: Claude API key (defaults to CLAUDE_API_KEY env var).
            base_url: Claude API base URL (defaults to CLAUDE_BASE_URL env var).
        """
        self.config = config
        self.tool = NotebookLMTool(config)

        # Initialize Claude client
        self.client = Anthropic(
            api_key=api_key or os.getenv("CLAUDE_API_KEY"),
            base_url=base_url or os.getenv("CLAUDE_BASE_URL")
        )

        self.model = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

    def _handle_tool_call(self, tool_name: str, tool_input: dict) -> str:
        """Handle a tool call from Claude.

        Args:
            tool_name: Name of the tool to call.
            tool_input: Input parameters for the tool.

        Returns:
            Tool result as string.
        """
        if tool_name == self.tool.name:
            query = tool_input.get("query", "")
            logger.info(f"[NotebookLM] 搜索: {query[:50]}...")
            result = self.tool.execute(query=query)

            if result.success:
                return result.content
            else:
                return f"搜索失败: {result.error}"

        return f"未知工具: {tool_name}"

    def run(
        self,
        topic: str,
        system_prompt: Optional[str] = None,
        on_progress: Optional[Callable[[str], None]] = None
    ) -> AgentResult:
        """Run the agent with a topic.

        Args:
            topic: Writing topic from user.
            system_prompt: Optional system prompt (defaults to basic assistant).
            on_progress: Optional callback for progress updates.

        Returns:
            AgentResult with output and statistics.
        """
        if on_progress:
            on_progress("[开始] 正在初始化...")

        # Default system prompt for Phase 1 (basic test)
        if system_prompt is None:
            system_prompt = """你是一个写作助手。当用户给你一个选题时，
你需要先使用 search_notebooklm 工具搜索相关资料，
然后基于搜索结果给出一个简短的回复，说明你找到了什么资料。
这是Phase 1测试，只需要验证工具调用成功即可。"""

        messages = [
            {"role": "user", "content": f"我要写一篇关于「{topic}」的文章，请先搜索一下相关资料。"}
        ]

        tools = [self.tool.to_claude_tool()]
        tool_call_count = 0
        max_iterations = 5  # Prevent infinite loops

        try:
            for iteration in range(max_iterations):
                if on_progress:
                    on_progress(f"[对话] 第{iteration + 1}轮...")

                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=messages,
                    tools=tools
                )

                # Check stop reason
                if response.stop_reason == "end_turn":
                    # Agent finished
                    final_text = ""
                    for block in response.content:
                        if hasattr(block, "text"):
                            final_text += block.text

                    if on_progress:
                        on_progress("[完成]")

                    return AgentResult(
                        success=True,
                        output=final_text,
                        tool_calls=tool_call_count
                    )

                elif response.stop_reason == "tool_use":
                    # Handle tool calls
                    assistant_content = response.content
                    tool_results = []

                    for block in assistant_content:
                        if block.type == "tool_use":
                            tool_call_count += 1
                            if on_progress:
                                on_progress(f"[工具] 调用 {block.name}...")

                            result = self._handle_tool_call(
                                block.name,
                                block.input
                            )

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result
                            })

                    # Add assistant response and tool results to messages
                    messages.append({"role": "assistant", "content": assistant_content})
                    messages.append({"role": "user", "content": tool_results})

                else:
                    # Unexpected stop reason
                    logger.warning(f"意外的停止原因: {response.stop_reason}")
                    break

            # Max iterations reached
            return AgentResult(
                success=False,
                output="",
                tool_calls=tool_call_count,
                error="达到最大对话轮数限制"
            )

        except Exception as e:
            logger.error(f"Agent执行错误: {e}")
            return AgentResult(
                success=False,
                output="",
                tool_calls=tool_call_count,
                error=str(e)
            )


def create_agent(config: Config) -> WritingAgent:
    """Factory function to create an agent.

    Args:
        config: Application configuration.

    Returns:
        Configured WritingAgent instance.
    """
    return WritingAgent(config)


def run_agent(topic: str, config: Config, on_progress: Optional[Callable[[str], None]] = None) -> AgentResult:
    """Convenience function to create and run an agent.

    Args:
        topic: Writing topic.
        config: Application configuration.
        on_progress: Optional progress callback.

    Returns:
        AgentResult from agent execution.
    """
    agent = create_agent(config)
    return agent.run(topic, on_progress=on_progress)
