"""Executor for hub-spoke architecture.

The Executor implements the main while loop that orchestrates all workers:
- State machine transitions (planner → miner → web → orchestrator → writer → critic)
- Rewrite loop (critic → writer backtracking)
- Degraded output handling (max iterations)
"""
from typing import Dict, Any, TYPE_CHECKING

from src.agent.hub_spoke.state import State
from src.agent.hub_spoke.router import determine_next_step
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.agent.backends.base import LLMBackend
    from src.output.tracer import OutputTracer

logger = get_logger(__name__)

# Maximum rewrite iterations before degraded output
MAX_ITERATIONS = 3


class Executor:
    """Hub-spoke architecture executor.

    Implements the main control loop that:
    1. Routes to appropriate worker based on state.next_step
    2. Updates state after each worker execution
    3. Handles critic feedback and rewrite loops
    4. Manages degraded output when max iterations exceeded
    """

    def __init__(self):
        """Initialize Executor."""
        self.max_iterations = MAX_ITERATIONS

    def run(
        self,
        state: State,
        workers: Dict[str, Any],
        tools: Dict[str, Any],
        backend: 'LLMBackend',
        tracer: 'OutputTracer'
    ) -> State:
        """Execute the hub-spoke workflow.

        Args:
            state: Current State object (will be modified in-place)
            workers: Dictionary of worker instances (planner, miner, orchestrator, writer, critic)
            tools: Dictionary of tool instances (notebooklm, web_search)
            backend: LLM backend for API calls
            tracer: OutputTracer for logging

        Returns:
            Final State object

        Main loop:
        ```
        while state.next_step != "done":
            if state.next_step == "planner":
                planner_result = workers["planner"].run(state, backend, tracer)
                # State is updated by planner
                state.next_step = determine_next_step(state, "")
            elif state.next_step == "miner":
                # ... similar
            # etc.
        ```
        """
        state.status = "IN_PROGRESS"

        try:
            # Main loop
            while state.next_step != "done":
                current_step = state.next_step
                logger.info(f"Executing step: {current_step}")

                try:
                    if current_step == "planner":
                        self._execute_planner(state, workers, backend, tracer)

                    elif current_step == "miner":
                        self._execute_miner(state, workers, tools, backend, tracer)

                    elif current_step == "web":
                        self._execute_web(state, workers, tools, backend, tracer)

                    elif current_step == "orchestrator":
                        self._execute_orchestrator(state, workers, backend, tracer)

                    elif current_step == "writer":
                        self._execute_writer(state, workers, backend, tracer)

                    elif current_step == "critic":
                        self._execute_critic(state, workers, tracer)

                    else:
                        raise ValueError(f"Unknown step: {current_step}")

                except Exception as e:
                    logger.error(f"Error in step {current_step}: {e}", exc_info=True)
                    state.status = "ERROR"
                    raise

            # Final status
            if state.status == "IN_PROGRESS":
                if state.iteration_count >= self.max_iterations and state.critic_score < 7:
                    state.status = "DEGRADED_OUTPUT"
                else:
                    state.status = "COMPLETED"

            logger.info(f"Executor finished with status: {state.status}")

        finally:
            # Record final status to trace and ensure tracer is always closed
            # This block runs regardless of success or exception
            if tracer:
                # Add final status marker
                if state.status:
                    final_msg = f"\n## 🏁 执行完成\n\n**状态**: {state.status}\n\n**最终评分**: {state.critic_score}/10\n\n"
                    tracer._append_to_trace(final_msg)

                # ✅ ALWAYS close tracer (critical for log completeness)
                tracer.close()

        return state

    def _execute_planner(self, state, workers, backend, tracer):
        """Execute Planner worker."""
        planner = workers.get("planner")
        if not planner:
            raise ValueError("Planner worker not found")

        result = planner.run(state, backend, tracer)

        # State is already updated by planner
        # Determine next step based on use_private/use_web flags
        state.next_step = determine_next_step(state, "")

    def _execute_miner(self, state, workers, tools, backend, tracer):
        """Execute Miner worker (private domain research)."""
        miner = workers.get("miner")
        if not miner:
            logger.warning("Miner worker not found, skipping")
            state.next_step = determine_next_step(state, "")
            return

        # Miner uses NotebookLM tool
        notebooklm_tool = tools.get("notebooklm") or tools.get("search_notebooklm")

        result = miner.run(state, notebooklm_tool, backend, tracer)

        # Update state with miner results
        if hasattr(result, 'structured_points'):
            state.structured_points = result.structured_points
        if hasattr(result, 'raw_voice_clips'):
            state.raw_voice_clips = result.raw_voice_clips

        # Determine next step
        state.next_step = determine_next_step(state, "")

    def _execute_web(self, state, workers, tools, backend, tracer):
        """Execute Web worker (public research)."""
        web = workers.get("web")
        if not web:
            logger.warning("Web worker not found, skipping")
            state.next_step = determine_next_step(state, "")
            return

        # Web uses web search tool
        web_tool = tools.get("web_search") or tools.get("search_web")

        result = web.run(state, web_tool, backend, tracer)

        # Update state with web results (dual-layer output)
        if hasattr(result, 'web_structured_points'):
            state.web_structured_points = result.web_structured_points
        if hasattr(result, 'web_raw_quotes'):
            state.web_raw_quotes = result.web_raw_quotes

        # Determine next step
        state.next_step = determine_next_step(state, "")

    def _execute_orchestrator(self, state, workers, backend, tracer):
        """Execute Orchestrator worker (outline generation)."""
        orchestrator = workers.get("orchestrator")
        if not orchestrator:
            raise ValueError("Orchestrator worker not found")

        result = orchestrator.run(state, backend, tracer)

        # Update state with outline
        if hasattr(result, 'outline'):
            state.outline = result.outline

        # Determine next step
        state.next_step = determine_next_step(state, "")

    def _execute_writer(self, state, workers, backend, tracer):
        """Execute Writer worker (draft generation)."""
        writer = workers.get("writer")
        if not writer:
            raise ValueError("Writer worker not found")

        result = writer.run(state, backend, tracer)

        # Update state with draft
        if hasattr(result, 'draft'):
            state.draft = result.draft

        # Determine next step (always goes to critic)
        state.next_step = determine_next_step(state, "")

    def _execute_critic(self, state, workers, tracer):
        """Execute Critic worker (quality check)."""
        critic = workers.get("critic")
        if not critic:
            raise ValueError("Critic worker not found")

        result = critic.run(state)

        # Update state with critic results
        state.critic_score = result.score
        state.critic_reason = result.reason

        # Record critic result in trace
        tracer.append_critic_result(
            cycle=state.iteration_count + 1,
            score=result.score,
            passed=result.passed,
            reason=result.reason
        )

        # Determine next action based on critic result
        if result.passed:
            # Quality check passed, save and finish
            tracer.save_article(state.draft, degraded=False)
            state.next_step = "done"
            logger.info(f"Critic passed with score {result.score}")

        elif state.iteration_count >= self.max_iterations:
            # Max iterations reached, save degraded output
            logger.warning(
                f"Max iterations ({self.max_iterations}) reached, "
                f"saving degraded output (score: {result.score})"
            )
            tracer.save_article(state.draft, degraded=True)
            state.next_step = "done"

        else:
            # Need rewrite
            state.critic_feedback = result.reason
            state.iteration_count += 1
            state.next_step = "writer"  # Go back to writer
            logger.info(
                f"Critic failed (score {result.score}), "
                f"rewrite attempt {state.iteration_count}/{self.max_iterations}"
            )
