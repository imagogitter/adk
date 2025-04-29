"""Centralized configuration management for the ADK Trading Platform."""

import os
from decimal import Decimal
from typing import Any, Dict, Optional, Union

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_env(key: str, default: Any = None, required: bool = False) -> Optional[str]:
    """Get environment variable with optional default and required flag."""
    value = os.getenv(key, default)
    if required and value is None:
        raise ValueError(f"Required environment variable {key} is not set")
    return value


def get_env_decimal(key: str, default: Union[str, float, int] = None) -> Decimal:
    """Get environment variable as Decimal."""
    value = get_env(key, default)
    return Decimal(str(value)) if value is not None else None


def get_env_int(key: str, default: Optional[int] = None) -> Optional[int]:
    """Get environment variable as integer."""
    value = get_env(key, default)
    return int(value) if value is not None else None


def get_env_bool(key: str, default: Optional[bool] = False) -> bool:
    """Get environment variable as boolean."""
    value = get_env(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "yes", "1", "y")
    return bool(value)


def get_config() -> Dict[str, Any]:
    """Get all configuration as a dictionary."""
    return {
        "influxdb": {
            "url": get_env("INFLUXDB_URL", "http://localhost:8086"),
            "token": get_env("INFLUXDB_TOKEN", required=True),
            "org": get_env("INFLUXDB_ORG", required=True),
            "bucket": get_env("INFLUXDB_BUCKET", "trading_data"),
        },
        "exchange": {
            "id": get_env("EXCHANGE_ID", "binance"),
            "api_key": get_env("EXCHANGE_API_KEY"),
            "api_secret": get_env("EXCHANGE_API_SECRET"),
        },
        "trading": {
            "position_size": get_env_decimal("POSITION_SIZE", "0.01"),
            "max_positions": get_env_int("MAX_POSITIONS", 2),
            "initial_capital": get_env_decimal("INITIAL_CAPITAL", "10000"),
        },
        "monitoring": {
            "prometheus_port": get_env_int("PROMETHEUS_PORT", 8000),
            "slack_token": get_env("SLACK_TOKEN"),
        },
        "web_ui": {
            "port": get_env_int("WEB_UI_PORT", 8050),
        },
    }
