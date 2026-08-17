#!/usr/bin/env python
"""
End-to-end integration test.
Sends real prompts through the gateway, measures routing, latency, cost, cache hits.
"""

import sys
import time
import requests
import json
from typing import Dict, List
import structlog

logger = structlog.get_logger(__name__)

# Test scenarios covering all tiers
TEST_PROMPTS = [
    # Simple tier (factual queries)
    {
        "prompt": "What is the capital of France?",
        "expected_tier": "simple",
        "description": "Simple factual question"
    },
    {
        "prompt": "What is 2 + 2?",
        "expected_tier": "simple",
        "description": "Simple math"
    },
    {
        "prompt": "How tall is Mount Everest in meters?",
        "expected_tier": "simple",
        "description": "Simple fact lookup"
    },

    # Medium tier (reasoning, code, analysis)
    {
        "prompt": "Explain how photosynthesis works in plants.",
        "expected_tier": "medium",
        "description": "Explanation/reasoning"
    },
    {
        "prompt": "Write a Python function that reverses a list.",
        "expected_tier": "medium",
        "description": "Code generation"
    },
    {
        "prompt": "Compare and contrast Python vs Go for backend development.",
        "expected_tier": "medium",
        "description": "Comparative analysis"
    },

    # Complex tier (research, design, novel problems)
    {
        "prompt": "Design a distributed caching architecture for a global content delivery network.",
        "expected_tier": "complex",
        "description": "System architecture design"
    },
    {
        "prompt": "Research the theoretical implications of quantum computing on current cryptography standards.",
        "expected_tier": "complex",
        "description": "Research analysis"
    },
    {
        "prompt": "Architect a novel consensus algorithm for Byzantine fault tolerance.",
        "expected_tier": "complex",
        "description": "Advanced algorithmic design"
    },
]

API_URL = "http://localhost:8000/v1/chat/completions"
TIMEOUT = 30

