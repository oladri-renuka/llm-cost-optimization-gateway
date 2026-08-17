"""
Load test: Generate real traffic against the gateway and populate metrics database.
- Loads 500 prompts from Alpaca dataset
- Makes REAL HTTP requests to http://localhost:8000/v1/chat/completions
- Stores results in SQLite for dashboard consumption
- Fails clearly if server is not running
"""

import sqlite3
import requests
import json
import time
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

API_URL = "http://localhost:8000/v1/chat/completions"
METRICS_DB = "metrics.db"
BATCH_SIZE = 10  # Concurrent requests


class MetricsDB:
    """SQLite database for storing request metrics"""

    def __init__(self, db_path: str = METRICS_DB):
        self.db_path = db_path
        self._init_schema()

    def _init_schema(self):
        """Create metrics table if not exists"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    prompt TEXT NOT NULL,
                    model_tier TEXT NOT NULL,
                    model_used TEXT NOT NULL,
                    cost_usd REAL NOT NULL,
                    baseline_cost REAL NOT NULL,
                    savings_usd REAL NOT NULL,
                    latency_ms REAL NOT NULL,
                    cache_hit BOOLEAN NOT NULL,
                    confidence REAL NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )
            conn.commit()
        logger.info("metrics_db_initialized", path=self.db_path)

    def insert_request(self, data: Dict):
        """Insert a single request record"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO requests (
                    prompt, model_tier, model_used, cost_usd, baseline_cost,
                    savings_usd, latency_ms, cache_hit, confidence, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["prompt"],
                    data["model_tier"],
                    data["model_used"],
                    data["cost_usd"],
                    data["baseline_cost"],
                    data["savings_usd"],
                    data["latency_ms"],
                    data["cache_hit"],
                    data["confidence"],
                    data["status"],
                ),
            )
            conn.commit()

    def get_summary(self) -> Dict:
        """Get summary statistics from all requests"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total requests
            cursor.execute("SELECT COUNT(*) FROM requests")
            total = cursor.fetchone()[0]

            # Total cost
            cursor.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM requests")
            total_cost = cursor.fetchone()[0]

            # Total baseline
            cursor.execute("SELECT COALESCE(SUM(baseline_cost), 0) FROM requests")
            total_baseline = cursor.fetchone()[0]

            # Total savings
            total_savings = total_baseline - total_cost

            # Cache hits
            cursor.execute("SELECT COUNT(*) FROM requests WHERE cache_hit = 1")
            cache_hits = cursor.fetchone()[0]

            # By tier
            cursor.execute(
                """
                SELECT model_tier, COUNT(*), SUM(cost_usd), SUM(baseline_cost), SUM(savings_usd)
                FROM requests
                WHERE status = 'success'
                GROUP BY model_tier
                """
            )
            by_tier = {
                row[0]: {
                    "count": row[1],
                    "cost": row[2] or 0,
                    "baseline": row[3] or 0,
                    "savings": row[4] or 0,
                }
                for row in cursor.fetchall()
            }

            # Average latency
            cursor.execute("SELECT AVG(latency_ms) FROM requests WHERE status = 'success'")
            avg_latency = cursor.fetchone()[0] or 0

            savings_pct = (total_savings / total_baseline * 100) if total_baseline > 0 else 0
            cache_hit_rate = (cache_hits / total * 100) if total > 0 else 0

            return {
                "total_requests": total,
                "total_cost": round(total_cost, 2),
                "total_baseline": round(total_baseline, 2),
                "total_savings": round(total_savings, 2),
                "savings_percentage": round(savings_pct, 1),
                "cache_hit_rate": round(cache_hit_rate, 1),
                "avg_latency_ms": round(avg_latency, 2),
                "by_tier": by_tier,
            }


def check_server_health() -> bool:
    """Check if the API server is running"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            logger.info("server_health_ok")
            return True
    except requests.exceptions.ConnectionError:
        logger.error("server_unreachable", url="http://localhost:8000/health")
        return False
    except Exception as e:
        logger.error("server_health_check_failed", error=str(e))
        return False


def load_alpaca_prompts(num_prompts: int = 500) -> list:
    """Load prompts from Alpaca dataset"""
    try:
        import datasets

        logger.info("loading_alpaca_dataset", num_prompts=num_prompts)
        dataset = datasets.load_dataset("yahma/alpaca-cleaned", split="train")

        prompts = []
        for i, sample in enumerate(dataset):
            if i >= num_prompts:
                break
            # Use instruction as prompt, optionally append input
            prompt = sample.get("instruction", "")
            if sample.get("input"):
                prompt += f"\n{sample.get('input')}"
            prompts.append(prompt[:1000])  # Limit to 1000 chars

        logger.info("alpaca_loaded", count=len(prompts))
        return prompts

    except ImportError:
        logger.error("datasets_library_not_installed")
        print("❌ Error: Please install 'datasets' library: pip install datasets")
        sys.exit(1)
    except Exception as e:
        logger.error("alpaca_load_failed", error=str(e))
        print(f"❌ Error loading Alpaca dataset: {e}")
        sys.exit(1)


