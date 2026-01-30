from openai import AsyncOpenAI
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

from llm.base import LLMProvider, ModelConfig
from llm.config import ProviderConfig


class ClaudeProvider(LLMProvider):
    """Claude API provider implementation (supports third-party proxies with OpenAI-compatible format)."""

    def __init__(self, config: ModelConfig):
        self._config = config
        self._client = None
        self._model = None

    @classmethod
    def from_config(cls, config: ProviderConfig) -> "ClaudeProvider":
        """Create provider from configuration."""
        model_config = ModelConfig(
            name=f"Claude-{config.model}",
            provider="claude",
            model_id=config.model,
            api_key=config.api_key,
            base_url=config.base_url,
        )
        return cls(model_config)

    def create_model(self) -> OpenAIChatCompletionsModel:
        """Create Claude model instance via OpenAI-compatible API."""
        if self._model is None:
            self._client = AsyncOpenAI(
                api_key=self._config.api_key,
                base_url=self._config.base_url,
            )
            self._model = OpenAIChatCompletionsModel(
                model=self._config.model_id,
                openai_client=self._client,
            )
        return self._model

    @property
    def config(self) -> ModelConfig:
        return self._config

    @property
    def display_name(self) -> str:
        return f"Claude-{self._config.model_id}"


class MiniMaxProvider(LLMProvider):
    """MiniMax API provider implementation."""

    def __init__(self, config: ModelConfig):
        self._config = config
        self._client = None
        self._model = None

    @classmethod
    def from_config(cls, config: ProviderConfig) -> "MiniMaxProvider":
        """Create provider from configuration."""
        model_config = ModelConfig(
            name=f"MiniMax-{config.model}",
            provider="minimax",
            model_id=config.model,
            api_key=config.api_key,
            base_url=config.base_url,
        )
        return cls(model_config)

    def create_model(self) -> OpenAIChatCompletionsModel:
        """Create MiniMax model instance."""
        if self._model is None:
            self._client = AsyncOpenAI(
                api_key=self._config.api_key,
                base_url=self._config.base_url,
                default_headers={
                    "Authorization": f"Bearer {self._config.api_key}",
                },
            )
            self._model = OpenAIChatCompletionsModel(
                model=self._config.model_id,
                openai_client=self._client,
            )
        return self._model

    @property
    def config(self) -> ModelConfig:
        return self._config

    @property
    def display_name(self) -> str:
        return f"MiniMax-{self._config.model_id}"


class OpenAIProvider(LLMProvider):
    """OpenAI API provider implementation (supports third-party proxies)."""

    def __init__(self, config: ModelConfig):
        self._config = config
        self._client = None
        self._model = None

    @classmethod
    def from_config(cls, config: ProviderConfig) -> "OpenAIProvider":
        """Create provider from configuration."""
        model_config = ModelConfig(
            name=f"OpenAI-{config.model}",
            provider="openai",
            model_id=config.model,
            api_key=config.api_key,
            base_url=config.base_url,
        )
        return cls(model_config)

    def create_model(self) -> OpenAIChatCompletionsModel:
        """Create OpenAI model instance."""
        if self._model is None:
            self._client = AsyncOpenAI(
                api_key=self._config.api_key,
                base_url=self._config.base_url,
            )
            self._model = OpenAIChatCompletionsModel(
                model=self._config.model_id,
                openai_client=self._client,
            )
        return self._model

    @property
    def config(self) -> ModelConfig:
        return self._config

    @property
    def display_name(self) -> str:
        return f"OpenAI-{self._config.model_id}"
