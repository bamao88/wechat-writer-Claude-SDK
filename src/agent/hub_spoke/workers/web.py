"""Web Worker for hub-spoke architecture (web research with LLM processing)."""
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, List

from src.agent.hub_spoke.state import State
from src.utils.logger import get_logger
from src.utils.prompt_loader import load_prompt

if TYPE_CHECKING:
    from src.agent.backends.base import LLMBackend
    from src.output.tracer import OutputTracer
    from src.tools.web_search import WebSearchTool

logger = get_logger(__name__)

MAX_TOKENS = 1000


@dataclass
class WebResult:
    """Result from Web worker (dual-layer output)."""
    web_structured_points: List[str]
    web_raw_quotes: List[str]


class WebWorker:
    """Web worker for public domain research using web search + LLM processing.

    Similar to Miner, Web worker:
    1. Calls Tavily API to get search results
    2. Uses LLM to process and extract key information
    3. Outputs dual-layer structure:
       - structured_points: Key information for Orchestrator
       - raw_quotes: Original quotes for Writer to cite
    """

    def __init__(self):
        """Initialize Web worker."""
        pass

    def run(
        self,
        state: State,
        web_tool: 'WebSearchTool',
        backend: 'LLMBackend',
        tracer: 'OutputTracer'
    ) -> WebResult:
        """Execute web search and LLM processing.

        Args:
            state: Current State (reads topic)
            web_tool: WebSearchTool instance
            backend: LLM backend for processing search results
            tracer: OutputTracer for logging

        Returns:
            WebResult with dual-layer structured output
        """
        try:
            # Extract clean topic (first line only, remove "选题：" prefix if present)
            clean_topic = state.topic.strip().split('\n')[0]
            if clean_topic.startswith('选题：') or clean_topic.startswith('选题:'):
                clean_topic = clean_topic.split('：', 1)[-1].split(':', 1)[-1].strip()

            query = clean_topic
            logger.info(f"Web worker searching: {query}")

            # Step 1: Execute web search
            tool_result = web_tool.execute(query)

            if not tool_result.success or not tool_result.content:
                logger.warning(f"Web search failed or returned no results: {tool_result.error}")
                # Return empty result
                return WebResult(
                    web_structured_points=[],
                    web_raw_quotes=[]
                )

            search_results = tool_result.content
            logger.info(f"Web search returned {len(search_results)} chars")

            # Step 2: Load web processing prompt
            system_prompt = load_prompt("web.txt")

            # Step 3: Build message for LLM
            user_message = f"""选题：{state.topic}

Web搜索结果：
{search_results}

请根据上述搜索结果，提炼与选题相关的关键信息，输出双层JSON格式。"""

            messages = [{"role": "user", "content": user_message}]

            # Record input
            tracer.append_agent_input(
                agent_name="Web",
                system_prompt=system_prompt[:200] + "...",
                messages=messages
            )

            # Step 4: Call LLM
            response = backend.create(
                system=system_prompt,
                messages=messages,
                tools=[],
                max_tokens=MAX_TOKENS
            )

            # Extract text
            output_text = response.content_text

            # Record output
            tracer.append_agent_output(output_text, agent_name="Web")

            # Step 5: Parse JSON
            result = self._parse_json_output(output_text)

            # Update state
            state.web_structured_points = result.web_structured_points
            state.web_raw_quotes = result.web_raw_quotes

            logger.info(
                f"Web processed: {len(result.web_structured_points)} points, "
                f"{len(result.web_raw_quotes)} quotes"
            )

            return result

        except Exception as e:
            # Handle any errors gracefully
            logger.error(f"Web worker error: {e}", exc_info=True)

            # Return empty result on error
            return WebResult(
                web_structured_points=[],
                web_raw_quotes=[]
            )

    def _parse_json_output(self, output: str) -> WebResult:
        """Parse JSON output from LLM.

        Args:
            output: LLM output text (should contain JSON)

        Returns:
            WebResult with parsed data

        Raises:
            ValueError: If JSON parsing fails
        """
        try:
            # Find JSON in output (handle cases with surrounding text)
            start = output.find('{')
            end = output.rfind('}')

            if start != -1 and end != -1 and end > start:
                json_str = output[start:end + 1]
                data = json.loads(json_str)

                # Extract fields
                structured_points = data.get('structured_points', [])
                raw_quotes = data.get('raw_quotes', [])

                # Ensure they are lists
                if not isinstance(structured_points, list):
                    structured_points = []
                if not isinstance(raw_quotes, list):
                    raw_quotes = []

                return WebResult(
                    web_structured_points=structured_points,
                    web_raw_quotes=raw_quotes
                )
            else:
                raise ValueError("No JSON object found in output")

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse Web JSON output: {e}")

            # Fallback: return empty lists
            return WebResult(
                web_structured_points=[],
                web_raw_quotes=[]
            )
