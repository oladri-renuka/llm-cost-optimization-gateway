import time
from dataclasses import dataclass
from typing import Optional, Literal
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RouterOutput:
    """Output from router"""
    model_tier: Literal["simple", "medium", "complex"]
    confidence: float
    reasoning: str
    latency_ms: float


class RouterState(TypedDict):
    """State passed through LangGraph DAG"""
    prompt: str
    system_prompt: Optional[str]
    token_count: int
    has_complex_keywords: bool
    has_reasoning_keywords: bool
    has_code_keywords: bool
    model_tier: Literal["simple", "medium", "complex"]
    confidence: float
    reasoning: str


class ComplexityRouter:
    """LangGraph-based complexity classifier with composable decision nodes"""

    REASONING_KEYWORDS = [
        "explain", "compare",
        "what if", "pros and cons", "benefits", "drawbacks",
        "think about", "consider", "evaluate", "assess",
        "analyze", "impact", "pros", "cons",
        "design", "architect", "propose",
    ]

    CODE_KEYWORDS = [
        "code", "write", "implement", "function", "algorithm",
        "debug", "error", "fix", "python", "javascript", "sql",
        "class", "method", "api", "database", "query",
    ]

    COMPLEX_KEYWORDS = [
        "novel", "invent", "research", "theoretical", "advanced",
        "innovation", "breakthrough",
        "architecture", "architect", "redesign",
        "distributed system", "microservices architecture",
        "quantum", "cryptography", "encryption",
        "consensus", "protocol",
        "edge case", "corner case", "anomaly",
        "transformer", "llm inference", "long-context",
    ]

    def __init__(self):
        """Initialize LangGraph-based router"""
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build composable LangGraph DAG for classification"""
        workflow = StateGraph(RouterState)

        # Add nodes
        workflow.add_node("extract_features", self._extract_features)
        workflow.add_node("classify_complex", self._classify_complex)
        workflow.add_node("classify_medium", self._classify_medium)
        workflow.add_node("classify_simple", self._classify_simple)

        # Add edges with conditional routing
        workflow.add_edge(START, "extract_features")
        workflow.add_edge("extract_features", "classify_complex")

        workflow.add_conditional_edges(
            "classify_complex",
            lambda state: state.get("model_tier") == "complex",
            {True: END, False: "classify_medium"},
        )

        workflow.add_conditional_edges(
            "classify_medium",
            lambda state: state.get("model_tier") == "medium",
            {True: END, False: "classify_simple"},
        )

        workflow.add_edge("classify_simple", END)

        return workflow.compile()

    def _extract_features(self, state: RouterState) -> RouterState:
        """Node 1: Extract features from prompt"""
        prompt_lower = state["prompt"].lower()
        token_count = len(state["prompt"]) // 4

        has_complex = any(kw in prompt_lower for kw in self.COMPLEX_KEYWORDS)
        has_reasoning = any(kw in prompt_lower for kw in self.REASONING_KEYWORDS)
        has_code = any(kw in prompt_lower for kw in self.CODE_KEYWORDS)

        state.update({
            "token_count": token_count,
            "has_complex_keywords": has_complex,
            "has_reasoning_keywords": has_reasoning,
            "has_code_keywords": has_code,
        })
        return state

    def _classify_complex(self, state: RouterState) -> RouterState:
        """Node 2: Check for complex-tier classification"""
        if state["has_complex_keywords"]:
            if state["token_count"] < 200:
                confidence = 0.92
                reasoning = "Complex concept in short prompt"
            elif state["token_count"] < 1000:
                confidence = 0.95
                reasoning = "Complex keywords detected"
            else:
                confidence = 0.97
                reasoning = "Complex prompt with extended explanation"

            state.update({
                "model_tier": "complex",
                "confidence": confidence,
                "reasoning": reasoning,
            })
        return state

    def _classify_medium(self, state: RouterState) -> RouterState:
        """Node 3: Check for medium-tier classification"""
        if state.get("model_tier") == "complex":
            return state

        if state["has_reasoning_keywords"] or state["has_code_keywords"]:
            if state["has_code_keywords"] and state["has_reasoning_keywords"]:
                confidence = 0.92
                reasoning = "Code + reasoning detected"
            elif state["has_code_keywords"]:
                confidence = 0.90
                reasoning = "Code generation/implementation requested"
            else:
                confidence = 0.85
                reasoning = "Reasoning/analysis/explanation requested"

            state.update({
                "model_tier": "medium",
                "confidence": confidence,
                "reasoning": reasoning,
            })
        return state

    def _classify_simple(self, state: RouterState) -> RouterState:
        """Node 4: Default to simple-tier classification"""
        if state.get("model_tier") in ["complex", "medium"]:
            return state

        confidence = 0.95 if state["token_count"] < 200 else 0.85
        state.update({
            "model_tier": "simple",
            "confidence": confidence,
            "reasoning": "Straightforward factual question",
        })
        return state

    def classify(self, prompt: str, system_prompt: Optional[str] = None) -> RouterOutput:
        """Classify prompt complexity using LangGraph DAG"""
        start_time = time.time()

        # Initialize state
        initial_state: RouterState = {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "token_count": 0,
            "has_complex_keywords": False,
            "has_reasoning_keywords": False,
            "has_code_keywords": False,
            "model_tier": "simple",
            "confidence": 0.85,
            "reasoning": "default",
        }

        # Invoke LangGraph
        final_state = self.graph.invoke(initial_state)

        latency_ms = (time.time() - start_time) * 1000

        logger.info(
            "router_classification",
            model_tier=final_state["model_tier"],
            confidence=final_state["confidence"],
            latency_ms=latency_ms,
        )

        return RouterOutput(
            model_tier=final_state["model_tier"],
            confidence=final_state["confidence"],
            reasoning=final_state["reasoning"],
            latency_ms=latency_ms,
        )
