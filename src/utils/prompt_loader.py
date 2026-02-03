"""Prompt loading utilities."""
import os
from pathlib import Path
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class PromptError(Exception):
    """Raised when prompt loading fails."""
    pass


def load_prompt(prompt_name: str, prompts_dir: Optional[str] = None) -> str:
    """Load a prompt from the prompts directory.

    Args:
        prompt_name: Name of prompt file (e.g., "prompt_run.txt")
        prompts_dir: Optional custom prompts directory path.
                     Defaults to "prompts/" relative to project root.

    Returns:
        Prompt content as string.

    Raises:
        PromptError: If prompt file not found or cannot be read.
    """
    if prompts_dir is None:
        # Default: prompts/ relative to project root
        project_root = Path(__file__).parent.parent.parent
        prompts_dir = project_root / "prompts"
    else:
        prompts_dir = Path(prompts_dir)

    prompt_path = prompts_dir / prompt_name

    if not prompt_path.exists():
        raise PromptError(f"Prompt文件不存在: {prompt_path}")

    try:
        content = prompt_path.read_text(encoding="utf-8")
        logger.debug(f"已加载prompt: {prompt_name} ({len(content)} 字符)")
        return content
    except Exception as e:
        raise PromptError(f"无法读取prompt文件 {prompt_path}: {e}")
