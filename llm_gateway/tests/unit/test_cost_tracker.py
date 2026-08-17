import pytest

from src.core.cost_tracker import CostTracker


@pytest.fixture
def cost_tracker():
    return CostTracker()


def test_cost_calculation_simple(cost_tracker):
    """Test cost calculation for simple model"""
    breakdown = cost_tracker.calculate_cost(
        model_tier="simple",
        input_tokens=100,
        output_tokens=50,
    )
    assert breakdown.model_tier == "simple"
    assert breakdown.input_tokens == 100
    assert breakdown.output_tokens == 50
    assert breakdown.total_cost < breakdown.baseline_cost
    assert breakdown.savings > 0


def test_cost_calculation_medium(cost_tracker):
    """Test cost calculation for medium model"""
    breakdown = cost_tracker.calculate_cost(
        model_tier="medium",
        input_tokens=100,
        output_tokens=50,
    )
    assert breakdown.model_tier == "medium"
    assert breakdown.total_cost < breakdown.baseline_cost


def test_cost_calculation_complex(cost_tracker):
    """Test cost calculation for complex model"""
    breakdown = cost_tracker.calculate_cost(
        model_tier="complex",
        input_tokens=100,
        output_tokens=50,
    )
    assert breakdown.model_tier == "complex"
    assert breakdown.total_cost == breakdown.baseline_cost  # Same as baseline


def test_savings_percentage_calculation(cost_tracker):
    """Test savings percentage calculation"""
    breakdown = cost_tracker.calculate_cost(
        model_tier="simple",
        input_tokens=1000,
        output_tokens=500,
    )
    assert breakdown.savings_percentage > 0
    assert breakdown.savings_percentage < 100


def test_invalid_model_tier(cost_tracker):
    """Test error handling for invalid model tier"""
    with pytest.raises(ValueError):
        cost_tracker.calculate_cost(
            model_tier="invalid",
            input_tokens=100,
            output_tokens=50,
        )
