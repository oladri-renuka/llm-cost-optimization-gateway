#!/usr/bin/env python
"""
Router validation script.
Tests classification accuracy on labeled dataset.
"""

import sys
import json
from typing import List, Tuple
import structlog

from src.core.router import ComplexityRouter

logger = structlog.get_logger(__name__)


# Sample labeled prompts (in production, load from annotation dataset)
LABELED_PROMPTS = [
    # Simple tier
    ("What is the capital of France?", "simple"),
    ("What time is it?", "simple"),
    ("How do I boil an egg?", "simple"),
    ("What is 5+3?", "simple"),
    ("Who was the first president?", "simple"),
    ("How tall is Mount Everest?", "simple"),
    ("What is the population of Paris?", "simple"),
    ("How do I make tea?", "simple"),
    ("What is the weather?", "simple"),
    ("Define photosynthesis in one sentence", "simple"),
    # Medium tier
    ("Explain how photosynthesis works", "medium"),
    ("Write a Python function to sort an array", "medium"),
    ("Compare Python vs Go", "medium"),
    ("Why is the sky blue?", "medium"),
    ("How do neural networks learn?", "medium"),
    ("Implement a binary search algorithm", "medium"),
    ("What are the benefits of async programming?", "medium"),
    ("Debug this code: function add(a, b) { return a + c; }", "medium"),
    ("Analyze the pros and cons of microservices", "medium"),
    ("Design a simple database schema for a blog", "medium"),
    # Complex tier
    ("Design a novel architecture for distributed systems", "complex"),
    ("Analyze the impact of quantum computing on cryptography", "complex"),
    ("Solve a novel problem in machine learning optimization", "complex"),
    ("Research and propose improvements to consensus algorithms", "complex"),
    ("Architect a global-scale edge computing network", "complex"),
    ("Invent a new data structure with O(log n) operations", "complex"),
    ("How would you redesign the internet for privacy?", "complex"),
    ("Propose a novel approach to long-context LLM inference", "complex"),
    ("Design an advanced caching strategy for distributed databases", "complex"),
    ("Research the theoretical limits of recommendation systems", "complex"),
] * 2  # Repeat to get ~60 examples


class RouterValidator:
    def __init__(self):
        self.router = ComplexityRouter()

    def validate(self, labeled_prompts: List[Tuple[str, str]]) -> dict:
        """Validate router accuracy"""
        logger.info("validation_started", num_prompts=len(labeled_prompts))

        results = {"simple": [], "medium": [], "complex": []}
        correct_by_tier = {"simple": 0, "medium": 0, "complex": 0}
        total_by_tier = {"simple": 0, "medium": 0, "complex": 0}

        for prompt, ground_truth in labeled_prompts:
            classification = self.router.classify(prompt)
            predicted = classification.model_tier

            total_by_tier[ground_truth] += 1

            if predicted == ground_truth:
                correct_by_tier[ground_truth] += 1
                results[ground_truth].append(
                    {
                        "prompt": prompt[:50],
                        "predicted": predicted,
                        "ground_truth": ground_truth,
                        "correct": True,
                        "confidence": classification.confidence,
                    }
                )
            else:
                results[ground_truth].append(
                    {
                        "prompt": prompt[:50],
                        "predicted": predicted,
                        "ground_truth": ground_truth,
                        "correct": False,
                        "confidence": classification.confidence,
                    }
                )

        # Calculate accuracy
        accuracies = {}
        for tier in ["simple", "medium", "complex"]:
            if total_by_tier[tier] > 0:
                accuracy = (
                    correct_by_tier[tier] / total_by_tier[tier] * 100
                )
                accuracies[tier] = round(accuracy, 1)
            else:
                accuracies[tier] = 0.0

        total_correct = sum(correct_by_tier.values())
        total_samples = sum(total_by_tier.values())
        overall_accuracy = round(total_correct / total_samples * 100, 1) if total_samples > 0 else 0

        logger.info(
            "validation_complete",
            overall_accuracy=overall_accuracy,
            simple_accuracy=accuracies["simple"],
            medium_accuracy=accuracies["medium"],
            complex_accuracy=accuracies["complex"],
        )

        return {
            "overall_accuracy": overall_accuracy,
            "accuracies_by_tier": accuracies,
            "correct_by_tier": correct_by_tier,
            "total_by_tier": total_by_tier,
            "results": results,
        }

    def validate_gate(self, overall_accuracy: float, threshold: float = 90.0) -> bool:
        """Validate that accuracy meets threshold"""
        if overall_accuracy >= threshold:
            logger.info(
                "validation_gate_passed",
                overall_accuracy=overall_accuracy,
                threshold=threshold,
            )
            return True
        else:
            logger.error(
                "validation_gate_failed",
                overall_accuracy=overall_accuracy,
                threshold=threshold,
            )
            return False


def main():
    validator = RouterValidator()

    # Run validation
    results = validator.validate(LABELED_PROMPTS)

    # Print results
    print("\n" + "=" * 60)
    print("ROUTER VALIDATION RESULTS")
    print("=" * 60)
    print(f"Overall Accuracy:     {results['overall_accuracy']}%")
    print(f"\nAccuracy by Tier:")
    print(f"  Simple:             {results['accuracies_by_tier']['simple']}%")
    print(f"  Medium:             {results['accuracies_by_tier']['medium']}%")
    print(f"  Complex:            {results['accuracies_by_tier']['complex']}%")
    print(f"\nSamples by Tier:")
    print(f"  Simple:             {results['total_by_tier']['simple']}")
    print(f"  Medium:             {results['total_by_tier']['medium']}")
    print(f"  Complex:            {results['total_by_tier']['complex']}")
    print("=" * 60 + "\n")

    # Save results
    with open("validation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    logger.info("results_saved", path="validation_results.json")

    # Check gate
    gate_passed = validator.validate_gate(results["overall_accuracy"], threshold=90.0)

    if gate_passed:
        print("✅ GATE PASSED: Accuracy >= 90%")
        return 0
    else:
        print("❌ GATE FAILED: Accuracy < 90%")
        return 1


if __name__ == "__main__":
    sys.exit(main())
