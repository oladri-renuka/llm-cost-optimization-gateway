"""
Production-grade LLM Gateway Dashboard with Vellum.ai/Linear/Stripe-style design.
Real-time monitoring with professional UI, charts, and metrics.
"""

import gradio as gr
import requests
import json
import sqlite3
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
import structlog

logger = structlog.get_logger(__name__)

# API endpoints
PROMETHEUS_URL = "http://localhost:8000/metrics"
API_URL = "http://localhost:8000/v1/chat/completions"
METRICS_DB = "metrics.db"

# Color palette (Vellum.ai/Linear/Stripe style)
COLORS = {
    "primary": "#2563EB",      # Blue
    "success": "#10B981",      # Green
    "warning": "#F59E0B",      # Yellow
    "danger": "#EF4444",       # Red
    "background": "#0F172A",   # Dark navy
    "surface": "#1E293B",      # Dark slate
    "border": "#334155",       # Dark gray
    "text": "#F1F5F9",         # Light text
    "text_muted": "#94A3B8",   # Muted text
}

# Metrics storage
MOCK_METRICS = None
REAL_METRICS = None


def load_real_metrics_from_db() -> Optional[dict]:
    """Load real metrics from SQLite database created by load_test.py"""
    global REAL_METRICS

    db_path = Path(METRICS_DB)
    if not db_path.exists():
        return None

    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()

            # Check if table has data
            cursor.execute("SELECT COUNT(*) FROM requests")
            count = cursor.fetchone()[0]
            if count == 0:
                return None

            # Get summary stats
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(cost_usd) as total_cost,
                    SUM(baseline_cost) as total_baseline,
                    SUM(savings_usd) as total_savings,
                    COUNT(CASE WHEN cache_hit = 1 THEN 1 END) as cache_hits,
                    AVG(latency_ms) as avg_latency,
                    COUNT(CASE WHEN status = 'success' THEN 1 END) as success_count,
                    COUNT(CASE WHEN status != 'success' THEN 1 END) as error_count
                FROM requests
                """
            )
            row = cursor.fetchone()

            if not row or row[0] == 0:
                return None

            total, total_cost, total_baseline, total_savings, cache_hits, avg_latency, success_count, error_count = row

            # Failover rate
            failover_rate = (error_count / total * 100) if total > 0 else 0

            savings_pct = (total_savings / total_baseline * 100) if total_baseline else 0
            cache_hit_rate = (cache_hits / total * 100) if total > 0 else 0

            # Get by-tier breakdown
            cursor.execute(
                """
                SELECT model_tier, COUNT(*), SUM(cost_usd), SUM(baseline_cost), SUM(savings_usd), AVG(confidence)
                FROM requests
                WHERE status = 'success'
                GROUP BY model_tier
                """
            )

            by_tier = {}
            for tier, count, cost, baseline, savings, confidence in cursor.fetchall():
                by_tier[tier] = {
                    "count": count,
                    "cost": cost or 0,
                    "baseline": baseline or 0,
                    "savings": savings or 0,
                    "confidence": confidence or 0.85,
                }

            REAL_METRICS = {
                "source": "database",
                "generated_at": datetime.now().isoformat(),
                "summary": {
                    "total_requests": total,
                    "total_cost": round(total_cost or 0, 2),
                    "total_baseline": round(total_baseline or 0, 2),
                    "total_savings": round(total_savings or 0, 2),
                    "savings_percentage": round(savings_pct, 1),
                    "cache_hit_rate": round(cache_hit_rate, 1),
                    "avg_latency": round(avg_latency or 0, 2),
                    "failover_rate": round(failover_rate, 1),
                    "success_count": success_count,
                    "error_count": error_count,
                },
                "by_tier": by_tier,
            }

            logger.info("real_metrics_loaded", count=total, path=str(db_path))
            return REAL_METRICS

    except Exception as e:
        logger.warning("real_metrics_load_failed", error=str(e))
        return None


def load_mock_metrics() -> dict:
    """Load mock metrics from file, or generate if not exists"""
    global MOCK_METRICS

    metrics_file = Path("mock_metrics.json")

    if metrics_file.exists():
        with open(metrics_file) as f:
            MOCK_METRICS = json.load(f)
        logger.info("mock_metrics_loaded", path=str(metrics_file))
        return MOCK_METRICS

    # Generate if not found
    logger.info("generating_mock_metrics")
    from scripts.seed_metrics import seed_metrics

    MOCK_METRICS = seed_metrics(num_days=7, requests_per_day=100)
    return MOCK_METRICS


def get_status_banner() -> Tuple[str, str]:
    """Get status banner based on failover rate"""
    real_metrics = load_real_metrics_from_db()
    if real_metrics:
        failover_rate = real_metrics["summary"]["failover_rate"]
    else:
        failover_rate = 0

    if failover_rate < 2:
        status = "All Systems Operational"
        color = COLORS["success"]
    elif failover_rate < 5:
        status = "Degraded Performance"
        color = COLORS["warning"]
    else:
        status = "Service Disruption"
        color = COLORS["danger"]

    return status, color


def get_dashboard_summary() -> Tuple[str, str, str]:
    """Get summary metrics for display (real data if available, else mock)"""
    # Try to load real metrics from database first
    real_metrics = load_real_metrics_from_db()
    if real_metrics:
        metrics = real_metrics
        data_source = "Real Data (from Load Test)"
    else:
        # Fall back to mock data
        if not MOCK_METRICS:
            load_mock_metrics()
        metrics = MOCK_METRICS
        data_source = "🎭 Demo Data (Mock)"

    summary = metrics.get("summary", {})

    # Money saved card
    total_savings = summary.get("total_savings", 0)
    savings_pct = summary.get("savings_percentage", 0)

    # Color code based on savings rate
    if savings_pct >= 20:
        savings_color = COLORS["success"]
        savings_status = "EXCELLENT"
    elif savings_pct >= 10:
        savings_color = COLORS["warning"]
        savings_status = "GOOD"
    else:
        savings_color = COLORS["danger"]
        savings_status = "NEEDS IMPROVEMENT"

    money_saved_html = f"""
    <div style="
        background: linear-gradient(135deg, {savings_color}22 0%, {savings_color}11 100%);
        border: 1px solid {savings_color};
        border-radius: 12px;
        padding: 32px;
        text-align: center;
    ">
        <div style="font-size: 14px; color: {COLORS['text_muted']}; margin-bottom: 8px;">
            Money Saved This Week
        </div>
        <div style="font-size: 48px; font-weight: 700; color: {savings_color}; margin-bottom: 8px;">
            ${total_savings:.2f}
        </div>
        <div style="font-size: 18px; font-weight: 600; color: {COLORS['text']}; margin-bottom: 12px;">
            {savings_pct:.1f}% Savings
        </div>
        <div style="font-size: 12px; color: {COLORS['text_muted']};">
            Compared to always using GPT-4o baseline
        </div>
        <div style="font-size: 11px; color: {COLORS['text_muted']}; margin-top: 16px;">
            {data_source}
        </div>
    </div>
    """

    # Key metrics
    total_requests = summary.get("total_requests", 0)
    cache_hit_rate = summary.get("cache_hit_rate", 0)
    avg_latency = summary.get("avg_latency", 0)
    total_cost = summary.get("total_cost", 0)

    metrics_html = f"""
    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 16px;">
        <div style="
            background: {COLORS['surface']};
            border: 1px solid {COLORS['border']};
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        ">
            <div style="font-size: 12px; color: {COLORS['text_muted']}; margin-bottom: 8px;">Total Requests</div>
            <div style="font-size: 24px; font-weight: 700; color: {COLORS['text']};">{int(total_requests)}</div>
        </div>
        <div style="
            background: {COLORS['surface']};
            border: 1px solid {COLORS['border']};
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        ">
            <div style="font-size: 12px; color: {COLORS['text_muted']}; margin-bottom: 8px;">Cache Hit Rate</div>
            <div style="font-size: 24px; font-weight: 700; color: {COLORS['text']};">{cache_hit_rate:.1f}%</div>
        </div>
        <div style="
            background: {COLORS['surface']};
            border: 1px solid {COLORS['border']};
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        ">
            <div style="font-size: 12px; color: {COLORS['text_muted']}; margin-bottom: 8px;">Avg Latency</div>
            <div style="font-size: 24px; font-weight: 700; color: {COLORS['text']};">{avg_latency:.0f}ms</div>
        </div>
        <div style="
            background: {COLORS['surface']};
            border: 1px solid {COLORS['border']};
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        ">
            <div style="font-size: 12px; color: {COLORS['text_muted']}; margin-bottom: 8px;">Total Cost</div>
            <div style="font-size: 24px; font-weight: 700; color: {COLORS['text']};">${total_cost:.2f}</div>
        </div>
    </div>
    """

    return money_saved_html, metrics_html, data_source


def get_routing_accuracy_chart() -> go.Figure:
    """Create routing accuracy chart with gridlines and threshold"""
    real_metrics = load_real_metrics_from_db()
    if real_metrics:
        metrics = real_metrics
    else:
        if not MOCK_METRICS:
            load_mock_metrics()
        metrics = MOCK_METRICS

    daily = metrics.get("daily", {})

    days = []
    accuracy = []

    for day_idx in sorted(daily.keys()):
        day_data = daily[day_idx]
        total = sum(day_data[tier]["count"] for tier in ["simple", "medium", "complex"])
        correct = sum(day_data[tier]["correct"] for tier in ["simple", "medium", "complex"])

        acc = (correct / total * 100) if total > 0 else 0

        now = datetime.now()
        date = (now - timedelta(days=6 - day_idx)).strftime("%a %m/%d")

        days.append(date)
        accuracy.append(acc)

    fig = go.Figure()

    # Threshold line at 95%
    fig.add_hline(y=95, line_dash="dash", line_color=COLORS["warning"], annotation_text="95% Target", annotation_position="right")

    fig.add_trace(
        go.Scatter(
            x=days,
            y=accuracy,
            mode="lines+markers",
            name="Routing Accuracy",
            line=dict(color=COLORS["primary"], width=3),
            marker=dict(size=10, color=COLORS["primary"]),
            hovertemplate="<b>%{x}</b><br>Accuracy: %{y:.1f}%<extra></extra>",
        )
    )

    fig.update_layout(
        title="Routing Accuracy Over 7 Days",
        xaxis_title="Date",
        yaxis_title="Accuracy (%)",
        template="plotly_dark",
        hovermode="x unified",
        height=350,
        plot_bgcolor="#0F172A",
        paper_bgcolor="#1E293B",
        font=dict(color=COLORS["text"]),
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor=COLORS["border"],
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor=COLORS["border"],
        ),
    )

    return fig


def get_quality_by_tier_chart() -> go.Figure:
    """Create horizontal quality score chart"""
    real_metrics = load_real_metrics_from_db()
    if real_metrics:
        metrics = real_metrics
    else:
        if not MOCK_METRICS:
            load_mock_metrics()
        metrics = MOCK_METRICS

    by_tier = metrics.get("by_tier", {})

    tiers = []
    scores = []
    colors = []

    tier_colors = {
        "simple": COLORS["primary"],
        "medium": COLORS["warning"],
        "complex": COLORS["success"],
    }

    for tier in ["simple", "medium", "complex"]:
        if tier in by_tier:
            score = by_tier[tier].get("confidence", 0.85)
            tiers.append(tier.capitalize())
            scores.append(score)
            colors.append(tier_colors[tier])

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            y=tiers,
            x=scores,
            orientation="h",
            marker=dict(color=colors),
            text=[f"{s:.2f}" for s in scores],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Confidence: %{x:.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        title="Model Confidence by Tier",
        xaxis_title="Confidence Score",
        yaxis_title="Model Tier",
        template="plotly_dark",
        height=300,
        showlegend=False,
        plot_bgcolor="#0F172A",
        paper_bgcolor="#1E293B",
        font=dict(color=COLORS["text"]),
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor=COLORS["border"],
        ),
    )

    return fig


def get_cached_prompts_table() -> str:
    """Get top cached prompts as styled HTML table"""
    real_metrics = load_real_metrics_from_db()
    if real_metrics:
        metrics = real_metrics
    else:
        if not MOCK_METRICS:
            load_mock_metrics()
        metrics = MOCK_METRICS

    cached = metrics.get("cached_prompts", {})

    if not cached:
        return '<div style="color: #94A3B8; padding: 20px; text-align: center;">No cached prompts yet.</div>'

    rows = ""
    for i, (prompt, hits) in enumerate(list(cached.items())[:5], 1):
        bg_color = COLORS["surface"] if i % 2 == 0 else COLORS["background"]
        truncated = prompt[:60] + "..." if len(prompt) > 60 else prompt
        rows += f"""
        <tr style="background-color: {bg_color};">
            <td style="padding: 12px; border-bottom: 1px solid {COLORS['border']};">
                <span style="color: {COLORS['text_muted']};">{i}.</span>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid {COLORS['border']}; color: {COLORS['text']};">
                {truncated}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid {COLORS['border']}; text-align: center; color: {COLORS['success']}; font-weight: 600;">
                {hits}
            </td>
        </tr>
        """

    html = f"""
    <table style="width: 100%; border-collapse: collapse; border: 1px solid {COLORS['border']}; border-radius: 8px; overflow: hidden;">
        <thead>
            <tr style="background-color: {COLORS['surface']}; border-bottom: 2px solid {COLORS['border']};">
                <th style="padding: 12px; text-align: left; color: {COLORS['text_muted']}; font-weight: 600; font-size: 12px;">ID</th>
                <th style="padding: 12px; text-align: left; color: {COLORS['text_muted']}; font-weight: 600; font-size: 12px;">Prompt</th>
                <th style="padding: 12px; text-align: center; color: {COLORS['text_muted']}; font-weight: 600; font-size: 12px;">Cache Hits</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    """

    return html


def test_prompt(prompt: str, expected_tier: str = "medium") -> str:
    """Test a prompt through the gateway"""
    try:
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "model": "test",
            "max_tokens": 100,
        }

        response = requests.post(API_URL, json=payload, timeout=30)

        if response.status_code != 200:
            return f"❌ API Error: {response.status_code}\n{response.text[:200]}"

        data = response.json()

        # Extract from headers
        tier = response.headers.get("X-Model-Tier", "unknown")
        model = response.headers.get("X-Model-Name", "unknown")
        cost = response.headers.get("X-Cost-USD", "0")
        latency = response.headers.get("X-Total-Latency-Ms", "0")
        cache_hit = response.headers.get("X-Cache-Hit", "false")
        confidence = response.headers.get("X-Confidence", "0")

        result = f"""
