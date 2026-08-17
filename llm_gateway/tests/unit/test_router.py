import pytest

from src.core.router import ComplexityRouter


@pytest.fixture
def router():
    return ComplexityRouter()


def test_simple_classification(router):
    """Test simple prompt classification"""
    result = router.classify("What is 2+2?")
    assert result.model_tier == "simple"
    assert result.confidence > 0.8


def test_medium_classification_with_reasoning(router):
    """Test medium prompt with reasoning keywords"""
    result = router.classify("Why do clouds form? Explain the process.")
    assert result.model_tier == "medium"
    assert result.confidence > 0.8


def test_medium_classification_with_code(router):
    """Test medium prompt with code keywords"""
    result = router.classify("Write a Python function to sort an array")
    assert result.model_tier == "medium"
    assert result.confidence > 0.8


def test_complex_classification_long_prompt(router):
    """Test complex prompt (long)"""
    long_prompt = "Analyze the implications of quantum computing on cryptography. " * 100
    result = router.classify(long_prompt)
    assert result.model_tier == "complex"


def test_complex_classification_with_keywords(router):
    """Test complex prompt with complex keywords"""
    result = router.classify("Design a novel architecture for distributed systems")
    assert result.model_tier == "complex"
    assert result.confidence > 0.8


def test_router_has_reasoning(router):
    """Test router detects reasoning keywords"""
    result = router.classify("Compare the pros and cons of X")
    assert result.model_tier == "medium"
