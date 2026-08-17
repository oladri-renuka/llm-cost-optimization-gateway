"""
Seed realistic 7-day metrics for dashboard development.
Generates mock data for: requests, costs, cache hits, routing accuracy, failovers, quality scores.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)

# Pricing per tier
PRICING = {
    "simple": {"input": 0.25, "output": 1.25, "name": "Haiku"},
    "medium": {"input": 3.0, "output": 15.0, "name": "Sonnet"},
    "complex": {"input": 2.50, "output": 10.0, "name": "GPT-4o"},
}

# Sample prompts for caching
SAMPLE_PROMPTS = [
    "What is the capital of France?",
    "Explain how photosynthesis works",
    "Design a distributed cache architecture",
    "Write a Python function to sort an array",
    "What is machine learning?",
    "How do I deploy to Kubernetes?",
    "Compare Python vs Go",
    "Research quantum computing applications",
]

# Metrics storage (in-memory for demo)
METRICS_DATA = {
    "requests": [],
    "daily_stats": {},
    "cached_prompts": {},
    "failovers": [],
    "quality_scores": {},
}


def generate_request(timestamp: datetime, day_idx: int) -> dict:
    """Generate a single request record with realistic distribution"""
    # 70% simple, 20% medium, 10% complex (typical distribution)
    tier_rand = random.random()
    if tier_rand < 0.70:
        tier = "simple"
    elif tier_rand < 0.90:
        tier = "medium"
    else:
        tier = "complex"

    # Routing accuracy: 96% correct, 4% misrouted
    is_correct = random.random() < 0.96
    predicted_tier = tier if is_correct else random.choice(["simple", "medium", "complex"])

    # Cache hit: 15% of requests hit cache
    is_cache_hit = random.random() < 0.15

    # Token estimation (input + output)
    if tier == "simple":
        input_tokens = random.randint(20, 100)
        output_tokens = random.randint(10, 50)
    elif tier == "medium":
        input_tokens = random.randint(100, 300)
        output_tokens = random.randint(50, 150)
    else:
        input_tokens = random.randint(200, 500)
        output_tokens = random.randint(100, 300)

    # Calculate cost
    pricing = PRICING[tier]
    cost_usd = (
        (input_tokens / 1_000_000) * pricing["input"] +
        (output_tokens / 1_000_000) * pricing["output"]
    )

    # Baseline cost (always GPT-4o)
    gpt4o_pricing = PRICING["complex"]
    baseline_cost = (
        (input_tokens / 1_000_000) * gpt4o_pricing["input"] +
        (output_tokens / 1_000_000) * gpt4o_pricing["output"]
    )

    savings = baseline_cost - cost_usd

    # Failover: 2% of requests have failover
    has_failover = random.random() < 0.02

    # Random prompt for caching
    prompt = random.choice(SAMPLE_PROMPTS)

    return {
        "timestamp": timestamp.isoformat(),
        "day_idx": day_idx,
        "tier": tier,
        "predicted_tier": predicted_tier,
        "is_correct": is_correct,
        "cache_hit": is_cache_hit,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost_usd, 6),
        "baseline_cost": round(baseline_cost, 6),
        "savings": round(savings, 6),
        "failover": has_failover,
        "prompt": prompt,
        "latency_ms": random.randint(100, 3500),
        "quality_score": random.uniform(0.7, 1.0),  # 0-1 scale
    }


def aggregate_daily_stats(requests: list) -> dict:
    """Aggregate metrics by day"""
    daily = {}

    for req in requests:
        day_idx = req["day_idx"]
        if day_idx not in daily:
            daily[day_idx] = {
                "simple": {"count": 0, "cost": 0, "correct": 0},
                "medium": {"count": 0, "cost": 0, "correct": 0},
                "complex": {"count": 0, "cost": 0, "correct": 0},
                "cache_hits": 0,
                "failovers": 0,
                "total_savings": 0,
                "avg_quality": [],
            }

        tier = req["tier"]
        daily[day_idx][tier]["count"] += 1
        daily[day_idx][tier]["cost"] += req["cost_usd"]
        if req["is_correct"]:
            daily[day_idx][tier]["correct"] += 1

        if req["cache_hit"]:
            daily[day_idx]["cache_hits"] += 1

        if req["failover"]:
            daily[day_idx]["failovers"] += 1

        daily[day_idx]["total_savings"] += req["savings"]
        daily[day_idx]["avg_quality"].append(req["quality_score"])

    # Calculate averages
    for day_idx in daily:
        if daily[day_idx]["avg_quality"]:
            daily[day_idx]["avg_quality"] = round(
                sum(daily[day_idx]["avg_quality"]) / len(daily[day_idx]["avg_quality"]),
                2,
            )
        else:
            daily[day_idx]["avg_quality"] = 0.0

    return daily


def aggregate_cached_prompts(requests: list) -> dict:
    """Count cache hits per prompt"""
    cached = {}

    for req in requests:
        if req["cache_hit"]:
            prompt = req["prompt"]
            if prompt not in cached:
                cached[prompt] = 0
            cached[prompt] += 1

    # Sort by count, return top 5
    return dict(
        sorted(cached.items(), key=lambda x: x[1], reverse=True)[:5]
    )


def seed_metrics(num_days: int = 7, requests_per_day: int = 100) -> dict:
    """Generate 7 days of realistic metrics"""
    logger.info("seed_metrics_start", num_days=num_days, requests_per_day=requests_per_day)

    now = datetime.now()
    all_requests = []

    # Generate requests for each day
    for day_idx in range(num_days):
        target_date = now - timedelta(days=num_days - day_idx - 1)

        for _ in range(requests_per_day):
            # Spread requests throughout the day
            hour = random.randint(0, 23)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)

            timestamp = target_date.replace(hour=hour, minute=minute, second=second)
            request = generate_request(timestamp, day_idx)
            all_requests.append(request)

    # Aggregate stats
    daily_stats = aggregate_daily_stats(all_requests)
    cached_prompts = aggregate_cached_prompts(all_requests)

    # Calculate overall stats
    total_requests = len(all_requests)
    total_cost = sum(r["cost_usd"] for r in all_requests)
    total_baseline = sum(r["baseline_cost"] for r in all_requests)
    total_savings = total_baseline - total_cost
    total_cache_hits = sum(1 for r in all_requests if r["cache_hit"])
    total_failovers = sum(1 for r in all_requests if r["failover"])
    total_correct = sum(1 for r in all_requests if r["is_correct"])

    cache_hit_rate = (total_cache_hits / total_requests * 100) if total_requests > 0 else 0
    routing_accuracy = (total_correct / total_requests * 100) if total_requests > 0 else 0
    failover_rate = (total_failovers / total_requests * 100) if total_requests > 0 else 0
    savings_percentage = (total_savings / total_baseline * 100) if total_baseline > 0 else 0

    metrics = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "num_days": num_days,
            "total_requests": total_requests,
        },
        "summary": {
            "total_cost": round(total_cost, 2),
            "total_baseline": round(total_baseline, 2),
            "total_savings": round(total_savings, 2),
            "savings_percentage": round(savings_percentage, 1),
            "cache_hit_rate": round(cache_hit_rate, 1),
            "routing_accuracy": round(routing_accuracy, 1),
            "failover_rate": round(failover_rate, 1),
            "avg_quality": round(
                sum(r["quality_score"] for r in all_requests) / len(all_requests), 2
            ),
        },
        "daily": daily_stats,
        "cached_prompts": cached_prompts,
        "requests": all_requests,
    }

    logger.info(
        "seed_metrics_complete",
        total_requests=total_requests,
        total_savings=round(total_savings, 2),
        routing_accuracy=round(routing_accuracy, 1),
    )

    return metrics


def save_metrics(metrics: dict, output_path: str = "mock_metrics.json"):
    """Save metrics to file"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump(metrics, f, indent=2)

    logger.info("metrics_saved", path=str(path))


if __name__ == "__main__":
    # Generate 7 days of metrics with 100 requests per day
    metrics = seed_metrics(num_days=7, requests_per_day=100)
    save_metrics(metrics)

    print("\n" + "=" * 70)
    print("METRICS SEEDING COMPLETE")
    print("=" * 70)
    print(f"Generated {metrics['metadata']['total_requests']} requests over {metrics['metadata']['num_days']} days")
    print(f"\nSummary:")
    print(f"  Total Cost:        ${metrics['summary']['total_cost']:.2f}")
    print(f"  Total Savings:     ${metrics['summary']['total_savings']:.2f}")
    print(f"  Savings Rate:      {metrics['summary']['savings_percentage']:.1f}%")
    print(f"  Cache Hit Rate:    {metrics['summary']['cache_hit_rate']:.1f}%")
    print(f"  Routing Accuracy:  {metrics['summary']['routing_accuracy']:.1f}%")
    print(f"  Failover Rate:     {metrics['summary']['failover_rate']:.1f}%")
    print(f"  Avg Quality Score: {metrics['summary']['avg_quality']:.2f}")
    print("=" * 70 + "\n")
