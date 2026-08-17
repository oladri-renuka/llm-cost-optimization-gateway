# LLM Cost-Optimization Gateway - Hugging Face Spaces Deployment

This is a production-grade dashboard for the LLM Cost-Optimization Gateway, deployed as a Gradio Space on Hugging Face.

## 🚀 Quick Start

### Option 1: Deploy to Your Own Hugging Face Space

1. **Create a new Space on Hugging Face**
   - Go to https://huggingface.co/new-space
   - Name: `llm-gateway-dashboard`
   - License: Apache 2.0
   - Space SDK: Gradio
   - Visibility: Public

2. **Upload Files**
   - Clone/fork this repository to your Space
   - The Space will automatically detect `app.py` and `requirements.txt`
   - Add `metrics.db` (from your load test) to the Space files

3. **Done!**
   - Your dashboard is live at `https://huggingface.co/spaces/[your-username]/llm-gateway-dashboard`

### Option 2: Use Pre-Loaded Demo Space

**Coming soon** — We'll host a demo space with sample metrics data.

---

## 📊 What's Included

### Dashboard Features

- **Status Banner** — Real-time health indicator (green/yellow/red)
- **Money Saved Card** — Total savings with percentage breakdown
- **Key Metrics Row** — Requests, cache hit rate, latency, cost
- **Routing Accuracy Chart** — 7-day trend with 95% target line
- **Model Confidence Chart** — Confidence scores by tier
- **Professional Design** — Dark theme inspired by Vellum.ai/Linear/Stripe

### Data Source

The dashboard reads from `metrics.db` (SQLite) which contains:
- 500 load test requests with real latency/cost data
- Per-tier breakdown (simple/medium/complex)
- Cache hit tracking
- Request status and error rates

---

## 🔧 Setup Instructions

### Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run dashboard
python app.py
```

Open http://localhost:7860

### Adding Your Own Data

Replace `metrics.db` with your load test results:

```bash
# From the main gateway repo
python scripts/load_test.py 500
cp metrics.db /path/to/hf-space/
```

---

## 📈 Current Metrics (Demo Data)

- **Total Requests**: 500
- **Total Savings**: $0.27 (36.9%)
- **Avg Latency**: 20,573ms
- **Success Rate**: 100%
- **Cache Hit Rate**: 0.2%

### By Model Tier

| Tier | Requests | Cost | Savings |
|------|----------|------|---------|
| Simple | 315 | $0.05 | $0.39 |
| Medium | 167 | $0.37 | -$0.12 |
| Complex | 18 | $0.03 | $0.00 |

---

## 🏗️ Architecture

```
Hugging Face Space
    ↓
Gradio App (app.py)
    ↓
SQLite Database (metrics.db)
    ↓
Plotly Charts + HTML Components
```

**Why this setup?**
- ✅ No external API dependencies (self-contained)
- ✅ Real data from production load tests
- ✅ Fast load times (all local)
- ✅ Privacy-first (no data sent to external services)

---

## 🔐 Privacy & Security

- ✅ **All data local** — SQLite database stored in the Space
- ✅ **No external calls** — Dashboard generates charts locally
- ✅ **No sensitive data** — Metrics are aggregated, anonymized
- ✅ **Open source** — Full transparency

---

## 📝 Files

- `app.py` — Gradio dashboard application
- `requirements.txt` — Python dependencies
- `metrics.db` — SQLite database with load test results
- `HF_SPACES_README.md` — This file

---

## 🚀 Next Steps

1. **Integrate with your OpenRouter API**
   - Deploy the full gateway stack
   - Run load tests on real workloads
   - Import metrics into dashboard

2. **Customize the dashboard**
   - Modify color palette
   - Add additional charts
   - Include more metrics

3. **Scale to production**
   - Deploy FastAPI backend to production
   - Connect to real Redis cluster
   - Monitor in Grafana

---

## 📚 Related Resources

- [LLM Gateway GitHub](https://github.com/anthropics/llm-gateway)
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [OpenRouter API](https://openrouter.ai)
- [Hugging Face Spaces Docs](https://huggingface.co/docs/hub/spaces)

---

## 💬 Support

For issues or questions:
- Check the main gateway repository
- Review the design documentation (DESIGN.md)
- Open an issue on GitHub

---

**Last Updated**: 2026-08-16  
**Status**: Production-Ready ✅
