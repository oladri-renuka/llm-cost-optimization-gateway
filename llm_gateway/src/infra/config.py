import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Load config from .env and settings.yaml"""

    # API
    log_level: str = "INFO"
    environment: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # OpenRouter (unified provider)
    openrouter_api_key: str

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Gateway
    cache_ttl_seconds: int = 3600
    router_timeout_ms: int = 5000
    inference_timeout_ms: int = 30000
    max_retries: int = 3
    max_requests_per_minute: int = 100

    # Pricing (per 1M tokens) - OpenRouter rates
    haiku_input_cost: float = 0.25
    haiku_output_cost: float = 1.25
    sonnet_input_cost: float = 3.0
    sonnet_output_cost: float = 15.0
    gpt4o_input_cost: float = 2.50
    gpt4o_output_cost: float = 10.0

    # Circuit Breaker
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_success_threshold: int = 2
    circuit_breaker_timeout_seconds: int = 60

    # Guardrails
    enable_prompt_injection_detection: bool = True
    enable_toxicity_filter: bool = True
    enable_pii_redaction: bool = True
    max_prompt_length_tokens: int = 8000

    # Dashboard
    dashboard_port: int = 7860
    mock_mode: bool = False

    # Monitoring
    prometheus_multiprocess_dir: Optional[str] = None
    metrics_retention_days: int = 7

    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_model_config(self, model_name: str) -> dict:
        """Get config for a specific model or tier"""
        # Map tier names to model names
        tier_map = {
            "simple": "haiku",
            "medium": "sonnet",
            "complex": "gpt4o",
        }
        # Use the mapped name if it's a tier, otherwise use as-is
        actual_model = tier_map.get(model_name, model_name)

        models = {
            "haiku": {
                "name": "anthropic/claude-3-haiku",
                "input_cost": self.haiku_input_cost,
                "output_cost": self.haiku_output_cost,
            },
            "sonnet": {
                "name": "anthropic/claude-sonnet-4",
                "input_cost": self.sonnet_input_cost,
                "output_cost": self.sonnet_output_cost,
            },
            "gpt4o": {
                "name": "openai/gpt-4o",
                "input_cost": self.gpt4o_input_cost,
                "output_cost": self.gpt4o_output_cost,
            },
        }
        return models.get(actual_model, {})


class YAMLConfig:
    """Load settings.yaml for advanced configuration"""

    def __init__(self, path: str = "config/settings.yaml"):
        self.path = Path(path)
        self.data = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        with open(self.path) as f:
            return yaml.safe_load(f) or {}

    def get(self, key: str, default=None):
        keys = key.split(".")
        value = self.data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


@lru_cache(maxsize=1)
def get_yaml_config() -> YAMLConfig:
    """Get cached YAML config"""
    return YAMLConfig()
