"""
Base settings module for the SEO AI Agent configuration.

Provides common utilities and base settings used across all configuration modules.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    """Base configuration class for all settings modules."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


def get_settings() -> "Settings":
    """
    Factory function to create Settings instance.
    
    Use this instead of the module-level singleton to ensure
    fresh configuration on each call when needed.
    """
    from config.settings import Settings
    return Settings()