"""Configuration loading from environment variables."""
from dataclasses import dataclass
from typing import Optional
import os

from dotenv import load_dotenv


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


@dataclass
class Config:
    """Application configuration."""
    notebook_id: str
    notebook_url: str
    retry_count: int
    retry_delay_sec: int
    timeout_sec: int
    log_level: str


def load_config() -> Config:
    """Load configuration from environment variables.

    Loads .env file if present, then reads required and optional
    environment variables.

    Returns:
        Config object with all settings.

    Raises:
        ConfigError: If required environment variables are missing.
    """
    load_dotenv()

    # Required variables
    notebook_id = os.getenv("NOTEBOOK_ID")
    if not notebook_id:
        raise ConfigError("缺少必需的环境变量: NOTEBOOK_ID，请在 .env 文件中配置")

    notebook_url = os.getenv("NOTEBOOK_URL")
    if not notebook_url:
        raise ConfigError("缺少必需的环境变量: NOTEBOOK_URL，请在 .env 文件中配置")

    # Optional variables with defaults
    retry_count = int(os.getenv("NOTEBOOKLM_RETRY_COUNT", "3"))
    retry_delay_sec = int(os.getenv("NOTEBOOKLM_RETRY_DELAY_SEC", "2"))
    timeout_sec = int(os.getenv("NOTEBOOKLM_TIMEOUT_SEC", "120"))
    log_level = os.getenv("LOG_LEVEL", "INFO")

    return Config(
        notebook_id=notebook_id,
        notebook_url=notebook_url,
        retry_count=retry_count,
        retry_delay_sec=retry_delay_sec,
        timeout_sec=timeout_sec,
        log_level=log_level
    )
