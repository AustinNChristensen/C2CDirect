import pytest
from pydantic import ValidationError

from app import main
from app.auth import Principal
from app.models import CandidateProfile


def principal():
    return Principal("user", "tenant", None, ("owner",), scopes=("jobs:write",))


def async_value(value):
    async def result(*_args, **_kwargs):
        return value

    return result


def test_candidate_profile_validates_commercial_and_work_preferences():
    profile = CandidateProfile(min_rate=140, target_rate=155, work_modes=["remote", "hybrid"])
    assert profile.require_c2c
    with pytest.raises(ValidationError):
        CandidateProfile(min_rate=160, target_rate=150)
    with pytest.raises(ValidationError):
        CandidateProfile(work_modes=["teleport"])


def test_completed_profile_requires_matching_inputs():
    with pytest.raises(ValidationError):
        CandidateProfile(onboarding_completed=True)
    completed = CandidateProfile(
        onboarding_completed=True,
        target_roles=["AI Engineer"],
        locations=["Remote"],
        ai_skills=["Python"],
    )
    assert completed.onboarding_completed is True


@pytest.mark.asyncio
async def test_candidate_profile_endpoints_are_user_and_tenant_scoped(monkeypatch):
    saved = CandidateProfile(display_name="Chris").model_dump() | {"resume": None}
    monkeypatch.setattr(main, "get_matching_profile", async_value(saved))
    monkeypatch.setattr(main, "upsert_matching_profile", async_value(None))
    monkeypatch.setattr(main, "delete_matching_resume", async_value(None))

    assert (await main.candidate_profile(principal()))["display_name"] == "Chris"
    updated = await main.update_candidate_profile(CandidateProfile(display_name="Chris"), principal())
    assert updated["resume"] is None
    assert await main.remove_candidate_resume(principal()) == {"deleted": True}
