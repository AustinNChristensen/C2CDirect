from uuid import uuid4

import pytest
from pydantic import ValidationError

from app import main
from app.auth import Principal
from app.models import JobDecisionIn


def principal():
    return Principal("user", "tenant", None, ("owner",), scopes=("jobs:write",))


def async_value(value):
    async def result(*_args, **_kwargs):
        return value

    return result


def test_job_decision_requires_a_supported_outcome_and_reason():
    decision = JobDecisionIn(outcome="not_interested", reason_code="rate_below_floor")
    assert decision.notes is None
    with pytest.raises(ValidationError):
        JobDecisionIn(outcome="maybe", reason_code="other")
    with pytest.raises(ValidationError):
        JobDecisionIn(outcome="denied", reason_code="made_up")


@pytest.mark.asyncio
async def test_job_decision_endpoints_delegate_with_tenant_and_user(monkeypatch):
    job_id = uuid4()
    saved = {
        "id": uuid4(),
        "outcome": "denied",
        "reason_code": "denied_by_client",
        "notes": "Role was filled internally",
    }
    monkeypatch.setattr(main, "record_job_decision", async_value(saved))
    monkeypatch.setattr(main, "list_job_decisions", async_value([saved]))

    created = await main.create_job_decision(
        job_id,
        JobDecisionIn(
            outcome="denied",
            reason_code="denied_by_client",
            notes="Role was filled internally",
        ),
        principal(),
    )
    history = await main.job_decisions(job_id, principal())

    assert created["outcome"] == "denied"
    assert history[0]["reason_code"] == "denied_by_client"
