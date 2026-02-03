"""Tests for configuration loading."""
import os
import pytest
from src.config.settings import load_config, Config, ConfigError


class TestLoadConfig:
    """Test load_config function."""

    def test_loads_notebook_id_from_env(self, monkeypatch):
        """Config loads NOTEBOOK_ID from environment."""
        monkeypatch.setenv("NOTEBOOK_ID", "test-notebook-123")
        monkeypatch.setenv("NOTEBOOK_URL", "https://example.com")
        config = load_config()
        assert config.notebook_id == "test-notebook-123"

    def test_loads_notebook_url_from_env(self, monkeypatch):
        """Config loads NOTEBOOK_URL from environment."""
        monkeypatch.setenv("NOTEBOOK_ID", "test-id")
        monkeypatch.setenv("NOTEBOOK_URL", "https://notebooklm.google.com/nb/123")
        config = load_config()
        assert config.notebook_url == "https://notebooklm.google.com/nb/123"

    def test_loads_retry_count_with_default(self, monkeypatch):
        """Config loads retry count with default of 3."""
        monkeypatch.setenv("NOTEBOOK_ID", "id")
        monkeypatch.setenv("NOTEBOOK_URL", "url")
        # Not setting NOTEBOOKLM_RETRY_COUNT
        config = load_config()
        assert config.retry_count == 3

    def test_loads_retry_count_from_env(self, monkeypatch):
        """Config loads custom retry count from env."""
        monkeypatch.setenv("NOTEBOOK_ID", "id")
        monkeypatch.setenv("NOTEBOOK_URL", "url")
        monkeypatch.setenv("NOTEBOOKLM_RETRY_COUNT", "5")
        config = load_config()
        assert config.retry_count == 5

    def test_loads_retry_delay_with_default(self, monkeypatch):
        """Config loads retry delay with default of 2 seconds."""
        monkeypatch.setenv("NOTEBOOK_ID", "id")
        monkeypatch.setenv("NOTEBOOK_URL", "url")
        config = load_config()
        assert config.retry_delay_sec == 2

    def test_loads_timeout_with_default(self, monkeypatch):
        """Config loads timeout with default of 120 seconds."""
        monkeypatch.setenv("NOTEBOOK_ID", "id")
        monkeypatch.setenv("NOTEBOOK_URL", "url")
        config = load_config()
        assert config.timeout_sec == 120

    def test_loads_log_level_with_default(self, monkeypatch):
        """Config loads log level with default INFO."""
        monkeypatch.setenv("NOTEBOOK_ID", "id")
        monkeypatch.setenv("NOTEBOOK_URL", "url")
        config = load_config()
        assert config.log_level == "INFO"

    def test_loads_log_level_from_env(self, monkeypatch):
        """Config loads custom log level from env."""
        monkeypatch.setenv("NOTEBOOK_ID", "id")
        monkeypatch.setenv("NOTEBOOK_URL", "url")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        config = load_config()
        assert config.log_level == "DEBUG"

    def test_missing_notebook_id_raises_error(self, monkeypatch):
        """Missing NOTEBOOK_ID raises ConfigError."""
        # Clear all NotebookLM env vars to ensure clean state
        monkeypatch.delenv("NOTEBOOK_ID", raising=False)
        monkeypatch.delenv("NOTEBOOK_URL", raising=False)
        monkeypatch.delenv("NOTEBOOKLM_RETRY_COUNT", raising=False)
        monkeypatch.delenv("NOTEBOOKLM_RETRY_DELAY_SEC", raising=False)
        monkeypatch.delenv("NOTEBOOKLM_TIMEOUT_SEC", raising=False)
        monkeypatch.delenv("LOG_LEVEL", raising=False)

        # Mock load_dotenv to do nothing
        monkeypatch.setattr("src.config.settings.load_dotenv", lambda: None)

        # Set only NOTEBOOK_URL
        monkeypatch.setenv("NOTEBOOK_URL", "url")
        with pytest.raises(ConfigError) as exc_info:
            load_config()
        assert "NOTEBOOK_ID" in str(exc_info.value)

    def test_missing_notebook_url_raises_error(self, monkeypatch):
        """Missing NOTEBOOK_URL raises ConfigError."""
        # Clear all NotebookLM env vars to ensure clean state
        monkeypatch.delenv("NOTEBOOK_ID", raising=False)
        monkeypatch.delenv("NOTEBOOK_URL", raising=False)
        monkeypatch.delenv("NOTEBOOKLM_RETRY_COUNT", raising=False)
        monkeypatch.delenv("NOTEBOOKLM_RETRY_DELAY_SEC", raising=False)
        monkeypatch.delenv("NOTEBOOKLM_TIMEOUT_SEC", raising=False)
        monkeypatch.delenv("LOG_LEVEL", raising=False)

        # Mock load_dotenv to do nothing
        monkeypatch.setattr("src.config.settings.load_dotenv", lambda: None)

        # Set only NOTEBOOK_ID
        monkeypatch.setenv("NOTEBOOK_ID", "id")
        with pytest.raises(ConfigError) as exc_info:
            load_config()
        assert "NOTEBOOK_URL" in str(exc_info.value)


class TestConfig:
    """Test Config dataclass."""

    def test_config_is_immutable_like(self):
        """Config attributes are accessible."""
        config = Config(
            notebook_id="id",
            notebook_url="url",
            retry_count=3,
            retry_delay_sec=2,
            timeout_sec=120,
            log_level="INFO"
        )
        assert config.notebook_id == "id"
        assert config.timeout_sec == 120
