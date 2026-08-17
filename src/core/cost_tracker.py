from dataclasses import dataclass
from typing import Optional

import structlog

from src.infra.config import get_settings
from src.infra.redis_client import RedisClient

logger = structlog.get_logger(__name__)


@dataclass
class CostBreakdown:
    """Cost breakdown for a request"""
    model_tier: str
    model_name: str
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    baseline_cost: float  # GPT-4o cost
    savings: float  # baseline - total
    savings_percentage: float  # (savings / baseline) * 100


class CostTracker:
    """Track and calculate costs for requests"""

    def __init__(self, redis_client: Optional[RedisClient] = None):
        self.settings = get_settings()
        self.redis = redis_client

    def calculate_cost(
        self,
        model_tier: str,
        input_tokens: int,
        output_tokens: int,
    ) -> CostBreakdown:
        """Calculate cost for a request"""
        # Get model pricing
        model_config = self.settings.get_model_config(model_tier)
        if not model_config:
            raise ValueError(f"Unknown model tier: {model_tier}")

        input_cost = (input_tokens / 1_000_000) * model_config["input_cost"]
        output_cost = (output_tokens / 1_000_000) * model_config["output_cost"]
        total_cost = input_cost + output_cost

        # Calculate baseline (GPT-4o)
        baseline_config = self.settings.get_model_config("gpt4o")
        baseline_input_cost = (input_tokens / 1_000_000) * baseline_config["input_cost"]
        baseline_output_cost = (output_tokens / 1_000_000) * baseline_config["output_cost"]
        baseline_cost = baseline_input_cost + baseline_output_cost

        savings = baseline_cost - total_cost
        savings_percentage = (savings / baseline_cost * 100) if baseline_cost > 0 else 0

        breakdown = CostBreakdown(
            model_tier=model_tier,
            model_name=model_config["name"],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            baseline_cost=baseline_cost,
            savings=savings,
            savings_percentage=savings_percentage,
        )

        logger.info(
            "cost_calculated",
            model_tier=model_tier,
            total_cost=total_cost,
            savings=savings,
            savings_percentage=savings_percentage,
        )

        return breakdown

    def record_cost(self, breakdown: CostBreakdown) -> bool:
        """Record cost in Redis for metrics"""
        if not self.redis:
            return False

        try:
            # Increment counters
            self.redis.increment(f"cost:total:{breakdown.model_tier}", int(breakdown.total_cost * 1_000_000))
            self.redis.increment(f"cost:baseline", int(breakdown.baseline_cost * 1_000_000))
            self.redis.increment(f"cost:savings", int(breakdown.savings * 1_000_000))
            self.redis.increment(f"requests:count:{breakdown.model_tier}")

            logger.debug("cost_recorded", model_tier=breakdown.model_tier)
            return True
        except Exception as e:
            logger.warning("cost_recording_failed", error=str(e))
            return False

    def get_daily_stats(self) -> dict:
        """Get daily cost statistics"""
        if not self.redis:
            return {}

        try:
            total_cost = self.redis.get("cost:total") or 0
            baseline_cost = self.redis.get("cost:baseline") or 0
            savings = self.redis.get("cost:savings") or 0
            request_count = self.redis.get("requests:count") or 0

            return {
                "total_cost": total_cost / 1_000_000,  # Convert back to dollars
                "baseline_cost": baseline_cost / 1_000_000,
                "savings": savings / 1_000_000,
                "request_count": request_count,
            }
        except Exception as e:
            logger.warning("stats_retrieval_failed", error=str(e))
            return {}