**Routing Decision**
- Tier: `{tier}` (expected: `{expected_tier}`)
- Model: `{model}`
- Confidence: {confidence}
- Cache Hit: {cache_hit}

**Performance**
- Latency: {latency}ms

**Cost**
- This Request: ${cost}

**Response Preview**
```
{data.get('choices', [{}])[0].get('message', {}).get('content', '')[:200]}
```
"""
        return result

    except requests.exceptions.Timeout:
        return "❌ Request timed out (>30s)"
    except Exception as e:
        return f"❌ Error: {str(e)}"


def create_dashboard():
    """Create production-grade dashboard"""
    with gr.Blocks(title="LLM Gateway Dashboard") as dashboard:
        # Status banner at top
        status_text, status_color = get_status_banner()
        gr.HTML(
            f"""
            <div style="
                background: linear-gradient(90deg, {status_color}22 0%, {status_color}11 100%);
                border-bottom: 2px solid {status_color};
                padding: 16px 24px;
                margin: -16px -16px 24px -16px;
                text-align: center;
            ">
                <div style="font-size: 16px; font-weight: 600; color: {COLORS['text']};">
                    {status_text}
                </div>
            </div>
            """
        )

        gr.Markdown("# LLM Cost-Optimization Gateway")
        gr.Markdown("Real-time monitoring of routing decisions, costs, and performance.")

        # Load metrics on startup
        real_data = load_real_metrics_from_db()
        if not real_data:
            load_mock_metrics()

        # Money Saved Card
        money_html, metrics_html, data_source = get_dashboard_summary()
        gr.HTML(money_html)

        gr.HTML(metrics_html)

        # Charts
        with gr.Row():
            with gr.Column():
                gr.Plot(value=get_routing_accuracy_chart(), label="Routing Accuracy")

            with gr.Column():
                gr.Plot(value=get_quality_by_tier_chart(), label="Model Confidence")

        # Top Cached Prompts
        gr.Markdown("## 📦 Top Cached Prompts")
        cached_html = get_cached_prompts_table()
        gr.HTML(cached_html)

        # Divider
        gr.Markdown("---")

        # Test Routing Section (kept from original)
        gr.Markdown("## 🧪 Test Routing")
        with gr.Row():
            test_prompt_input = gr.Textbox(
                label="Prompt",
                placeholder="Enter a prompt to test routing...",
                lines=3,
            )
            expected_tier = gr.Dropdown(
                choices=["simple", "medium", "complex"],
                value="medium",
                label="Expected Tier",
            )

        test_output = gr.Markdown(label="Result")
        test_button = gr.Button("Test Routing", variant="primary")

        test_button.click(
            test_prompt,
            inputs=[test_prompt_input, expected_tier],
            outputs=test_output,
        )

        # Refresh button
        refresh_button = gr.Button("🔄 Refresh Data", variant="secondary")

        def refresh_all():
            money_html, metrics_html, data_source = get_dashboard_summary()
            return (
                money_html,
                metrics_html,
                get_routing_accuracy_chart(),
                get_quality_by_tier_chart(),
                get_cached_prompts_table(),
                f"Last updated: {datetime.now().strftime('%H:%M:%S')}",
            )

        refresh_button.click(
            refresh_all,
            outputs=[
                # These are references to the output elements
            ],
        )

        # Footer
        gr.HTML(
            f"""
            <div style="
                margin-top: 48px;
                padding-top: 24px;
                border-top: 1px solid {COLORS['border']};
                text-align: center;
                color: {COLORS['text_muted']};
                font-size: 12px;
            ">
                Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                <br>
                <a href="http://localhost:8000/metrics" target="_blank" style="color: {COLORS['primary']}; text-decoration: none;">
                    View Prometheus Metrics →
                </a>
            </div>
            """
        )

    return dashboard


if __name__ == "__main__":
    dashboard = create_dashboard()
    dashboard.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
    )
