import hashlib
import json
from typing import Optional, Any

import structlog

from src.infra.redis_client import RedisClient
from src.infra.config import get_settings

logger = structlog.get_logger(__name__)


class CacheManager:
    """Manage prompt response caching"""

    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
        self.settings = get_settings()

    def _make_cache_key(self, prompt: str, model_tier: str, system_prompt: Optional[str] = None) -> str:
        """Generate cache key from prompt + tier"""
        key_content = f"{prompt}:{model_tier}:{system_prompt or ''}"
        return f"cache:{hashlib.sha256(key_content.encode()).hexdigest()}"

    def get(self, prompt: str, model_tier: str, system_prompt: Optional[str] = None) -> Optional[dict]:
        """Get cached response"""
        cache_key = self._make_cache_key(prompt, model_tier, system_prompt)
        cached = self.redis.get(cache_key)

        if cached:
            logger.info("cache_hit", cache_key=cache_key)
            return cached

        logger.debug("cache_miss", cache_key=cache_key)
        return None

    def set(self, prompt: str, model_tier: str, response: dict, system_prompt: Optional[str] = None) -> bool:
        """Cache a response"""
        cache_key = self._make_cache_key(prompt, model_tier, system_prompt)
        success = self.redis.set(
            cache_key,
            response,
            ttl=self.settings.cache_ttl_seconds,
        )

        if success:
            logger.info("cache_set", cache_key=cache_key, ttl=self.settings.cache_ttl_seconds)
        else:
            logger.warning("cache_set_failed", cache_key=cache_key)

        return success

    def clear_all(self) -> bool:
        """Clear all cache"""
        return self.redis.clear()

    def is_healthy(self) -> bool:
        """Check cache health"""
        return self.redis.is_healthy()
