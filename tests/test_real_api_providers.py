"""Real API integration tests for all LLM providers.

Tests verify that all three providers (MiniMax, OpenAI, Claude) work correctly
with actual API calls using credentials from the environment.
"""

import os
import pytest
import asyncio
from typing import Optional

from llm import ProviderRegistry


def check_provider_configured(provider_id: str) -> bool:
    """Check if a provider has credentials configured.

    Args:
        provider_id: The provider identifier (minimax, openai, claude)

    Returns:
        True if the provider has an API key configured, False otherwise
    """
    env_vars = {
        "minimax": "MINIMAX_API_KEY",
        "openai": "OPENAI_API_KEY",
        "claude": "CLAUDE_API_KEY",
    }
    env_var = env_vars.get(provider_id)
    if not env_var:
        return False
    return bool(os.getenv(env_var))


def get_skip_reason(provider_id: str) -> str:
    """Get the skip reason message for a provider.

    Args:
        provider_id: The provider identifier

    Returns:
        Skip reason message
    """
    env_vars = {
        "minimax": "MINIMAX_API_KEY",
        "openai": "OPENAI_API_KEY",
        "claude": "CLAUDE_API_KEY",
    }
    env_var = env_vars.get(provider_id, f"{provider_id.upper()}_API_KEY")
    return f"{env_var} not set - skipping real API test"


class TestProviderFromEnv:
    """Test that providers can be loaded from environment configuration."""

    @pytest.mark.skipif(
        not check_provider_configured("minimax"),
        reason=get_skip_reason("minimax")
    )
    def test_minimax_from_env(self):
        """Verify MiniMax provider loads from environment."""
        registry = ProviderRegistry.from_env()
        assert "minimax" in registry.list_available()

        provider = registry.get("minimax")
        assert provider is not None
        assert provider.config.provider == "minimax"
        assert provider.config.api_key is not None
        assert len(provider.config.api_key) > 0

    @pytest.mark.skipif(
        not check_provider_configured("openai"),
        reason=get_skip_reason("openai")
    )
    def test_openai_from_env(self):
        """Verify OpenAI provider loads from environment."""
        registry = ProviderRegistry.from_env()
        assert "openai" in registry.list_available()

        provider = registry.get("openai")
        assert provider is not None
        assert provider.config.provider == "openai"
        assert provider.config.api_key is not None
        assert len(provider.config.api_key) > 0

    @pytest.mark.skipif(
        not check_provider_configured("claude"),
        reason=get_skip_reason("claude")
    )
    def test_claude_from_env(self):
        """Verify Claude provider loads from environment."""
        registry = ProviderRegistry.from_env()
        assert "claude" in registry.list_available()

        provider = registry.get("claude")
        assert provider is not None
        assert provider.config.provider == "claude"
        assert provider.config.api_key is not None
        assert len(provider.config.api_key) > 0


class TestProviderModelCreation:
    """Test that providers can create model instances."""

    @pytest.mark.skipif(
        not check_provider_configured("minimax"),
        reason=get_skip_reason("minimax")
    )
    def test_minimax_create_model(self):
        """Verify MiniMax creates model instance."""
        registry = ProviderRegistry.from_env()
        provider = registry.get("minimax")
        assert provider is not None

        model = provider.create_model()
        assert model is not None
        assert hasattr(model, 'model')
        assert model.model == provider.config.model_id

    @pytest.mark.skipif(
        not check_provider_configured("openai"),
        reason=get_skip_reason("openai")
    )
    def test_openai_create_model(self):
        """Verify OpenAI creates model instance."""
        registry = ProviderRegistry.from_env()
        provider = registry.get("openai")
        assert provider is not None

        model = provider.create_model()
        assert model is not None
        assert hasattr(model, 'model')
        assert model.model == provider.config.model_id

    @pytest.mark.skipif(
        not check_provider_configured("claude"),
        reason=get_skip_reason("claude")
    )
    def test_claude_create_model(self):
        """Verify Claude creates model instance."""
        registry = ProviderRegistry.from_env()
        provider = registry.get("claude")
        assert provider is not None

        model = provider.create_model()
        assert model is not None
        assert hasattr(model, 'model')
        assert model.model == provider.config.model_id


@pytest.mark.integration
class TestRealAPI:
    """Real API integration tests requiring credentials."""

    @pytest.mark.skipif(
        not check_provider_configured("minimax"),
        reason=get_skip_reason("minimax")
    )
    @pytest.mark.asyncio
    async def test_minimax_real_api_call(self):
        """Real API call to MiniMax."""
        from agents import Agent, Runner

        registry = ProviderRegistry.from_env()
        provider = registry.get("minimax")
        assert provider is not None

        model = provider.create_model()

        agent = Agent(
            name="TestMiniMax",
            instructions="You are a helpful assistant.",
            model=model,
        )

        result = await Runner.run(
            agent,
            "Say 'Hello from MiniMax' and nothing else."
        )

        assert result is not None
        assert result.final_output is not None
        assert isinstance(result.final_output, str)
        assert len(result.final_output) > 0
        print(f"MiniMax response: {result.final_output}")

    @pytest.mark.skipif(
        not check_provider_configured("openai"),
        reason=get_skip_reason("openai")
    )
    @pytest.mark.asyncio
    async def test_openai_real_api_call(self):
        """Real API call to OpenAI."""
        from agents import Agent, Runner

        registry = ProviderRegistry.from_env()
        provider = registry.get("openai")
        assert provider is not None

        model = provider.create_model()

        agent = Agent(
            name="TestOpenAI",
            instructions="You are a helpful assistant.",
            model=model,
        )

        result = await Runner.run(
            agent,
            "Say 'Hello from OpenAI' and nothing else."
        )

        assert result is not None
        assert result.final_output is not None
        assert isinstance(result.final_output, str)
        assert len(result.final_output) > 0
        print(f"OpenAI response: {result.final_output}")

    @pytest.mark.skipif(
        not check_provider_configured("claude"),
        reason=get_skip_reason("claude")
    )
    @pytest.mark.asyncio
    async def test_claude_real_api_call(self):
        """Real API call to Claude."""
        from agents import Agent, Runner

        registry = ProviderRegistry.from_env()
        provider = registry.get("claude")
        assert provider is not None

        model = provider.create_model()

        agent = Agent(
            name="TestClaude",
            instructions="You are a helpful assistant.",
            model=model,
        )

        result = await Runner.run(
            agent,
            "Say 'Hello from Claude' and nothing else."
        )

        assert result is not None
        assert result.final_output is not None
        assert isinstance(result.final_output, str)
        assert len(result.final_output) > 0
        print(f"Claude response: {result.final_output}")
