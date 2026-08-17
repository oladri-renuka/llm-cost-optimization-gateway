import json
import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.infra.config import get_settings
from src.infra.redis_client import RedisClient

logger = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add request ID to every request"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with structured logging"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        request_id = getattr(request.state, "request_id", "unknown")

        # Parse body if available
        body = {}
        try:
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.json()
        except Exception:
            pass

        logger.info(
            "request_started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else "unknown",
        )

        response = await call_next(request)

        latency_ms = (time.time() - start_time) * 1000
        logger.info(
            "request_completed",
            request_id=request_id,
            status_code=response.status_code,
            latency_ms=latency_ms,
        )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limit requests per user/IP"""

    def __init__(self, app, redis_client: RedisClient):
        super().__init__(app)
        self.redis = redis_client
        self.settings = get_settings()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get client identifier (IP or API key)
        client_id = request.client.host if request.client else "unknown"

        # Check rate limit
        rate_limit_key = f"rate_limit:{client_id}"
        current = self.redis.increment(rate_limit_key, 1)

        if current == 1:
            # Set expiry on first request
            self.redis.client.expire(rate_limit_key, 60)

        if current > self.settings.max_requests_per_minute:
            logger.warning("rate_limit_exceeded", client_id=client_id, current=current)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.settings.max_requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.settings.max_requests_per_minute - current)
        )

        return response
