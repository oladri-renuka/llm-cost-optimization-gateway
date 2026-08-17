import time
import uuid
import json
from datetime import datetime
from typing import Optional

import structlog
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest

from src.api.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    Message,
    Usage,
    HealthResponse,
    MetricsResponse,
    ErrorResponse,
)
from src.api.middleware import RequestIDMiddleware, LoggingMiddleware, RateLimitMiddleware
from src.core.router import ComplexityRouter
from src.core.guardrails import InputGuardrails, OutputGuardrails
from src.core.cache import CacheManager
from src.core.cost_tracker import CostTracker
from src.infra.config import get_settings
from src.infra.redis_client import RedisClient
from src.infra.providers import ProviderRouter

logger = structlog.get_logger(__name__)

# Metrics
requests_total = Counter(
    "llm_gateway_requests_total",
    "Total requests",
    ["model_tier", "provider", "status"],
)
request_duration = Histogram(
    "llm_gateway_request_duration_ms",
    "Request duration in ms",
    ["model_tier"],
)
cache_hits = Counter("llm_gateway_cache_hits_total", "Cache hits")
cache_misses = Counter("llm_gateway_cache_misses_total", "Cache misses")
cost_total = Gauge(
    "llm_gateway_cost_usd_total",
    "Total cost in USD",
    ["model_tier"],
)
guardrail_blocks = Counter(
    "llm_gateway_guardrail_blocks_total",
    "Guardrail blocks",
    ["guardrail_type"],
)


