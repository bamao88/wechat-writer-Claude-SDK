"""Planner Agent for hub-spoke architecture.

The Planner decides the research path based on the topic and user context:
- use_private: Whether to call Miner for private domain research
- use_web: Whether to call Web for public research
- Both can be False only when user provides ≥300 chars context
"""
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.agent.hub_spoke.state import State
from src.utils.logger import get_logger
from src.utils.prompt_loader import load_prompt

if TYPE_CHECKING:
    from src.agent.backends.base import LLMBackend
    from src.output.tracer import OutputTracer

logger = get_logger(__name__)

MAX_TOKENS = 500


@dataclass
class PlannerResult:
    """Result from Planner agent decision.

    Attributes:
        use_private: Whether to use private domain research (Miner)
        use_web: Whether to use web research
        reason: Planner's reasoning for the decision
    """
    use_private: bool
    use_web: bool
    reason: str


class PlannerWorker:
    """Planner agent that decides research path.

    The Planner analyzes the topic and user context to determine:
    1. Whether private domain research is needed (use_private)
    2. Whether web research is needed (use_web)
    3. The reasoning behind this decision

    Output format: JSON
    {
        "use_private": bool,
        "use_web": bool,
        "reason": str
    }
    """

    def __init__(self):
        """Initialize Planner worker."""
        pass

    def _parse_json_output(self, output: str) -> PlannerResult:
        """Parse JSON output from Planner.

        Args:
            output: LLM output text (should be JSON)

        Returns:
            PlannerResult with parsed values, or fallback default on error

        Fallback strategy:
            If JSON parsing fails, return safe default (both True) to ensure
            complete research rather than skipping it.
        """
        try:
            # Try to extract JSON from output
            # Handle cases where LLM adds text before/after JSON
            output = output.strip()

            # Look for JSON object pattern
            start = output.find('{')
            end = output.rfind('}')

            if start != -1 and end != -1 and end > start:
                json_str = output[start:end+1]
                data = json.loads(json_str)
            else:
                data = json.loads(output)

            # Extract fields with defaults
            use_private = bool(data.get('use_private', True))
            use_web = bool(data.get('use_web', True))
            reason = str(data.get('reason', '未提供原因'))

            return PlannerResult(
                use_private=use_private,
                use_web=use_web,
                reason=reason
            )

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse Planner JSON output: {e}")
            logger.debug(f"Raw output: {output[:200]}...")

            # Fallback: safe default (both True)
            return PlannerResult(
                use_private=True,
                use_web=True,
                reason=f"JSON解析失败，使用默认策略（全量调研）。错误: {str(e)}"
            )

    def run(
        self,
        state: State,
        backend: 'LLMBackend',
        tracer: 'OutputTracer'
    ) -> PlannerResult:
        """Execute Planner agent to decide research path.

        Args:
            state: Current State object (reads topic, user_context)
            backend: LLM backend for API calls
            tracer: OutputTracer for logging

        Returns:
            PlannerResult with decision

        Side effects:
            Updates state.use_private, state.use_web, state.planner_reason
        """
        try:
            # Load prompt
            system_prompt = load_prompt("planner.txt")

            # Build user message
            user_message = f"选题：{state.topic}"
            if state.user_context:
                user_message += f"\n\n用户上下文：\n{state.user_context}"

            messages = [{"role": "user", "content": user_message}]

            # Record input
            tracer.append_agent_input(
                agent_name="Planner",
                system_prompt=system_prompt,
                messages=messages,
                routing_info={
                    "triggered_by": "User",
                    "reason": "开始新的写作任务，决定调研路径",
                    "expected_output": "use_private和use_web决策（JSON格式）"
                }
            )

            # Call LLM
            response = backend.create(
                system=system_prompt,
                messages=messages,
                tools=[],  # No tools needed for Planner
                max_tokens=MAX_TOKENS
            )

            # Extract text
            output_text = response.content_text

            # Record output
            tracer.append_agent_output(output_text, agent_name="Planner")

            # Parse JSON
            result = self._parse_json_output(output_text)

            # Update state
            state.use_private = result.use_private
            state.use_web = result.use_web
            state.planner_reason = result.reason

            logger.info(
                f"Planner decision: use_private={result.use_private}, "
                f"use_web={result.use_web}, reason='{result.reason[:50]}...'"
            )

            return result

        except Exception as e:
            # Handle any errors gracefully
            logger.error(f"Planner execution error: {e}", exc_info=True)

            # Fallback to safe default
            result = PlannerResult(
                use_private=True,
                use_web=True,
                reason=f"执行错误，使用默认策略。错误: {str(e)}"
            )

            # Still update state even on error
            state.use_private = result.use_private
            state.use_web = result.use_web
            state.planner_reason = result.reason

            return result
