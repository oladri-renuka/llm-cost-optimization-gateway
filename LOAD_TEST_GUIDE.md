# Load Test Guide: Populate Dashboard with Real Data

This guide explains how to generate real traffic against your LLM Gateway and populate the dashboard with actual metrics.

---

## Quick Start

### 1. Start the API Server

```bash
python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 &
```

Verify it's running:
```bash
curl -s http://localhost:8000/health | python -m json.tool
```

### 2. Run the Load Test

```bash
python scripts/load_test.py 500
```

This will:
- ✅ Load 500 prompts from Alpaca dataset
- ✅ Make REAL HTTP requests to your API
- ✅ Store results in `metrics.db` SQLite database
- ✅ Print summary (cost, savings, cache hits, latency)

**Time estimate:** 500 requests at ~2-3s per request = ~20-25 minutes with 10 concurrent workers.

### 3. View Dashboard with Real Data

```bash
python src/dashboard/app.py &
# Open http://localhost:7860
```

The dashboard will automatically:
- 📊 Read from `metrics.db` (real data from load test)
- 📈 Display charts showing real routing, costs, savings
- 🔄 Update when you click "Refresh Metrics"

---

## How It Works

### Load Test Pipeline

```
Alpaca Dataset (500 prompts)
         ↓
    load_test.py
         ↓
HTTP requests to localhost:8000
         ↓
API processes & returns metadata
    (tier, model, cost, latency)
         ↓
SQLite database (metrics.db)
         ↓
Dashboard reads & displays
```

### Data Stored in SQLite

The `metrics.db` table includes every request:

```sql
CREATE TABLE requests (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    prompt TEXT,
    model_tier TEXT,          -- "simple", "medium", "complex"
    model_used TEXT,          -- "anthropic/claude-3-haiku", etc.
    cost_usd REAL,           -- Actual cost of this request
    baseline_cost REAL,      -- What GPT-4o would cost
    savings_usd REAL,        -- baseline - cost
    latency_ms REAL,         -- Request latency
    cache_hit BOOLEAN,       -- Was this a cache hit?
    confidence REAL,         -- Router's confidence in tier decision
    status TEXT              -- "success", "error", "timeout"
)
```

---

## Output Example

```
================================================================================
LLM GATEWAY LOAD TEST
================================================================================

1️⃣  Checking server health...
✅ Server is healthy

2️⃣  Loading 500 prompts from Alpaca dataset...
✅ Loaded 500 prompts

3️⃣  Initializing metrics database (metrics.db)...
✅ Database ready

4️⃣  Sending 500 requests with 10 workers...
    (This will take a few minutes...)

    [500/500] 100.0%
✅ All requests completed

5️⃣  Calculating summary statistics...

================================================================================
LOAD TEST RESULTS
================================================================================

📊 Overall Metrics:
  • Total Requests:      500
  • Total Cost:          $4.82
  • Baseline Cost (GPT-4o): $14.38
  • Total Savings:       $9.56
  • Savings Rate:        66.5%
  • Cache Hit Rate:      12.3%
  • Avg Latency:         2156ms

🎯 Breakdown by Tier:
  • SIMPLE:
      Requests:  350
      Cost:      $0.45
      Savings:   $9.78
  • MEDIUM:
      Requests:  100
      Cost:      $1.20
      Savings:   $0.00
  • COMPLEX:
      Requests:  50
      Cost:      $3.17
      Savings:   $0.00

📁 Metrics stored in: metrics.db
   Dashboard will read from this database

✅ Load test complete!
================================================================================
```

---

## Customization

### Run with Different Number of Prompts

```bash
# Load 100 prompts (faster)
python scripts/load_test.py 100

# Load 1000 prompts (longer, more comprehensive)
python scripts/load_test.py 1000
```

### Adjust Concurrency

Edit `scripts/load_test.py`, line 32:
```python
BATCH_SIZE = 10  # Change this to 5 (slower) or 20 (faster)
```

### Clear Database and Start Fresh

```bash
rm metrics.db
python scripts/load_test.py 500
```

---

## Troubleshooting

### ❌ "Server not running"

The API must be running:
```bash
# Terminal 1: Start API
python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000

# Terminal 2: Run load test
python scripts/load_test.py 500
```

### ❌ "datasets library not installed"

Install it:
```bash
pip install datasets
```

### ❌ Dashboard shows "DEMO data"

The dashboard prioritizes real data if available. Check:
1. Does `metrics.db` exist?
2. Does it have data? `sqlite3 metrics.db "SELECT COUNT(*) FROM requests;"`
3. Restart dashboard: `python src/dashboard/app.py &`

### ❌ Load test is slow

Latency depends on:
- **OpenRouter API response time** (2-5s typical)
- **Redis caching** (some requests hit cache, <100ms)
- **Network** (should be local, <1s)

Total expected time for 500 requests: 20-30 minutes with 10 workers.

---

## Dashboard Features (with Real Data)

### 💰 Money Saved Card
- Shows actual `$X.XX` saved vs GPT-4o baseline
- Real savings percentage from your load test

### 📈 Routing Accuracy Chart
- Plots tier decisions over time
- Shows if router is making smart choices

### 🟢 Quality Score by Tier
- Average response quality per tier
- Validates that cheaper tiers still work

### 📦 Top Cached Prompts
- Most frequently reused prompts
- Shows cache effectiveness

### 🔄 Test Routing (Live)
- Type a prompt and see real routing decision
- Uses live API (not from load test data)

---

## Production Workflow

For production deployments:

1. **Load test** to generate representative metrics
2. **Share dashboard** with stakeholders (shows real cost savings)
3. **Monitor live** via Prometheus + Grafana (once deployed)
4. **Compare** load test predictions vs actual production metrics

---

## See Also

- `scripts/load_test.py` — The load test implementation
- `AUDIT.md` — Confirms all load test calls are REAL (no mocks)
- `src/dashboard/app.py` — Dashboard that reads SQLite data
- `.env` — OpenRouter API key and Redis config
