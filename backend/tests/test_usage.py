from dataclasses import dataclass

from app import usage
from app.models import BudgetPolicy, CostEstimate, SearchProfile
from tests.factories import make_posting


@dataclass
class ModelUsage:
    actual_cost_usd: float = 0.002
    input_tokens: int = 1000
    output_tokens: int = 500


async def test_metered_screening_reserves_and_reconciles(monkeypatch):
    events = []

    async def reserve(*_args, **kwargs):
        events.append(("reserve", kwargs["operation"], kwargs["provider"]))
        return usage.Reservation("reservation-1", 0.003)

    async def reconcile(*args):
        events.append(("reconcile", args[2], args[3], args[4]))

    async def connection(*_args):
        return None

    monkeypatch.setattr(usage, "reserve_budget", reserve)
    monkeypatch.setattr(usage, "reconcile_budget", reconcile)
    monkeypatch.setattr(usage, "get_model_connection", connection)
    monkeypatch.setattr(
        usage,
        "runtime_estimate",
        lambda *_: CostEstimate(
            model="owned-model",
            estimated_input_tokens=1200,
            estimated_output_tokens=600,
            estimated_cost_usd=0.003,
            allowed=True,
        ),
    )
    monkeypatch.setattr(
        usage,
        "runtime_status",
        lambda *_: {"provider": "openai_compatible", "model": "owned-model"},
    )

    class Graph:
        async def ainvoke(self, _state):
            return {
                "cost_estimate": CostEstimate(
                    model="owned-model",
                    estimated_input_tokens=1000,
                    estimated_output_tokens=500,
                    estimated_cost_usd=0.002,
                    allowed=True,
                ),
                "model_usage": ModelUsage(),
            }

    await usage.metered_screening(
        "tenant",
        Graph(),
        make_posting(),
        SearchProfile(),
        BudgetPolicy(),
        operation="source_greenhouse",
    )
    assert events == [
        ("reserve", "source_greenhouse", "openai_compatible"),
        ("reconcile", 0.002, 1000, 500),
    ]
