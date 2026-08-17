from typing import Optional

import structlog
from openai import OpenAI, RateLimitError, APIConnectionError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .config import get_settings
from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig

logger = structlog.get_logger(__name__)


class OpenRouterProvider:
    """OpenRouter provider wrapper - unified API for all models"""

    def __init__(self):
        settings = get_settings()
        # OpenRouter uses OpenAI-compatible API
        self.client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        self.config = CircuitBreakerConfig(
            failure_threshold=settings.circuit_breaker_failure_threshold,
            success_threshold=settings.circuit_breaker_success_threshold,
            timeout_seconds=settings.circuit_breaker_timeout_seconds,
        )
        self.circuit_breaker = CircuitBreaker("openrouter", self.config)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError)),
    )
    def chat(self, model: str, messages: list, **kwargs) -> dict:
        """Call model via OpenRouter with retry logic"""
        if not self.circuit_breaker.is_available():
            raise Exception("OpenRouter circuit breaker is OPEN")

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs,
            )
            self.circuit_breaker.record_success()
            return {
                "content": response.choices[0].message.content,
                "stop_reason": response.choices[0].finish_reason,
                "usage": {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens,
                },
            }
        except (RateLimitError, APIConnectionError) as e:
            self.circuit_breaker.record_failure()
            logger.warning("openrouter_call_failed", error=str(e), model=model)
            raise
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error("openrouter_call_error", error=str(e), model=model)
            raise

    def is_healthy(self) -> bool:
        """Check provider health"""
        return self.circuit_breaker.is_available()


class ProviderRouter:
    """Route requests to appropriate model via OpenRouter"""

    def __init__(self):
        self.openrouter = OpenRouterProvider()

    def get_provider(self, model_tier: str) -> tuple:
        """Get provider and model name for tier"""
        settings = get_settings()

        if model_tier == "simple":
            config = settings.get_model_config("haiku")
            return self.openrouter, "anthropic/claude-3-haiku"
        elif model_tier == "medium":
            config = settings.get_model_config("sonnet")
            return self.openrouter, "anthropic/claude-sonnet-4"
        elif model_tier == "complex":
            config = settings.get_model_config("gpt4o")
            return self.openrouter, "openai/gpt-4o"
        else:
            # Default to medium if unknown
            return self.openrouter, "anthropic/claude-sonnet-4"

    def is_healthy(self) -> dict:
        """Check health of OpenRouter"""
        return {
            "openrouter": self.openrouter.is_healthy(),
        }
