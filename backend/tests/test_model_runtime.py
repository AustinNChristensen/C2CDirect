import httpx

from app import model_runtime
from app.models import BudgetPolicy, SearchProfile
from app.scoring import screen
from tests.factories import make_posting


def test_deterministic_runtime_has_zero_cost(monkeypatch):
    monkeypatch.setattr(model_runtime.settings, "c2cdirect_model_provider", "deterministic")
    monkeypatch.setattr(model_runtime.settings, "c2cdirect_model_base_url", "")
    estimate = model_runtime.runtime_estimate(1000, 500, BudgetPolicy())
    assert estimate.model == "local-rules"
    assert estimate.estimated_cost_usd == 0
    assert model_runtime.runtime_status()["mode"] == "deterministic"


def test_tenant_runtime_overrides_environment(monkeypatch):
    monkeypatch.setattr(model_runtime.settings, "c2cdirect_model_provider", "deterministic")
    config = {
        "provider": "openai_compatible",
        "base_url": "http://model/v1",
        "model_name": "tenant-model",
        "api_key": "private",
        "input_cost_per_million": 1.5,
        "output_cost_per_million": 3,
        "source": "tenant",
    }
    status = model_runtime.runtime_status(config)
    estimate = model_runtime.runtime_estimate(1000, 500, BudgetPolicy(), config)
    assert status == {
        "provider": "openai_compatible",
        "model": "tenant-model",
        "base_url_configured": True,
        "api_key_configured": True,
        "input_cost_per_million": 1.5,
        "output_cost_per_million": 3,
        "mode": "model-assisted",
        "source": "tenant",
    }
    assert estimate.estimated_cost_usd == 0.003


async def test_openai_compatible_runtime_records_provider_usage(monkeypatch):
    monkeypatch.setattr(model_runtime.settings, "c2cdirect_model_provider", "openai_compatible")
    monkeypatch.setattr(model_runtime.settings, "c2cdirect_model_base_url", "http://model/v1")
    monkeypatch.setattr(model_runtime.settings, "c2cdirect_model_name", "owned-model")
    monkeypatch.setattr(model_runtime.settings, "c2cdirect_model_input_cost_per_million", 1.0)
    monkeypatch.setattr(model_runtime.settings, "c2cdirect_model_output_cost_per_million", 2.0)

    async def send(_, url, **_kwargs):
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=request,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"reasons":["Strong fit"],"risks":[],"recommended_action":"Review"}'
                        }
                    }
                ],
                "usage": {"prompt_tokens": 1000, "completion_tokens": 500},
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", send)
    posting = make_posting()
    result, usage = await model_runtime.enrich_screening(
        posting, SearchProfile(), screen(posting, SearchProfile())
    )
    assert result.reasons == ["Strong fit"]
    assert usage.status == "succeeded"
    assert usage.actual_cost_usd == 0.002
