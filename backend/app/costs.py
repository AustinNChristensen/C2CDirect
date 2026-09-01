from dataclasses import dataclass

from .models import BudgetPolicy, CostEstimate


@dataclass(frozen=True)
class ModelPrice:
    input_per_million: float
    output_per_million: float


# Deliberately configuration-owned: update from provider pricing before production use.
MODEL_PRICES: dict[str, ModelPrice] = {
    "economy": ModelPrice(0.25, 2.00),
    "standard": ModelPrice(1.25, 10.00),
    "premium": ModelPrice(5.00, 25.00),
}


def estimate_cost(
    model: str, input_tokens: int, output_tokens: int, policy: BudgetPolicy
) -> CostEstimate:
    price = MODEL_PRICES[model]
    cost = (
        input_tokens / 1_000_000 * price.input_per_million
        + output_tokens / 1_000_000 * price.output_per_million
    )
    reason = None
    if input_tokens + output_tokens > policy.max_total_tokens:
        reason = "token_limit_exceeded"
    elif cost > policy.per_run_limit_usd:
        reason = "per_run_cost_limit_exceeded"
    return CostEstimate(
        model=model,
        estimated_input_tokens=input_tokens,
        estimated_output_tokens=output_tokens,
        estimated_cost_usd=round(cost, 6),
        allowed=reason is None,
        gate_reason=reason,
    )


def route_model(complexity: int) -> str:
    return "economy" if complexity < 35 else "standard" if complexity < 80 else "premium"
