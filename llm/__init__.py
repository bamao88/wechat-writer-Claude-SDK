from llm.base import LLMProvider, ModelConfig
from llm.config import LLMConfig, ProviderConfig
from llm.registry import ProviderRegistry
from llm.providers import MiniMaxProvider, ClaudeProvider, OpenAIProvider

# Register provider classes
ProviderRegistry.register_class("minimax", MiniMaxProvider)
ProviderRegistry.register_class("claude", ClaudeProvider)
ProviderRegistry.register_class("openai", OpenAIProvider)

__all__ = [
    "LLMProvider",
    "ModelConfig",
    "LLMConfig",
    "ProviderConfig",
    "ProviderRegistry",
    "MiniMaxProvider",
    "ClaudeProvider",
    "OpenAIProvider",
]
