import re
from dataclasses import dataclass
from typing import Optional

import structlog

from src.infra.config import get_settings

logger = structlog.get_logger(__name__)


@dataclass
class GuardrailResult:
    """Result of guardrail check"""
    passed: bool
    reason: Optional[str] = None
    escalate: bool = False  # If True, escalate to stronger model


class InputGuardrails:
    """Validate and sanitize input prompts"""

    # Common jailbreak patterns
    JAILBREAK_PATTERNS = [
        r"ignore.{0,20}(previous|prior|above).{0,20}instructions",
        r"forget.{0,20}(everything|instructions)",
        r"pretend.{0,20}(you are|you're).{0,20}(unrestricted|unfiltered)",
        r"DAN\s*[0-9]*:",
        r"act as if you were",
        r"assume you have no restrictions",
    ]

    TOXICITY_KEYWORDS = [
        "suicide",
        "self-harm",
        "bomb",
        "terrorism",
        "illegal drugs",
    ]

    PII_PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    }

    def __init__(self):
        self.settings = get_settings()

    def check(self, prompt: str) -> GuardrailResult:
        """Check if prompt passes all guardrails"""
        if not self.settings.enable_prompt_injection_detection:
            return GuardrailResult(passed=True)

        # Check length
        if len(prompt) > self.settings.max_prompt_length_tokens * 4:  # Rough estimate: 1 token ~= 4 chars
            return GuardrailResult(
                passed=False,
                reason="prompt_too_long",
            )

        # Check for prompt injection
        for pattern in self.JAILBREAK_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                logger.warning("prompt_injection_detected", pattern=pattern)
                return GuardrailResult(
                    passed=False,
                    reason="prompt_injection_detected",
                )

        # Check for toxicity keywords
        if self.settings.enable_toxicity_filter:
            for keyword in self.TOXICITY_KEYWORDS:
                if keyword.lower() in prompt.lower():
                    logger.warning("toxic_content_detected", keyword=keyword)
                    return GuardrailResult(
                        passed=False,
                        reason="toxic_content_detected",
                    )

        return GuardrailResult(passed=True)

    def get_pii_info(self, text: str) -> dict:
        """Extract PII information (for auditing, not removal)"""
        pii_found = {}
        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                pii_found[pii_type] = len(matches)
        return pii_found


class OutputGuardrails:
    """Validate and sanitize output responses"""

    TOXICITY_KEYWORDS = [
        "hate",
        "violence",
        "discriminat",
    ]

    PII_PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    }

    def __init__(self):
        self.settings = get_settings()

    def check(self, response: str) -> GuardrailResult:
        """Check if response passes guardrails"""
        # Check for toxicity
        if self.settings.enable_toxicity_filter:
            for keyword in self.TOXICITY_KEYWORDS:
                if keyword.lower() in response.lower():
                    logger.warning("toxic_output_detected", keyword=keyword)
                    return GuardrailResult(
                        passed=False,
                        reason="toxic_output_detected",
                        escalate=True,  # Try stronger model
                    )

        return GuardrailResult(passed=True)

    def redact_pii(self, text: str) -> str:
        """Redact PII from text"""
        if not self.settings.enable_pii_redaction:
            return text

        redacted = text
        for pii_type, pattern in self.PII_PATTERNS.items():
            redacted = re.sub(pattern, f"[REDACTED_{pii_type.upper()}]", redacted)

        return redacted

    def get_pii_info(self, text: str) -> dict:
        """Extract PII information (for auditing)"""
        pii_found = {}
        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                pii_found[pii_type] = len(matches)
        return pii_found
