import pytest
from pydantic import ValidationError

from app import main
from app.auth import Principal
from app.models import JobImportRequest, JobPostingIn, ModelConnectionIn


def principal():
    return Principal("user", "tenant", None, ("owner",), scopes=("jobs:write",))


def async_value(value):
    async def result(*_args, **_kwargs):
        return value

    return result


def test_model_connection_requires_a_safe_compatible_url():
    with pytest.raises(ValidationError):
        ModelConnectionIn(provider="openai_compatible", model_name="owned-model")
    with pytest.raises(ValidationError):
        ModelConnectionIn(
            provider="openai_compatible",
            base_url="https://user:password@example.com/v1",
            model_name="owned-model",
        )
    deterministic = ModelConnectionIn(
        provider="deterministic", base_url="http://ignored", model_name="ignored"
    )
    assert deterministic.model_name == "local-rules"
    assert deterministic.base_url == ""


@pytest.mark.asyncio
async def test_model_connection_save_never_returns_the_secret(monkeypatch):
    stored = {
        "provider": "openai_compatible",
        "base_url": "http://model/v1",
        "model_name": "owned-model",
        "api_key": "super-secret",
        "input_cost_per_million": 1,
        "output_cost_per_million": 2,
        "updated_at": "2026-08-31T12:00:00Z",
        "source": "tenant",
    }
    monkeypatch.setattr(main, "upsert_model_connection", async_value(None))
    monkeypatch.setattr(main, "get_model_connection", async_value(stored))
    result = await main.save_model_connection(
        ModelConnectionIn(
            provider="openai_compatible",
            base_url="http://model/v1",
            model_name="owned-model",
            api_key="super-secret",
        ),
        principal(),
    )
    assert result["api_key_configured"] is True
    assert "api_key" not in result


@pytest.mark.asyncio
async def test_manual_import_uses_the_screening_pipeline(monkeypatch):
    captured = {}

    async def ingest(tenant_id, batch, _graph, **kwargs):
        captured.update(tenant_id=tenant_id, batch=batch, kwargs=kwargs)
        return {"persisted": 1, "duplicates": 0, "qualified": 1}

    monkeypatch.setattr(main, "ingest_batch", ingest)
    request = JobImportRequest(
        jobs=[
            JobPostingIn(
                source="manual-import",
                title="AI Engineer",
                company="Example Co",
                description="A contract AI engineering role with enough detail for safe screening.",
            )
        ]
    )
    result = await main.import_jobs(request, principal())
    assert result["persisted"] == 1
    assert captured["tenant_id"] == "tenant"
    assert captured["kwargs"]["provider"] == "manual"
    assert captured["batch"].retain_all_in_pipeline is True
