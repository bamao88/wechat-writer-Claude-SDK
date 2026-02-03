"""Writing assistant agent with multi-backend LLM (Anthropic/MiniMax + OpenAI)."""
from typing import Optional, Callable, TYPE_CHECKING
from dataclasses import dataclass

from src.config.settings import Config
from src.agent.backends import get_backend
from src.agent.backends.base import BackendResponse
from src.tools.notebooklm import NotebookLMTool
from src.utils.logger import get_logger
from src.utils.prompt_loader import load_prompt, PromptError

if TYPE_CHECKING:
    from src.output.tracer import OutputTracer

logger = get_logger(__name__)

# prompt_run.txt flow: 1 tool call (search) -> then analysis + outline + full article in one turn
MAX_ITERATIONS_PRODUCTION = 15
MAX_TOKENS_PRODUCTION = 8192
DEFAULT_PROMPT = "prompt_run.txt"


@dataclass
class AgentResult:
    """Result of agent execution."""
    success: bool
    output: str
    tool_calls: int
    error: Optional[str] = None


def _tool_to_def(tool: NotebookLMTool) -> dict:
    """Build normalized tool def (name, description, parameters) for backends."""
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.input_schema,
    }


class WritingAgent:
    """Writing assistant: NotebookLM tool + configurable LLM backend (Anthropic/MiniMax or OpenAI)."""

    def __init__(
        self,
        config: Config,
        prompt_name: Optional[str] = None,
    ):
        """Initialize the agent.

        Args:
            config: Application configuration (llm_provider: anthropic | openai).
            prompt_name: Name of prompt file in prompts/ (defaults to prompt_run.txt).
        """
        self.config = config
        self.tool = NotebookLMTool(config)
        self.prompt_name = prompt_name or DEFAULT_PROMPT
        self.backend = get_backend(config.llm_provider)
        logger.info(f"LLM 后端: {config.llm_provider}")

    def _handle_tool_call(self, tool_name: str, tool_input: dict) -> str:
        """Handle a tool call from the model."""
        if tool_name == self.tool.name:
            query = tool_input.get("query", "")
            logger.info(f"[NotebookLM] 搜索: {query[:50]}...")
            result = self.tool.execute(query=query)
            if result.success:
                return result.content
            return f"搜索失败: {result.error}"
        return f"未知工具: {tool_name}"

    def run(
        self,
        topic: str,
        system_prompt: Optional[str] = None,
        on_progress: Optional[Callable[[str], None]] = None,
        tracer: Optional["OutputTracer"] = None
    ) -> AgentResult:
        """Run the agent with a topic."""
        if on_progress:
            on_progress("[开始] 正在初始化...")

        if system_prompt is None:
            try:
                system_prompt = load_prompt(self.prompt_name)
                logger.info(f"已加载系统prompt: {self.prompt_name}")
            except PromptError as e:
                logger.error(f"Prompt加载失败: {e}")
                return AgentResult(success=False, output="", tool_calls=0, error=f"Prompt加载失败: {e}")

        tools = [_tool_to_def(self.tool)]
        messages: list = [{"role": "user", "content": f"选题：{topic}"}]
        tool_call_count = 0

        try:
            for iteration in range(MAX_ITERATIONS_PRODUCTION):
                if on_progress:
                    on_progress(f"[对话] 第{iteration + 1}轮...")

                resp: BackendResponse = self.backend.create(
                    system=system_prompt,
                    messages=messages,
                    tools=tools,
                    max_tokens=MAX_TOKENS_PRODUCTION,
                )

                if tracer and resp.content_text:
                    tracer.append_agent_output(resp.content_text)

                if resp.stop_reason == "end_turn":
                    if tracer:
                        tracer.save_article(resp.content_text)
                        tracer.close()
                    if on_progress:
                        on_progress("[完成]")
                    return AgentResult(
                        success=True,
                        output=resp.content_text,
                        tool_calls=tool_call_count,
                    )

                if resp.stop_reason == "tool_use" and resp.tool_calls:
                    tool_results: list = []
                    assistant_content = resp.content_text
                    assistant_tool_calls = [
                        {"id": tc.id, "name": tc.name, "input": tc.input}
                        for tc in resp.tool_calls
                    ]
                    for tc in resp.tool_calls:
                        tool_call_count += 1
                        if on_progress:
                            on_progress(f"[工具] 调用 {tc.name}...")
                        if tracer:
                            tracer.append_tool_call(tc.name, tc.input)
                        result = self._handle_tool_call(tc.name, tc.input)
                        if tracer:
                            tracer.append_tool_result(result)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tc.id,
                            "content": result,
                        })
                    messages.append({
                        "role": "assistant",
                        "content": assistant_content,
                        "tool_calls": assistant_tool_calls,
                    })
                    messages.append({"role": "user", "content": tool_results})
                else:
                    logger.warning(f"意外的停止原因: {resp.stop_reason}")
                    break

            return AgentResult(
                success=False,
                output="",
                tool_calls=tool_call_count,
                error="达到最大对话轮数限制",
            )
        except Exception as e:
            logger.error(f"Agent执行错误: {e}")
            return AgentResult(
                success=False,
                output="",
                tool_calls=tool_call_count,
                error=str(e),
            )


def create_agent(config: Config, prompt_name: Optional[str] = None) -> WritingAgent:
    """Create a configured WritingAgent."""
    return WritingAgent(config, prompt_name=prompt_name)


def run_agent(
    topic: str,
    config: Config,
    prompt_name: Optional[str] = None,
    on_progress: Optional[Callable[[str], None]] = None,
    tracer: Optional["OutputTracer"] = None
) -> AgentResult:
    """Convenience: create agent and run with topic."""
    agent = create_agent(config, prompt_name=prompt_name)
    return agent.run(topic, on_progress=on_progress, tracer=tracer)
