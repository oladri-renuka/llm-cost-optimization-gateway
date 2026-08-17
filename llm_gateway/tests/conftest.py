"""Pytest configuration and fixtures"""

import pytest
from unittest.mock import MagicMock

import structlog

# Configure structlog for testing
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer(),
    ],
)


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    mock = MagicMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    mock.clear.return_value = True
    mock.is_healthy.return_value = True
    return mock


@pytest.fixture
def mock_anthropic_provider():
    """Mock Anthropic provider"""
    mock = MagicMock()
    mock.chat.return_value = {
        "content": "Test response",
        "stop_reason": "stop",
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50,
        },
    }
    mock.is_healthy.return_value = True
    return mock


@pytest.fixture
def mock_openai_provider():
    """Mock OpenAI provider"""
    mock = MagicMock()
    mock.chat.return_value = {
        "content": "Test response",
        "stop_reason": "stop",
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50,
        },
    }
    mock.is_healthy.return_value = True
    return mock
