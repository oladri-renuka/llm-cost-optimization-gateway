import json
import logging
from typing import Any, Optional

import redis
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


class RedisClient:
    """Redis wrapper with exponential backoff retries"""

    def __init__(self, url: str = "redis://localhost:6379"):
        self.url = url
        self.client = None
        self._connect()

    def _connect(self):
        """Connect to Redis with retry logic"""
        try:
            self.client = redis.from_url(self.url, decode_responses=True)
            self.client.ping()
            logger.info("redis_connected", url=self.url)
        except Exception as e:
            logger.error("redis_connection_failed", url=self.url, error=str(e))
            self.client = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
    )
    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis with retry"""
        if not self.client:
            return None
        try:
            value = self.client.get(key)
            if value:
                logger.debug("cache_hit", key=key)
                return json.loads(value)
            else:
                logger.debug("cache_miss", key=key)
                return None
        except redis.ConnectionError as e:
            logger.warning("redis_get_failed", key=key, error=str(e))
            return None
        except json.JSONDecodeError as e:
            logger.error("cache_decode_error", key=key, error=str(e))
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
    )
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in Redis with TTL and retry"""
        if not self.client:
            return False
        try:
            serialized = json.dumps(value)
            self.client.setex(key, ttl, serialized)
            logger.debug("cache_set", key=key, ttl=ttl)
            return True
        except redis.ConnectionError as e:
            logger.warning("redis_set_failed", key=key, error=str(e))
            return False
        except json.JSONEncodeError as e:
            logger.error("cache_encode_error", key=key, error=str(e))
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
    )
    def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if not self.client:
            return False
        try:
            self.client.delete(key)
            logger.debug("cache_delete", key=key)
            return True
        except redis.ConnectionError as e:
            logger.warning("redis_delete_failed", key=key, error=str(e))
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
    )
    def clear(self) -> bool:
        """Clear all keys from Redis"""
        if not self.client:
            return False
        try:
            self.client.flushdb()
            logger.info("cache_cleared")
            return True
        except redis.ConnectionError as e:
            logger.warning("redis_clear_failed", error=str(e))
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
    )
    def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter in Redis"""
        if not self.client:
            return 0
        try:
            value = self.client.incr(key, amount)
            logger.debug("counter_increment", key=key, value=value)
            return value
        except redis.ConnectionError as e:
            logger.warning("redis_increment_failed", key=key, error=str(e))
            return 0

    def is_healthy(self) -> bool:
        """Check Redis health"""
        if not self.client:
            return False
        try:
            self.client.ping()
            return True
        except Exception:
            return False
