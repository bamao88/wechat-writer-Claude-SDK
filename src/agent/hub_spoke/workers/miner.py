"""Miner Worker for hub-spoke architecture.

The Miner performs private domain research by querying NotebookLM
and extracting dual-layer output:
- structured_points: For Orchestrator to arrange outline
- raw_voice_clips: For Writer to learn user's voice/style
"""
import json
from dataclasses import dataclass
from typing import List, TYPE_CHECKING

from src.agent.hub_spoke.state import State
from src.utils.logger import get_logger
from src.utils.prompt_loader import load_prompt

if TYPE_CHECKING:
    from src.agent.backends.base import LLMBackend
    from src.output.tracer import OutputTracer
    from src.tools.notebooklm import NotebookLMTool

logger = get_logger(__name__)

MAX_TOKENS = 1000


@dataclass
class MinerResult:
    """Result from Miner worker (dual-layer output).

    Attributes:
        structured_points: Structured talking points for Orchestrator
        raw_voice_clips: Original voice clips for Writer to match style
    """
    structured_points: List[str]
    raw_voice_clips: List[str]


class MinerWorker:
    """Miner worker for private domain research.

    Queries NotebookLM knowledge base and extracts:
    1. Structured points (for outline arrangement)
    2. Raw voice clips (for style matching)

    Output format (JSON):
    {
        "structured_points": ["观点1", "观点2", ...],
        "raw_voice_clips": ["原话片段1", "原话片段2", ...]
    }

    Total output: ≤500 chars
    """

    def __init__(self):
        """Initialize Miner worker."""
        pass

    def _parse_json_output(self, output: str) -> MinerResult:
        """Parse dual-layer JSON output from Miner.

        Args:
            output: LLM output text (should be JSON)

        Returns:
            MinerResult with parsed values, or empty fallback on error
        """
        try:
            # Extract JSON from output
            output = output.strip()

            # Look for JSON object
            start = output.find('{')
            end = output.rfind('}')

            if start != -1 and end != -1 and end > start:
                json_str = output[start:end+1]
                data = json.loads(json_str)
            else:
                data = json.loads(output)

            # Extract fields
            structured_points = data.get('structured_points', [])
            raw_voice_clips = data.get('raw_voice_clips', [])

            # Ensure they are lists
            if not isinstance(structured_points, list):
                structured_points = []
            if not isinstance(raw_voice_clips, list):
                raw_voice_clips = []

            return MinerResult(
                structured_points=structured_points,
                raw_voice_clips=raw_voice_clips
            )

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse Miner JSON output: {e}")
            logger.debug(f"Raw output: {output[:200]}...")

            # Fallback: empty result
            return MinerResult(
                structured_points=[],
                raw_voice_clips=[]
            )

    def run(
        self,
        state: State,
        notebooklm_tool: 'NotebookLMTool',
        backend: 'LLMBackend',
        tracer: 'OutputTracer'
    ) -> MinerResult:
        """Execute Miner to extract dual-layer output from NotebookLM.

        Args:
            state: Current State object (reads topic)
            notebooklm_tool: NotebookLM tool instance
            backend: LLM backend for processing
            tracer: OutputTracer for logging

        Returns:
            MinerResult with structured_points and raw_voice_clips
        """
        try:
            # Step 1: Extract clean topic (first line only, remove "选题：" prefix if present)
            clean_topic = state.topic.strip().split('\n')[0]
            if clean_topic.startswith('选题：') or clean_topic.startswith('选题:'):
                clean_topic = clean_topic.split('：', 1)[-1].split(':', 1)[-1].strip()

            # Query NotebookLM with clean topic
            query = f"{clean_topic}\n\n请提供与此选题相关的素材、观点和原话片段。"

            logger.info(f"Miner querying NotebookLM: {query[:80]}...")

            tool_result = notebooklm_tool.execute(query)

            if not tool_result.success:
                logger.warning(f"NotebookLM query failed: {tool_result.error}")
                # Return empty result
                return MinerResult(structured_points=[], raw_voice_clips=[])

            notebooklm_content = tool_result.content

            # Step 2: Use LLM to extract dual-layer structure
            system_prompt = load_prompt("miner.txt")

            user_message = f"""选题：{state.topic}

NotebookLM返回结果：
{notebooklm_content}

请按照双层JSON格式提取structured_points和raw_voice_clips。"""

            messages = [{"role": "user", "content": user_message}]

            # Record input
            tracer.append_agent_input(
                agent_name="Miner",
                system_prompt=system_prompt,
                messages=messages,
                routing_info={
                    "triggered_by": "Planner",
                    "reason": "需要私域调研",
                    "expected_output": "双层JSON（structured_points + raw_voice_clips）"
                }
            )

            # Call LLM
            response = backend.create(
                system=system_prompt,
                messages=messages,
                tools=[],
                max_tokens=MAX_TOKENS
            )

            output_text = response.content_text

            # Record output
            tracer.append_agent_output(output_text, agent_name="Miner")

            # Parse JSON
            result = self._parse_json_output(output_text)

            # Log result
            logger.info(
                f"Miner extracted: {len(result.structured_points)} points, "
                f"{len(result.raw_voice_clips)} clips"
            )

            # Check output length (warning only)
            total_length = sum(len(p) for p in result.structured_points)
            total_length += sum(len(c) for c in result.raw_voice_clips)

            if total_length > 500:
                logger.warning(
                    f"Miner output length ({total_length} chars) exceeds "
                    f"recommended limit (500 chars)"
                )

            return result

        except Exception as e:
            logger.error(f"Miner execution error: {e}", exc_info=True)

            # Fallback: empty result
            return MinerResult(
                structured_points=[],
                raw_voice_clips=[]
            )
