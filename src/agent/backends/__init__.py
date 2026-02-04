"""LLM backends: Anthropic (incl. MiniMax compat) and OpenAI."""
import os
from typing import TYPE_CHECKING

from src.agent.backends.anthropic_ import AnthropicBackend
from src.agent.backends.base import BackendResponse, LLMBackend, ToolCall, ToolDef
from src.agent.backends.openai_ import OpenAIBackend

if TYPE_CHECKING:
    from src.config.settings import Config


def get_model_name(provider: str) -> str:
    """Return the model name for the given provider (from env)."""
    p = (provider or "").strip().lower()
    if p == "openai":
        return (
            os.getenv("WECHAT_WRITER_OPENAI_MODEL")
            or os.getenv("OPENAI_MODEL")
            or "gpt-4o"
        )
    return (
        os.getenv("WECHAT_WRITER_ANTHROPIC_MODEL")
        or os.getenv("ANTHROPIC_MODEL")
        or "claude-haiku-4-5-20251001"
    )


def get_backend(provider: str) -> LLMBackend:
    """Create backend by provider name.

    - anthropic: Anthropic API (and MiniMax via Anthropic-compatible base_url/model).
    - openai: OpenAI API (and OpenAI-compatible endpoints).
    """
    p = (provider or "").strip().lower()
    if p == "openai":
        return OpenAIBackend()
    return AnthropicBackend()


def get_backend_from_env() -> LLMBackend:
    """Create backend from WECHAT_WRITER_LLM_PROVIDER (default: anthropic)."""
    provider = os.getenv("WECHAT_WRITER_LLM_PROVIDER") or os.getenv("LLM_PROVIDER") or "anthropic"
    return get_backend(provider)


__all__ = [
    "LLMBackend",
    "BackendResponse",
    "ToolCall",
    "ToolDef",
    "AnthropicBackend",
    "OpenAIBackend",
    "get_backend",
    "get_backend_from_env",
    "get_model_name",
]
