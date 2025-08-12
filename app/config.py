from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    broker: str = "paper"  # paper or alpaca

    # Alpaca
    alpaca_key_id: str | None = None
    alpaca_secret_key: str | None = None
    alpaca_base_url: str = "https://paper-api.alpaca.markets"

    # Data provider
    data_provider: str = "yahoo"

    # State for paper broker
    state_dir: Path = Path("/workspace/state")

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore", env_nested_delimiter="__")


def get_settings() -> AppSettings:
    settings = AppSettings()
    # Ensure state directory exists
    if settings.state_dir and not settings.state_dir.exists():
        settings.state_dir.mkdir(parents=True, exist_ok=True)
    return settings