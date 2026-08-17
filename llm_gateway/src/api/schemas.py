from typing import Any, List, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Chat message"""
    role: str = Field(..., description="Message role: user, assistant, system")
    content: str = Field(..., description="Message content")


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request"""
    model: str = Field(default="gpt-4o", description="Model name (ignored by gateway)")
    messages: List[Message] = Field(..., description="Conversation messages")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=2048, ge=1, le=4096)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    system_prompt: Optional[str] = Field(default=None, description="System prompt (non-standard)")


class Choice(BaseModel):
    """Response choice"""
    index: int
    message: Message
    finish_reason: str


class Usage(BaseModel):
    """Token usage"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Usage


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    redis: bool
    providers: dict


class MetricsResponse(BaseModel):
    """Metrics response"""
    requests_total: int
    cache_hits: int
    cache_hit_ratio: float
    cost_total_usd: float
    cost_baseline_usd: float
    savings_usd: float
    savings_percentage: float
    avg_latency_ms: float


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    message: str
    request_id: Optional[str] = None