def create_app() -> FastAPI:
    """Create and configure FastAPI app"""
    app = FastAPI(
        title="LLM Cost-Optimization Gateway",
        description="Route LLM requests to optimal model tier",
        version="1.0.0",
    )

    settings = get_settings()

    # Initialize dependencies
    redis_client = RedisClient(settings.redis_url)
    router = ComplexityRouter()
    input_guardrails = InputGuardrails()
    output_guardrails = OutputGuardrails()
    cache_manager = CacheManager(redis_client)
    cost_tracker = CostTracker(redis_client)
    provider_router = ProviderRouter()

    # Add middleware
    app.add_middleware(RateLimitMiddleware, redis_client=redis_client)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    @app.post("/v1/chat/completions")
    async def chat_completions(request: ChatCompletionRequest) -> ChatCompletionResponse:
        """OpenAI-compatible chat completions endpoint"""
        request_id = str(uuid.uuid4())
        start_time = time.time()

        try:
            # Extract prompt
            if not request.messages:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No messages provided",
                )

            prompt = request.messages[-1].content
            system_prompt = request.system_prompt

            # Input guardrails
            guardrail_result = input_guardrails.check(prompt)
            if not guardrail_result.passed:
                guardrail_blocks.labels(guardrail_type=guardrail_result.reason).inc()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Input guardrail failed: {guardrail_result.reason}",
                )

            # Check cache
            cached_response = cache_manager.get(prompt, "medium", system_prompt)
            if cached_response:
                cache_hits.inc()
                latency_ms = (time.time() - start_time) * 1000
                cached_tier = cached_response.get("model_tier", "unknown")

                response_data = ChatCompletionResponse(
                    id=f"chatcmpl-{request_id}",
                    created=int(datetime.now().timestamp()),
                    model=cached_response["model"],
                    choices=[
                        Choice(
                            index=0,
                            message=Message(
                                role="assistant",
                                content=cached_response["content"],
                            ),
                            finish_reason=cached_response.get("finish_reason", "stop"),
                        )
                    ],
                    usage=Usage(
                        prompt_tokens=cached_response["usage"]["input_tokens"],
                        completion_tokens=cached_response["usage"]["output_tokens"],
                        total_tokens=cached_response["usage"]["input_tokens"]
                        + cached_response["usage"]["output_tokens"],
                    ),
                )

                return Response(
                    content=response_data.model_dump_json(),
                    media_type="application/json",
                    headers={
                        "X-Model-Tier": cached_tier,
                        "X-Model-Name": cached_response["model"],
                        "X-Cache-Hit": "true",
                        "X-Total-Latency-Ms": str(round(latency_ms, 2)),
                    },
                )

            cache_misses.inc()

            # Classify complexity
            classification = router.classify(prompt, system_prompt)
            model_tier = classification.model_tier

            # Get provider and model
            provider, model_name = provider_router.get_provider(model_tier)

            # Prepare messages for provider
            messages = [
                {"role": msg.role, "content": msg.content} for msg in request.messages
            ]

            if system_prompt:
                messages.insert(0, {"role": "system", "content": system_prompt})

            # Call provider
            try:
                response = provider.chat(
                    model=model_name,
                    messages=messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                )
            except Exception as e:
                logger.error("provider_call_failed", error=str(e), model_tier=model_tier)
                # Escalate to stronger model
                if model_tier != "complex":
                    escalated_provider, escalated_model = provider_router.get_provider(
                        "complex"
                    )
                    response = escalated_provider.chat(
                        model=escalated_model,
                        messages=messages,
                        temperature=request.temperature,
                        max_tokens=request.max_tokens,
                    )
                    model_tier = "complex"
                else:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="All providers failed",
                    )

            # Output guardrails
            output_result = output_guardrails.check(response["content"])
            if not output_result.passed:
                if output_result.escalate and model_tier != "complex":
                    # Escalate and retry
                    escalated_provider, escalated_model = provider_router.get_provider(
                        "complex"
                    )
                    response = escalated_provider.chat(
                        model=escalated_model,
                        messages=messages,
                        temperature=request.temperature,
                        max_tokens=request.max_tokens,
                    )
                    model_tier = "complex"
                else:
                    guardrail_blocks.labels(guardrail_type=output_result.reason).inc()
                    logger.warning(
                        "output_guardrail_failed",
                        reason=output_result.reason,
                        request_id=request_id,
                    )

            # Redact PII
            response_content = output_guardrails.redact_pii(response["content"])

            # Calculate cost
            cost_breakdown = cost_tracker.calculate_cost(
                model_tier=model_tier,
                input_tokens=response["usage"]["input_tokens"],
                output_tokens=response["usage"]["output_tokens"],
            )
            cost_tracker.record_cost(cost_breakdown)
            cost_total.labels(model_tier=model_tier).set(cost_breakdown.total_cost)

            # Cache response
            cache_manager.set(
                prompt,
                model_tier,
                {
                    "model": model_name,
                    "model_tier": model_tier,
                    "content": response_content,
                    "finish_reason": response.get("stop_reason", "stop"),
                    "usage": response["usage"],
                },
                system_prompt,
            )

            # Metrics
            latency_ms = (time.time() - start_time) * 1000
            request_duration.labels(model_tier=model_tier).observe(latency_ms)
            requests_total.labels(
                model_tier=model_tier,
                provider="anthropic" if model_tier != "complex" else "openai",
                status="200",
            ).inc()

            logger.info(
                "request_success",
                request_id=request_id,
                model_tier=model_tier,
                latency_ms=latency_ms,
                cost=cost_breakdown.total_cost,
                savings=cost_breakdown.savings,
            )

            response_data = ChatCompletionResponse(
                id=f"chatcmpl-{request_id}",
                created=int(datetime.now().timestamp()),
                model=model_name,
                choices=[
                    Choice(
                        index=0,
                        message=Message(
                            role="assistant",
                            content=response_content,
                        ),
                        finish_reason=response.get("stop_reason", "stop"),
                    )
                ],
                usage=Usage(
                    prompt_tokens=response["usage"]["input_tokens"],
                    completion_tokens=response["usage"]["output_tokens"],
                    total_tokens=response["usage"]["input_tokens"]
                    + response["usage"]["output_tokens"],
                ),
            )

            return Response(
                content=response_data.model_dump_json(),
                media_type="application/json",
                headers={
                    "X-Model-Tier": model_tier,
                    "X-Model-Name": model_name,
                    "X-Cost-USD": str(round(cost_breakdown.total_cost, 6)),
                    "X-Cost-vs-GPT4o-USD": str(round(cost_breakdown.savings, 6)),
                    "X-Cache-Hit": "false",
                    "X-Total-Latency-Ms": str(round(latency_ms, 2)),
                    "X-Router-Latency-Ms": str(round(classification.latency_ms, 2)),
                    "X-Confidence": str(round(classification.confidence, 2)),
                },
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error("request_failed", error=str(e), request_id=request_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )

    @app.get("/health")
    async def health() -> HealthResponse:
        """Health check endpoint"""
        return HealthResponse(
            status="ok",
            timestamp=datetime.now().isoformat(),
            redis=redis_client.is_healthy(),
            providers=provider_router.is_healthy(),
        )

    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint"""
        return generate_latest()

    @app.delete("/cache")
    async def clear_cache():
        """Clear cache"""
        success = cache_manager.clear_all()
        return {"success": success}

    return app


# Create app instance for uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
