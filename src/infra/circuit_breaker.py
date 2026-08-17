import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

import structlog

logger = structlog.get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes in half-open before closing
    timeout_seconds: int = 60  # Time before half-open retry


class CircuitBreaker:
    """Simple circuit breaker for provider reliability"""

    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None

    def record_success(self):
        """Record a successful operation"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._close()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

        logger.debug(
            "circuit_breaker_success",
            name=self.name,
            state=self.state.value,
            success_count=self.success_count,
        )

    def record_failure(self):
        """Record a failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self._open()
        elif self.state == CircuitState.HALF_OPEN:
            self._open()

        logger.warning(
            "circuit_breaker_failure",
            name=self.name,
            state=self.state.value,
            failure_count=self.failure_count,
        )

    def is_available(self) -> bool:
        """Check if circuit is available for requests"""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if self._should_try_recovery():
                self._half_open()
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return True
        return False

    def call(self, func: Callable, *args, **kwargs):
        """Execute function through circuit breaker"""
        if not self.is_available():
            raise Exception(f"Circuit breaker {self.name} is OPEN")

        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise

    def _open(self):
        """Transition to OPEN state"""
        self.state = CircuitState.OPEN
        self.success_count = 0
        logger.error(f"circuit_breaker_opened", name=self.name)

    def _half_open(self):
        """Transition to HALF_OPEN state"""
        self.state = CircuitState.HALF_OPEN
        self.failure_count = 0
        self.success_count = 0
        logger.info("circuit_breaker_half_open", name=self.name)

    def _close(self):
        """Transition to CLOSED state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        logger.info("circuit_breaker_closed", name=self.name)

    def _should_try_recovery(self) -> bool:
        """Check if enough time has passed to retry"""
        if not self.last_failure_time:
            return True
        return time.time() - self.last_failure_time >= self.config.timeout_seconds

    def get_status(self) -> dict:
        """Get circuit breaker status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "available": self.is_available(),
        }
