"""Writer Worker for hub-spoke architecture (stylized writing)."""
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.agent.hub_spoke.state import State
from src.utils.logger import get_logger
from src.utils.prompt_loader import load_prompt

if TYPE_CHECKING:
    from src.agent.backends.base import LLMBackend
    from src.output.tracer import OutputTracer

logger = get_logger(__name__)

MAX_TOKENS = 4000


@dataclass
class WriterResult:
    """Result from Writer worker."""
    draft: str


class WriterWorker:
    """Writer worker for stylized article writing.

    Inputs: outline + raw_voice_clips + web_raw_quotes + critic_feedback (optional)
    Output: Draft article (≥800 chars)
    """

    def __init__(self):
        """Initialize Writer worker."""
        pass

    def run(
        self,
        state: State,
        backend: 'LLMBackend',
        tracer: 'OutputTracer'
    ) -> WriterResult:
        """Execute Writer to generate draft article.

        Args:
            state: Current State (reads outline, raw_voice_clips, web_raw_quotes, critic_feedback, iteration_count)
            backend: LLM backend
            tracer: OutputTracer

        Returns:
            WriterResult with draft
        """
        try:
            # Load base prompt
            system_prompt = load_prompt("writer.txt")

            # Add rewrite feedback if this is a rewrite iteration
            if state.iteration_count > 0 and state.critic_feedback:
                rewrite_section = f"""

**重要**：这是第{state.iteration_count + 1}轮写作，上一轮审稿意见如下：

{state.critic_feedback}

**修改要求**：
- 针对上述问题进行定向修改
- 其余部分保持原有风格，不要大改
- 确保修改后满足质量标准（字数≥800，结构完整，论点齐全）
"""
                system_prompt += rewrite_section

            # Build user message
            user_parts = [f"选题：{state.topic}"]

            if state.outline:
                user_parts.append(f"\n**大纲**：\n{state.outline}")

            if state.raw_voice_clips:
                clips_text = "\n".join(f'- "{c}"' for c in state.raw_voice_clips)
                user_parts.append(f"\n**用户语气参考（原话片段）**：\n{clips_text}")

            if state.web_raw_quotes:
                quotes_text = "\n".join(f'- {q}' for q in state.web_raw_quotes)
                user_parts.append(f"\n**权威引用素材（全网调研）**：\n{quotes_text}")

            instruction = "\n请按照大纲撰写文章"
            if state.raw_voice_clips:
                instruction += "，使用用户语气参考中的表达风格"
            if state.web_raw_quotes:
                instruction += "，可适当引用全网调研素材以增强权威性"
            instruction += "。"
            user_parts.append(instruction)

            user_message = "".join(user_parts)

            messages = [{"role": "user", "content": user_message}]

            tracer.append_agent_input("Writer", system_prompt, messages)

            response = backend.create(
                system=system_prompt,
                messages=messages,
                tools=[],
                max_tokens=MAX_TOKENS
            )

            draft = response.content_text

            tracer.append_agent_output(draft, "Writer")

            logger.info(
                f"Writer generated draft ({len(draft)} chars), "
                f"iteration={state.iteration_count}"
            )

            return WriterResult(draft=draft)

        except Exception as e:
            logger.error(f"Writer error: {e}", exc_info=True)
            return WriterResult(draft="")
