from app.costs import estimate_cost, route_model
from app.models import BudgetPolicy


def test_cost_gate_blocks_oversized_run():
    result = estimate_cost("premium", 50_000, 10_000, BudgetPolicy(max_total_tokens=12_000))
    assert not result.allowed
    assert result.gate_reason == "token_limit_exceeded"


def test_router_uses_economy_for_simple_work():
    assert route_model(20) == "economy"
