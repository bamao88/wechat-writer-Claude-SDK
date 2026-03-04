"""Orchestrator Worker for hub-spoke architecture (outline generation)."""
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.agent.hub_spoke.state import State
from src.utils.logger import get_logger
from src.utils.prompt_loader import load_prompt

if TYPE_CHECKING:
    from src.agent.backends.base import LLMBackend
    from src.output.tracer import OutputTracer

logger = get_logger(__name__)

MAX_TOKENS = 1000


@dataclass
class OrchestratorResult:
    """Result from Orchestrator worker."""
    outline: str


class OrchestratorWorker:
    """Orchestrator worker for outline generation.

    Inputs: structured_points + web_structured_points
    Output: Compact outline (≤800 chars)
    """

    def __init__(self):
        """Initialize Orchestrator worker."""
        pass

    def run(
        self,
        state: State,
        backend: 'LLMBackend',
        tracer: 'OutputTracer'
    ) -> OrchestratorResult:
        """Execute Orchestrator to generate outline.

        Args:
            state: Current State (reads structured_points, web_structured_points)
            backend: LLM backend
            tracer: OutputTracer

        Returns:
            OrchestratorResult with outline
        """
        try:
            system_prompt = load_prompt("orchestrator.txt")

            # Build context from research materials
            context_parts = []

            if state.structured_points:
                points_text = "\n".join(f"- {p}" for p in state.structured_points)
                context_parts.append(f"**私域观点**：\n{points_text}")

            if state.web_structured_points:
                web_points_text = "\n".join(f"- {p}" for p in state.web_structured_points)
                context_parts.append(f"**全网调研**：\n{web_points_text}")

            if state.user_context:
                context_parts.append(f"**用户上下文**：\n{state.user_context}")

            context = "\n\n".join(context_parts) if context_parts else "（无调研素材）"

            user_message = f"""选题：{state.topic}

调研素材：
{context}

请编排紧凑大纲（≤800字）。"""

            messages = [{"role": "user", "content": user_message}]

            tracer.append_agent_input("Orchestrator", system_prompt, messages)

            response = backend.create(
                system=system_prompt,
                messages=messages,
                tools=[],
                max_tokens=MAX_TOKENS
            )

            outline = response.content_text

            tracer.append_agent_output(outline, "Orchestrator")

            logger.info(f"Orchestrator generated outline ({len(outline)} chars)")

            if len(outline) > 800:
                logger.warning(f"Outline exceeds 800 chars: {len(outline)}")

            return OrchestratorResult(outline=outline)

        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            return OrchestratorResult(outline="")
