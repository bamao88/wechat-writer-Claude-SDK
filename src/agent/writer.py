"""Writing assistant agent using Claude SDK with tool support."""
import os
from typing import Optional, Callable
from dataclasses import dataclass

from anthropic import Anthropic

from src.config.settings import Config
from src.tools.notebooklm import NotebookLMTool, ToolResult
from src.utils.logger import get_logger
from src.utils.prompt_loader import load_prompt, PromptError

logger = get_logger(__name__)

# Production workflow requires multiple research rounds
# prompt_run.txt flow: 1st search -> 2nd search -> (optional 3rd) -> outline -> write
# Each search + response = 2 iterations, so need ~15 for safety
MAX_ITERATIONS_PRODUCTION = 15

# Articles can be 3000-5000 characters; with Chinese + formatting, need ~8000 tokens
MAX_TOKENS_PRODUCTION = 8192

# Default prompt file name
DEFAULT_PROMPT = "prompt_run.txt"


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
        base_url: Optional[str] = None,
        prompt_name: Optional[str] = None
    ):
        """Initialize the agent.

        Args:
            config: Application configuration.
            api_key: Claude API key (defaults to CLAUDE_API_KEY env var).
            base_url: Claude API base URL (defaults to CLAUDE_BASE_URL env var).
            prompt_name: Name of prompt file in prompts/ (defaults to prompt_run.txt).
        """
        self.config = config
        self.tool = NotebookLMTool(config)
        self.prompt_name = prompt_name or DEFAULT_PROMPT

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
            system_prompt: Optional system prompt (overrides prompt file).
            on_progress: Optional callback for progress updates.

        Returns:
            AgentResult with output and statistics.
        """
        if on_progress:
            on_progress("[开始] 正在初始化...")

        # Load system prompt from file or use provided
        if system_prompt is None:
            try:
                system_prompt = load_prompt(self.prompt_name)
                logger.info(f"已加载系统prompt: {self.prompt_name}")
            except PromptError as e:
                logger.error(f"Prompt加载失败: {e}")
                return AgentResult(
                    success=False,
                    output="",
                    tool_calls=0,
                    error=f"Prompt加载失败: {e}"
                )

        # User message - just the topic, prompt handles workflow
        messages = [
            {"role": "user", "content": f"选题：{topic}"}
        ]

        tools = [self.tool.to_claude_tool()]
        tool_call_count = 0

        try:
            for iteration in range(MAX_ITERATIONS_PRODUCTION):
                if on_progress:
                    on_progress(f"[对话] 第{iteration + 1}轮...")

                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=MAX_TOKENS_PRODUCTION,
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


def create_agent(config: Config, prompt_name: Optional[str] = None) -> WritingAgent:
    """Factory function to create an agent.

    Args:
        config: Application configuration.
        prompt_name: Optional prompt file name.

    Returns:
        Configured WritingAgent instance.
    """
    return WritingAgent(config, prompt_name=prompt_name)


def run_agent(
    topic: str,
    config: Config,
    prompt_name: Optional[str] = None,
    on_progress: Optional[Callable[[str], None]] = None
) -> AgentResult:
    """Convenience function to create and run an agent.

    Args:
        topic: Writing topic.
        config: Application configuration.
        prompt_name: Optional prompt file name.
        on_progress: Optional progress callback.

    Returns:
        AgentResult from agent execution.
    """
    agent = create_agent(config, prompt_name=prompt_name)
    return agent.run(topic, on_progress=on_progress)