def make_request(prompt: str, request_id: int) -> Optional[Dict]:
    """Make a single request to the gateway"""
    try:
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "model": "auto",
            "max_tokens": 200,
        }

        start_time = time.time()
        response = requests.post(API_URL, json=payload, timeout=60)
        latency_ms = (time.time() - start_time) * 1000

        if response.status_code != 200:
            logger.warning(
                "request_failed",
                request_id=request_id,
                status=response.status_code,
            )
            return {
                "prompt": prompt[:50],
                "model_tier": "unknown",
                "model_used": "unknown",
                "cost_usd": 0,
                "baseline_cost": 0,
                "savings_usd": 0,
                "latency_ms": latency_ms,
                "cache_hit": False,
                "confidence": 0,
                "status": "error",
            }

        data = response.json()

        # Extract from HTTP headers (per design)
        tier = response.headers.get("X-Model-Tier", "unknown")
        model = response.headers.get("X-Model-Name", "unknown")
        cost = float(response.headers.get("X-Cost-USD", "0.0"))
        baseline = float(response.headers.get("X-Cost-vs-GPT4o-USD", "0.0")) + cost
        savings = baseline - cost
        cache_hit = response.headers.get("X-Cache-Hit", "false").lower() == "true"
        confidence = float(response.headers.get("X-Confidence", "0.0"))

        logger.info(
            "request_success",
            request_id=request_id,
            tier=tier,
            latency_ms=round(latency_ms, 2),
        )

        return {
            "prompt": prompt[:100],
            "model_tier": tier,
            "model_used": model,
            "cost_usd": cost,
            "baseline_cost": baseline,
            "savings_usd": savings,
            "latency_ms": latency_ms,
            "cache_hit": cache_hit,
            "confidence": confidence,
            "status": "success",
        }

    except requests.exceptions.Timeout:
        logger.error("request_timeout", request_id=request_id)
        return {
            "prompt": prompt[:50],
            "model_tier": "unknown",
            "model_used": "unknown",
            "cost_usd": 0,
            "baseline_cost": 0,
            "savings_usd": 0,
            "latency_ms": 30000,
            "cache_hit": False,
            "confidence": 0,
            "status": "timeout",
        }
    except Exception as e:
        logger.error("request_error", request_id=request_id, error=str(e))
        return {
            "prompt": prompt[:50],
            "model_tier": "unknown",
            "model_used": "unknown",
            "cost_usd": 0,
            "baseline_cost": 0,
            "savings_usd": 0,
            "latency_ms": 0,
            "cache_hit": False,
            "confidence": 0,
            "status": "error",
        }


def run_load_test(num_prompts: int = 500, num_workers: int = BATCH_SIZE):
    """Run the load test"""
    print("\n" + "=" * 80)
    print("LLM GATEWAY LOAD TEST")
    print("=" * 80)

    # Check server
    print("\n1️⃣  Checking server health...")
    if not check_server_health():
        print("❌ Server not running at http://localhost:8000")
        print("   Start it with: python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000")
        sys.exit(1)
    print("✅ Server is healthy")

    # Load prompts
    print(f"\n2️⃣  Loading {num_prompts} prompts from Alpaca dataset...")
    prompts = load_alpaca_prompts(num_prompts)
    print(f"✅ Loaded {len(prompts)} prompts")

    # Initialize database
    print(f"\n3️⃣  Initializing metrics database ({METRICS_DB})...")
    db = MetricsDB()
    print(f"✅ Database ready")

    # Run load test
    print(f"\n4️⃣  Sending {len(prompts)} requests with {num_workers} workers...")
    print("    (This will take a few minutes...)\n")

    results = []
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {
            executor.submit(make_request, prompt, idx): idx
            for idx, prompt in enumerate(prompts)
        }

        completed = 0
        for future in as_completed(futures):
            completed += 1
            result = future.result()
            if result:
                results.append(result)
                db.insert_request(result)

            # Progress bar
            pct = (completed / len(prompts)) * 100
            print(f"    [{completed}/{len(prompts)}] {pct:.1f}%", end="\r")

    print("\n✅ All requests completed")

    # Get summary
    print(f"\n5️⃣  Calculating summary statistics...")
    summary = db.get_summary()

    # Print summary
    print("\n" + "=" * 80)
    print("LOAD TEST RESULTS")
    print("=" * 80)
    print(f"\n📊 Overall Metrics:")
    print(f"  • Total Requests:      {summary['total_requests']}")
    print(f"  • Total Cost:          ${summary['total_cost']:.2f}")
    print(f"  • Baseline Cost (GPT-4o): ${summary['total_baseline']:.2f}")
    print(f"  • Total Savings:       ${summary['total_savings']:.2f}")
    print(f"  • Savings Rate:        {summary['savings_percentage']:.1f}%")
    print(f"  • Cache Hit Rate:      {summary['cache_hit_rate']:.1f}%")
    print(f"  • Avg Latency:         {summary['avg_latency_ms']:.0f}ms")

    print(f"\n🎯 Breakdown by Tier:")
    for tier, stats in summary["by_tier"].items():
        if stats["count"] > 0:
            print(f"  • {tier.upper()}:")
            print(f"      Requests:  {stats['count']}")
            print(f"      Cost:      ${stats['cost']:.2f}")
            print(f"      Savings:   ${stats['savings']:.2f}")

    print(f"\n📁 Metrics stored in: {METRICS_DB}")
    print(f"   Dashboard will read from this database")

    print("\n✅ Load test complete!")
    print("=" * 80 + "\n")

    return summary


if __name__ == "__main__":
    try:
        num_prompts = 500
        if len(sys.argv) > 1:
            try:
                num_prompts = int(sys.argv[1])
            except ValueError:
                print(f"Usage: python load_test.py [num_prompts]")
                sys.exit(1)

        run_load_test(num_prompts=num_prompts)
    except KeyboardInterrupt:
        print("\n\n⚠️  Load test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error("load_test_failed", error=str(e))
        print(f"\n❌ Load test failed: {e}")
        sys.exit(1)
