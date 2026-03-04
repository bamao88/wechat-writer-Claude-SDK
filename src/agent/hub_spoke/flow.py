"""Hub-spoke flow: Planner → Miner/Web → Orchestrator → Writer → Critic (with rewrite loop).

This module provides the main entry point for the hub-spoke architecture workflow.
"""
from typing import Optional, Callable, TYPE_CHECKING
from dataclasses import dataclass

from src.agent.hub_spoke.state import State
from src.agent.hub_spoke.executor import Executor
from src.agent.hub_spoke.workers import create_workers
from src.agent.hub_spoke.tools import create_tools
from src.agent.backends import get_backend
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.config.settings import Config
    from src.output.tracer import OutputTracer

logger = get_logger(__name__)


@dataclass
class HubSpokeResult:
    """Result from hub-spoke workflow.

    Attributes:
        success: Whether the workflow completed successfully
        output: Final article draft
        degraded: Whether output is degraded (max iterations reached without passing critic)
        tool_calls: Total number of tool calls made (NotebookLM + Web)
        error: Error message if workflow failed
    """
    success: bool
    output: str
    degraded: bool = False
    tool_calls: int = 0
    error: Optional[str] = None


def run_hub_spoke_flow(
    topic: str,
    user_context: str = "",
    config: Optional["Config"] = None,
    on_progress: Optional[Callable[[str], None]] = None,
    tracer: Optional["OutputTracer"] = None,
) -> HubSpokeResult:
    """Execute hub-spoke workflow from topic to article.

    Workflow stages:
    1. Planner: Decide research path (use_private, use_web)
    2. Miner: Private domain research (if use_private)
    3. Web: Public research (if use_web)
    4. Orchestrator: Generate outline from research materials
    5. Writer: Generate draft article
    6. Critic: Quality check (may loop back to Writer ≤3 times)

    Args:
        topic: User's topic/question
        user_context: Optional user context (≥300 chars allows skipping research)
        config: Application configuration
        on_progress: Optional callback for progress updates
        tracer: OutputTracer for logging

    Returns:
        HubSpokeResult with final article and metadata

    Example:
        >>> from src.config.settings import load_config
        >>> config = load_config()
        >>> result = run_hub_spoke_flow("如何提升个人品牌", config=config)
        >>> if result.success:
        ...     print(result.output)
    """
    if config is None:
        from src.config.settings import load_config
        config = load_config()

    # Initialize state
    state = State(topic=topic, user_context=user_context)

    # Initialize backend, tools, workers
    try:
        backend = get_backend(config.llm_provider)
        tools = create_tools(config)
        workers = create_workers()
    except Exception as e:
        logger.error(f"Failed to initialize hub-spoke components: {e}", exc_info=True)
        return HubSpokeResult(
            success=False,
            output="",
            error=f"Initialization error: {e}"
        )

    if on_progress:
        on_progress("[开始] Hub-Spoke 流程...")
    logger.info(f"[Hub-Spoke] Starting workflow for topic: {topic[:50]}...")

    # Execute workflow
    try:
        executor = Executor()
        final_state = executor.run(state, workers, tools, backend, tracer)

        # Check final status
        if final_state.status == "ERROR":
            return HubSpokeResult(
                success=False,
                output=final_state.draft or "",
                error="Workflow encountered an error"
            )

        degraded = (final_state.status == "DEGRADED_OUTPUT")
        if degraded:
            logger.warning(
                f"Workflow completed with degraded output "
                f"(critic score: {final_state.critic_score})"
            )
            if on_progress:
                on_progress("[警告] 输出质量未达标准，已保存降级版本")
        else:
            logger.info("Workflow completed successfully")
            if on_progress:
                on_progress("[完成] Hub-Spoke 流程成功")

        # Count tool calls (NotebookLM + Web)
        tool_calls = 0
        if final_state.structured_points or final_state.raw_voice_clips:
            tool_calls += 1  # Miner was called
        if final_state.web_structured_points or final_state.web_raw_quotes:
            tool_calls += 1  # Web was called

        return HubSpokeResult(
            success=True,
            output=final_state.draft,
            degraded=degraded,
            tool_calls=tool_calls,
        )

    except Exception as e:
        logger.error(f"Hub-spoke workflow error: {e}", exc_info=True)
        if on_progress:
            on_progress(f"[错误] 流程失败: {e}")

        # Close tracer even on error to preserve logs
        if tracer:
            tracer.close()

        return HubSpokeResult(
            success=False,
            output="",
            error=str(e)
        )


__all__ = ["run_hub_spoke_flow", "HubSpokeResult"]
