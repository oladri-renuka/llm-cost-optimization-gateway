# LLM Cost-Optimization Gateway

**A production-grade FastAPI proxy that routes LLM requests to the cheapest capable model while maintaining quality.**

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](./tests)
[![Coverage](https://img.shields.io/badge/coverage-80%25-brightgreen)](./tests)
[![License](https://img.shields.io/badge/license-MIT-blue)](#license)

## 🎯 Key Metrics

| Metric | Target | Status |
|--------|--------|--------|
| **Cost Savings** | > 25% vs. GPT-4o baseline | ✅ |
| **Routing Accuracy** | > 95% | ✅ |
| **p95 Latency (Simple)** | < 500ms | ✅ |
| **p95 Latency (Complex)** | < 2s | ✅ |
| **Cache Hit Rate** | > 10% | ✅ |
| **Guardrail False Positive** | < 2% | ✅ |

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+**
- **Docker & Docker Compose** (for Redis)
- **API Keys**: Anthropic + OpenAI

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/llm-gateway.git
cd llm-gateway
make install
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Start Redis

```bash
docker-compose -f docker/docker-compose.yml up redis -d
```

### 4. Run the Gateway

```bash
make run-api
```

Server starts at `http://localhost:8000`

### 5. (Optional) Start Dashboard

```bash
make run-dashboard
# Dashboard at http://localhost:7860
```

---

## 📖 Usage

### OpenAI-Compatible Chat API

```python
from openai import OpenAI

client = OpenAI(
    api_key="any-key",
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="gpt-4o",  # (Ignored; gateway decides)
    messages=[{"role": "user", "content": "What is 2+2?"}],
    temperature=0.7,
    max_tokens=2048
)

print(response.choices[0].message.content)
```

**Response headers include:**
```
X-Model-Tier: simple
X-Model-Name: claude-3-5-haiku
X-Cost-USD: 0.00012
X-Cost-vs-GPT4o-USD: -0.00048  (savings!)
X-Cache-Hit: false
X-Total-Latency-Ms: 850
```

---

## 🏗️ Architecture

### Request Flow
1. **Input Validation** → Rate limiting, auth, Pydantic validation
2. **Input Guardrails** → Prompt injection detection, toxicity filter
3. **Classification** → LangGraph router (simple/medium/complex)
4. **Cache Lookup** → Check Redis for identical prompt
5. **Routing** → Select cheapest capable model (Haiku→Sonnet→GPT-4o)
6. **Inference** → Call provider with exponential backoff retries
7. **Output Guardrails** → Toxicity check, PII redaction
8. **Cost Tracking** → Log cost, calculate savings
9. **Cache Store** → Save response in Redis (1h TTL)
10. **Response** → Return OpenAI-format response + custom headers

### Model Selection

| Complexity | Model | Cost (1M tokens) | Use Case |
|---|---|---|---|
| **Simple** | Haiku | $0.80 input, $4 output | Q&A, facts, simple summarization |
| **Medium** | Sonnet | $3 input, $15 output | Code, multi-step reasoning, analysis |
| **Complex** | GPT-4o | $5 input, $15 output | Novel problems, advanced reasoning |

---

## 🧪 Testing

### Run All Tests
```bash
make test
```

### Coverage Report
```bash
make test-cov
```

Target: **>80% coverage**

---

## 📊 Validation & Benchmarking

### Cost-Savings Benchmark
```bash
python scripts/benchmark.py --dataset sharegpt --num-prompts 500
```

**Gate:** Script exits with code 1 if savings < 20%

### Router Accuracy Validation
```bash
python scripts/validate_router.py --dataset labeled_prompts.jsonl
```

**Gate:** Script exits with code 1 if accuracy < 90%

---

## 🔧 Development

### Makefile Targets
```bash
make install              # Install dependencies
make lint                 # Run linter
make format               # Auto-format code
make test                 # Run pytest with coverage
make test-cov             # Show coverage report
make run-api              # Start FastAPI server
make run-dashboard        # Start Gradio dashboard
make docker-build         # Build Docker image
make docker-run           # Run in Docker (redis + api)
make docker-down          # Stop Docker containers
make clean                # Remove cache files
```

### Project Structure
```
llm-gateway/
├── src/
│   ├── core/
│   │   ├── router.py              # LangGraph router
│   │   ├── guardrails.py          # Input/output validation
│   │   ├── cache.py               # Redis caching
│   │   └── cost_tracker.py        # Cost calculation
│   ├── api/
│   │   ├── app.py                 # FastAPI application
│   │   ├── middleware.py          # Auth, rate limiting
│   │   └── schemas.py             # Pydantic models
│   ├── infra/
│   │   ├── redis_client.py        # Redis wrapper
│   │   ├── providers.py           # OpenAI/Anthropic clients
│   │   ├── circuit_breaker.py     # Failure handling
│   │   └── config.py              # Configuration
│   └── ui/
│       └── dashboard.py           # Gradio dashboard
├── tests/
│   ├── unit/                      # Unit tests
│   ├── integration/               # Integration tests
│   └── failover/                  # Failure mode tests
├── scripts/
│   ├── benchmark.py               # Cost-savings validation
│   └── validate_router.py         # Classification accuracy
├── docker/
│   ├── Dockerfile                 # API container
│   └── docker-compose.yml         # Redis + API
├── config/
│   └── settings.yaml              # Configuration
├── docs/
│   └── DESIGN.md                  # Architecture document
├── Makefile                        # Build targets
├── requirements.txt               # Dependencies
├── .env.example                   # Environment template
└── README.md                      # This file
```

---

## 🚨 Failure Modes & Recovery

| Failure | Recovery | Impact |
|---------|----------|--------|
| **Redis Down** | Skip caching, proceed to routing | No cache benefit |
| **Provider Timeout** | Retry 3x with exponential backoff, escalate | Latency spike |
| **Guardrail Blocks** | Escalate to stronger model | Higher cost |
| **Rate-Limited** | Queue with backoff | Delayed response |
| **All Models Fail** | Return 503 Service Unavailable | User sees error |

---

## 🔐 Security

### API Key Management
- Use `.env` for local development
- AWS Secrets Manager for production
- Validate API key on every request

### Prompt Injection Defense
- Regex patterns for common jailbreaks
- Rate-limiting per user (100 req/min)

### PII Protection
- Auto-redact emails, phones, SSNs from responses
- Audit logging with prompt (redacted)

---

## 📦 Deployment

### Local (Development)
```bash
docker-compose -f docker/docker-compose.yml up
```

### AWS ECS (Production)
```bash
make docker-build
docker tag llm-gateway:latest <aws-account>.dkr.ecr.<region>.amazonaws.com/llm-gateway:latest
docker push <aws-account>.dkr.ecr.<region>.amazonaws.com/llm-gateway:latest
aws ecs update-service --cluster production --service llm-gateway --force-new-deployment
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE)

---

**Last Updated:** January 2024  
**Maintainers:** [@yourusername](https://github.com/yourusername)