class E2ETestRunner:
    def __init__(self):
        self.results: List[Dict] = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_cost = 0.0
        self.total_latency_ms = 0.0

    def test_prompt(self, test_case: Dict) -> Dict:
        """Send a prompt through the gateway and validate response."""
        prompt = test_case["prompt"]
        expected_tier = test_case["expected_tier"]
        description = test_case["description"]

        logger.info("e2e_test_start", prompt=prompt[:50], expected_tier=expected_tier)

        payload = {
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "model": "claude-3-sonnet",
            "max_tokens": 500,
        }

        start_time = time.time()
        try:
            response = requests.post(API_URL, json=payload, timeout=TIMEOUT)
            latency_ms = (time.time() - start_time) * 1000

            if response.status_code != 200:
                logger.error(
                    "e2e_test_failed",
                    status=response.status_code,
                    error=response.text[:200]
                )
                return {
                    "prompt": prompt[:100],
                    "description": description,
                    "expected_tier": expected_tier,
                    "status": "FAILED",
                    "error": f"HTTP {response.status_code}",
                    "latency_ms": latency_ms,
                }

            data = response.json()

            # Extract routing decision from HTTP headers (as per design)
            router_tier = response.headers.get("X-Model-Tier", "unknown")
            model_used = response.headers.get("X-Model-Name", "unknown")
            cost_usd = float(response.headers.get("X-Cost-USD", "0.0"))
            cache_hit = response.headers.get("X-Cache-Hit", "false").lower() == "true"
            confidence = float(response.headers.get("X-Confidence", "0.0"))

            # Validate routing
            routing_correct = router_tier == expected_tier

            # Extract response content
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")[:100]

            result = {
                "prompt": prompt[:100],
                "description": description,
                "expected_tier": expected_tier,
                "router_tier": router_tier,
                "routing_correct": routing_correct,
                "model_used": model_used,
                "cost_usd": cost_usd,
                "cache_hit": cache_hit,
                "confidence": confidence,
                "latency_ms": round(latency_ms, 2),
                "response_preview": content,
                "status": "PASSED" if routing_correct else "FAILED",
            }

            # Track metrics
            if cache_hit:
                self.cache_hits += 1
            else:
                self.cache_misses += 1
            self.total_cost += cost_usd
            self.total_latency_ms += latency_ms

            logger.info(
                "e2e_test_complete",
                routing_correct=routing_correct,
                tier=router_tier,
                latency_ms=round(latency_ms, 2),
                cost=cost_usd,
                cache_hit=cache_hit,
            )

            return result

        except requests.exceptions.Timeout:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("e2e_test_timeout", latency_ms=latency_ms)
            return {
                "prompt": prompt[:100],
                "description": description,
                "expected_tier": expected_tier,
                "status": "FAILED",
                "error": "Request timeout",
                "latency_ms": latency_ms,
            }
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("e2e_test_error", error=str(e), latency_ms=latency_ms)
            return {
                "prompt": prompt[:100],
                "description": description,
                "expected_tier": expected_tier,
                "status": "FAILED",
                "error": str(e),
                "latency_ms": latency_ms,
            }

    def run(self):
        """Run all tests."""
        print("\n" + "=" * 80)
        print("END-TO-END INTEGRATION TEST")
        print("=" * 80 + "\n")

        logger.info("e2e_test_suite_start", num_tests=len(TEST_PROMPTS))

        for test_case in TEST_PROMPTS:
            result = self.test_prompt(test_case)
            self.results.append(result)

        # Calculate metrics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.get("status") == "PASSED")
        routing_accuracy = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        cache_hit_rate = 0.0
        if self.cache_hits + self.cache_misses > 0:
            cache_hit_rate = self.cache_hits / (self.cache_hits + self.cache_misses) * 100

        avg_latency_ms = self.total_latency_ms / total_tests if total_tests > 0 else 0

        # Print results table
        print(f"\n{'Prompt':<50} {'Expected':<10} {'Got':<10} {'Latency':<10} {'Cost':<10} {'Cache':<8} {'Status':<10}")
        print("-" * 110)
        for result in self.results:
            status = result.get("status", "UNKNOWN")
            expected = result.get("expected_tier", "?")
            got = result.get("router_tier", "?")
            latency = f"{result.get('latency_ms', 0):.0f}ms"
            cost = f"${result.get('cost_usd', 0):.4f}"
            cache = "HIT" if result.get("cache_hit") else "MISS"
            prompt_preview = result.get("prompt", "")[:45]

            status_symbol = "✓" if status == "PASSED" else "✗"
            print(f"{prompt_preview:<50} {expected:<10} {got:<10} {latency:<10} {cost:<10} {cache:<8} {status_symbol} {status:<8}")

        # Print summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total Tests:           {total_tests}")
        print(f"Passed:                {passed_tests}/{total_tests}")
        print(f"Routing Accuracy:      {routing_accuracy:.1f}%")
        print(f"Cache Hit Rate:        {cache_hit_rate:.1f}% ({self.cache_hits} hits, {self.cache_misses} misses)")
        print(f"Average Latency:       {avg_latency_ms:.2f}ms")
        print(f"Total Cost:            ${self.total_cost:.4f}")
        print("=" * 80 + "\n")

        # Save results
        with open("e2e_results.json", "w") as f:
            json.dump({
                "total_tests": total_tests,
                "passed": passed_tests,
                "routing_accuracy": round(routing_accuracy, 1),
                "cache_hit_rate": round(cache_hit_rate, 1),
                "avg_latency_ms": round(avg_latency_ms, 2),
                "total_cost": round(self.total_cost, 4),
                "results": self.results,
            }, f, indent=2)
        logger.info("e2e_results_saved", path="e2e_results.json")

        # Gate checks
        gates_passed = []
        gates_failed = []

        if routing_accuracy >= 90.0:
            gates_passed.append(f"✅ Routing Accuracy: {routing_accuracy:.1f}% >= 90%")
        else:
            gates_failed.append(f"❌ Routing Accuracy: {routing_accuracy:.1f}% < 90%")

        if avg_latency_ms < 2000:  # p95 latency target
            gates_passed.append(f"✅ Latency: {avg_latency_ms:.2f}ms < 2000ms")
        else:
            gates_failed.append(f"❌ Latency: {avg_latency_ms:.2f}ms >= 2000ms")

        if self.total_cost > 0:
            gates_passed.append(f"✅ Cost Tracking: ${self.total_cost:.4f} recorded")
        else:
            gates_failed.append("❌ Cost Tracking: No costs recorded")

        print("GATES:")
        for gate in gates_passed:
            print(gate)
        for gate in gates_failed:
            print(gate)
        print()

        return len(gates_failed) == 0


def main():
    runner = E2ETestRunner()
    success = runner.run()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
