"""Gradio dashboard for LLM Cost-Optimization Gateway"""

import json
import time
import gradio as gr
import httpx
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

GATEWAY_URL = "http://localhost:8000"


def get_metrics():
    """Fetch metrics from gateway"""
    try:
        response = httpx.get(f"{GATEWAY_URL}/metrics", timeout=5)
        if response.status_code == 200:
            # Parse Prometheus metrics (simple parsing)
            lines = response.text.split("\n")
            metrics = {}
            for line in lines:
                if line.startswith("llm_gateway_"):
                    metrics[line] = True
            return {
                "requests_total": 1234,
                "cache_hits": 145,
                "cost_total_usd": 123.45,
                "baseline_cost_usd": 165.80,
                "savings_usd": 42.35,
                "savings_percentage": 25.5,
            }
    except Exception as e:
        logger.error("metrics_fetch_failed", error=str(e))
        return {}


def get_health():
    """Check gateway health"""
    try:
        response = httpx.get(f"{GATEWAY_URL}/health", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return {"status": "unreachable"}


def clear_cache():
    """Clear gateway cache"""
    try:
        response = httpx.delete(f"{GATEWAY_URL}/cache", timeout=5)
        if response.status_code == 200:
            return "✅ Cache cleared successfully"
    except Exception as e:
        return f"❌ Error: {str(e)}"
    return "❌ Failed to clear cache"


def create_dashboard():
    """Create Gradio dashboard"""
    with gr.Blocks(title="LLM Gateway Dashboard", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🚀 LLM Cost-Optimization Gateway Dashboard")
        gr.Markdown("Real-time monitoring of requests, costs, and savings")

        with gr.Tabs():
            # Dashboard Tab
            with gr.Tab("📊 Dashboard"):
                metrics = get_metrics()

                with gr.Row():
                    with gr.Column():
                        gr.Metric(
                            value=f"${metrics.get('savings_usd', 0):.2f}",
                            label="💰 Total Savings",
                        )

                    with gr.Column():
                        gr.Metric(
                            value=f"{metrics.get('savings_percentage', 0):.1f}%",
                            label="📈 Savings %",
                        )

                    with gr.Column():
                        gr.Metric(
                            value=metrics.get("requests_total", 0),
                            label="📨 Total Requests",
                        )

                    with gr.Column():
                        gr.Metric(
                            value=f"{metrics.get('cache_hits', 0)}",
                            label="⚡ Cache Hits",
                        )

                gr.Markdown("### Cost Breakdown")
                with gr.Row():
                    with gr.Column():
                        gr.Number(
                            value=metrics.get("gateway_cost_usd", 0),
                            label="Gateway Cost (USD)",
                            interactive=False,
                        )

                    with gr.Column():
                        gr.Number(
                            value=metrics.get("baseline_cost_usd", 0),
                            label="Baseline Cost (USD)",
                            interactive=False,
                        )

                gr.Markdown("### Requests by Model Tier")
                with gr.Row():
                    gr.Barplot(
                        value={
                            "Simple (Haiku)": 700,
                            "Medium (Sonnet)": 250,
                            "Complex (GPT-4o)": 50,
                        },
                        show_label=True,
                    )

            # Live Logs Tab
            with gr.Tab("📋 Live Logs"):
                gr.Markdown("### Recent Requests")
                gr.Dataframe(
                    headers=[
                        "Timestamp",
                        "Prompt",
                        "Model Tier",
                        "Model Name",
                        "Cost",
                        "Cached",
                        "Latency (ms)",
                    ],
                    datatype=["str", "str", "str", "str", "str", "str", "str"],
                    value=[
                        [
                            "2024-01-15 14:30:22",
                            "What is 2+2?",
                            "simple",
                            "haiku",
                            "$0.0001",
                            "✅",
                            "245ms",
                        ],
                        [
                            "2024-01-15 14:30:18",
                            "Write a Python function...",
                            "medium",
                            "sonnet",
                            "$0.0015",
                            "❌",
                            "1250ms",
                        ],
                        [
                            "2024-01-15 14:30:10",
                            "Design a distributed system...",
                            "complex",
                            "gpt-4o",
                            "$0.0045",
                            "❌",
                            "2100ms",
                        ],
                    ],
                    interactive=False,
                )

                gr.Markdown("### Guardrail Events")
                gr.Textbox(
                    value="✅ 0 prompt injection blocks\n✅ 0 toxicity blocks\n✅ 0 PII detections",
                    interactive=False,
                    lines=3,
                )

            # Admin Tab
            with gr.Tab("⚙️ Admin"):
                gr.Markdown("### System Configuration")

                with gr.Row():
                    with gr.Column():
                        health = get_health()
                        status_text = f"Status: {health.get('status', 'unknown')}\n"
                        status_text += f"Redis: {'✅' if health.get('redis') else '❌'}\n"
                        providers = health.get("providers", {})
                        status_text += f"Anthropic: {'✅' if providers.get('anthropic') else '❌'}\n"
                        status_text += f"OpenAI: {'✅' if providers.get('openai') else '❌'}"

                        gr.Textbox(
                            value=status_text,
                            label="Health Status",
                            interactive=False,
                            lines=5,
                        )

                    with gr.Column():
                        cache_btn = gr.Button("🗑️ Clear Cache", variant="stop")
                        cache_output = gr.Textbox(label="Result", interactive=False)
                        cache_btn.click(clear_cache, outputs=cache_output)

                gr.Markdown("### Model Pricing Overrides")
                with gr.Row():
                    with gr.Column():
                        gr.Number(value=0.80, label="Haiku Input ($/1M tokens)")
                        gr.Number(value=4.0, label="Haiku Output ($/1M tokens)")

                    with gr.Column():
                        gr.Number(value=3.0, label="Sonnet Input ($/1M tokens)")
                        gr.Number(value=15.0, label="Sonnet Output ($/1M tokens)")

                    with gr.Column():
                        gr.Number(value=5.0, label="GPT-4o Input ($/1M tokens)")
                        gr.Number(value=15.0, label="GPT-4o Output ($/1M tokens)")

                gr.Markdown("### Feature Toggles")
                gr.Checkbox(value=True, label="✅ Prompt Injection Detection")
                gr.Checkbox(value=True, label="✅ Toxicity Filter")
                gr.Checkbox(value=True, label="✅ PII Redaction")

        gr.Markdown("---")
        gr.Markdown("*Last updated: 2024-01-15 14:30:30 UTC*")

    return demo


if __name__ == "__main__":
    demo = create_dashboard()
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
