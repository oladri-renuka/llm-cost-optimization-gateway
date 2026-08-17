#!/usr/bin/env python
"""
Cost-savings benchmark script.
Runs 500 prompts through gateway and calculates savings vs. GPT-4o baseline.
"""

import sys
import time
import json
from typing import List
import structlog
import httpx

logger = structlog.get_logger(__name__)


# Sample prompts dataset (in production, load from ShareGPT or similar)
SAMPLE_PROMPTS = [
    "What is 2+2?",
    "How do I make coffee?",
    "List the capitals of Europe",
    "Explain photosynthesis",
    "Write a Python function to sort arrays",
    "Compare Python vs Go",
    "What are the best practices for REST APIs?",
    "Design a microservices architecture for e-commerce",
    "Analyze the impact of quantum computing on cryptography",
    "Solve a novel problem in distributed systems",
] * 50  # Repeat to get to ~500 prompts


class BenchmarkRunner:
    def __init__(self, gateway_url: str = "http://localhost:8000"):
        self.gateway_url = gateway_url
        self.client = httpx.Client(timeout=30)

    def run_benchmark(self, prompts: List[str], num_prompts: int = 500) -> dict:
        """Run benchmark and calculate savings"""
        logger.info("benchmark_started", num_prompts=num_prompts)

        prompts = prompts[:num_prompts]
        total_cost = 0.0
        baseline_cost = 0.0
        failed_requests = 0

        for i, prompt in enumerate(prompts):
            try:
                start = time.time()
                response = self.client.post(
                    f"{self.gateway_url}/v1/chat/completions",
                    json={
                        "model": "gpt-4o",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 100,
                    },
                )
                elapsed = time.time() - start

                if response.status_code == 200:
                    data = response.json()

                    # Parse costs from response headers (in real implementation)
                    # For now, we'll calculate from usage
                    usage = data.get("usage", {})
                    tokens_in = usage.get("prompt_tokens", 0)
                    tokens_out = usage.get("completion_tokens", 0)

                    # Estimate costs (based on Haiku/GPT-4o pricing)
                    model = data.get("model", "")
                    if "haiku" in model.lower():
                        request_cost = (tokens_in / 1_000_000 * 0.80) + (
                            tokens_out / 1_000_000 * 4.0
                        )
                    else:
                        request_cost = (tokens_in / 1_000_000 * 5.0) + (
                            tokens_out / 1_000_000 * 15.0
                        )

                    baseline = (tokens_in / 1_000_000 * 5.0) + (
                        tokens_out / 1_000_000 * 15.0
                    )

                    total_cost += request_cost
                    baseline_cost += baseline

                    if (i + 1) % 50 == 0:
                        logger.info(
                            "benchmark_progress",
                            completed=i + 1,
                            total=num_prompts,
                            avg_latency_ms=elapsed * 1000,
                        )
                else:
                    logger.warning("request_failed", status=response.status_code)
                    failed_requests += 1

            except Exception as e:
                logger.error("request_error", error=str(e))
                failed_requests += 1

        savings = baseline_cost - total_cost
        savings_percentage = (savings / baseline_cost * 100) if baseline_cost > 0 else 0

        logger.info(
            "benchmark_complete",
            total_cost=total_cost,
            baseline_cost=baseline_cost,
            savings=savings,
            savings_percentage=savings_percentage,
            failed_requests=failed_requests,
        )

        return {
            "total_requests": num_prompts,
            "successful_requests": num_prompts - failed_requests,
            "failed_requests": failed_requests,
            "gateway_cost_usd": round(total_cost, 2),
            "baseline_cost_usd": round(baseline_cost, 2),
            "savings_usd": round(savings, 2),
            "savings_percentage": round(savings_percentage, 1),
        }

    def validate_gate(self, savings_percentage: float, threshold: float = 20.0) -> bool:
        """Validate that savings meet threshold"""
        if savings_percentage >= threshold:
            logger.info(
                "benchmark_gate_passed",
                savings_percentage=savings_percentage,
                threshold=threshold,
            )
            return True
        else:
            logger.error(
                "benchmark_gate_failed",
                savings_percentage=savings_percentage,
                threshold=threshold,
            )
            return False


def main():
    runner = BenchmarkRunner()

    # Run benchmark
    results = runner.run_benchmark(SAMPLE_PROMPTS, num_prompts=500)

    # Print results
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Total Requests:       {results['total_requests']}")
    print(f"Successful:           {results['successful_requests']}")
    print(f"Failed:               {results['failed_requests']}")
    print(f"\nGateway Cost:         ${results['gateway_cost_usd']}")
    print(f"Baseline (GPT-4o):    ${results['baseline_cost_usd']}")
    print(f"Savings:              ${results['savings_usd']}")
    print(f"Savings %:            {results['savings_percentage']}%")
    print("=" * 60 + "\n")

    # Save results
    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    logger.info("results_saved", path="benchmark_results.json")

    # Check gate
    gate_passed = runner.validate_gate(results["savings_percentage"], threshold=20.0)

    if gate_passed:
        print("✅ GATE PASSED: Savings >= 20%")
        return 0
    else:
        print("❌ GATE FAILED: Savings < 20%")
        return 1


if __name__ == "__main__":
    sys.exit(main())
