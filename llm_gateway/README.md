# LLM Cost-Optimization Gateway

Real-time monitoring dashboard for intelligent LLM request routing and cost optimization.

## Features

- **Intelligent Routing** - Dynamically routes requests to appropriate model tier (simple/medium/complex)
- **Cost Tracking** - Monitors savings vs GPT-4o baseline with real-time metrics
- **Performance Monitoring** - Charts routing accuracy, latency, and cache hit rates
- **Professional Dashboard** - Gradio-based web interface with Plotly charts

## Live Demo

**Dashboard:** https://huggingface.co/spaces/oladri-Renuka/llm-gateway

View real metrics from 500+ load test requests showing **36.9% cost savings**.

## Quick Start

### Local

```bash
pip install -r requirements.txt
python app.py
```

Open http://localhost:7860

### Deploy to HuggingFace Spaces

1. Create new Gradio Space at https://huggingface.co/new-space
2. Upload: `app.py`, `requirements.txt`, `metrics.db`
3. Space will auto-build and deploy

## Architecture

```
Gradio Dashboard
    ↓
SQLite Database (metrics.db)
    ↓
Plotly Charts + Real-time Metrics
```

## Files

- `app.py` - Gradio dashboard application
- `requirements.txt` - Python dependencies
- `metrics.db` - SQLite database with load test results
- `.env.example` - Configuration template

## Metrics

- Total Requests: 500
- Total Savings: $0.27 (36.9%)
- Avg Latency: 20,573ms
- Success Rate: 100%
- Cache Hit Rate: 0.2%

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py

# Database schema
sqlite3 metrics.db ".schema"
```

## License

Apache 2.0
