import pytest
from fastapi import HTTPException

from app import main
from app.auth import Principal
from app.main import require_owner_write
from app.models import (
    CandidateProfileUpdate,
    RecruiterContactIn,
    RecruiterContactPatch,
    SearchProfileUpdate,
)
from app.repositories import _json_list


def principal(*, roles=("owner",), scopes=("jobs:write",)):
    return Principal("user", "tenant", None, roles, scopes=scopes)


def test_source_sync_requires_owner_and_write_scope():
    require_owner_write(principal())

    with pytest.raises(HTTPException) as not_owner:
        require_owner_write(principal(roles=("member",)))
    assert not_owner.value.status_code == 403

    with pytest.raises(HTTPException) as read_only:
        require_owner_write(principal(scopes=("jobs:read",)))
    assert read_only.value.status_code == 403


def test_job_evidence_json_is_returned_as_arrays():
    assert _json_list('["first", "second"]') == ["first", "second"]
    assert _json_list('"[\\"nested\\"]"') == ["nested"]
    assert _json_list(None) == []


@pytest.mark.asyncio
async def test_personal_sourcing_endpoints_delegate_with_tenant_scope(monkeypatch):
    owner = principal()
    monkeypatch.setattr(main, "upsert_provider", async_value("provider-id"))
    monkeypatch.setattr(main, "list_providers", async_value([{"slug": "dexian"}]))
    monkeypatch.setattr(main, "list_recruiter_contacts", async_value([{"name": "Jamie"}]))
    monkeypatch.setattr(main, "create_recruiter_contact", async_value("contact-id"))
    monkeypatch.setattr(main, "update_recruiter_contact", async_value(None))
    monkeypatch.setattr(
        main, "list_daily_actions", async_value({"jobs": [], "recruiter_follow_ups": []})
    )

    targets = await main.provider_targets(owner)
    seeded = await main.seed_provider_targets(owner)
    assert targets["relationship_claim"] == "target_only_until_verified"
    assert seeded["seeded"] >= 20
    assert await main.providers(owner) == [{"slug": "dexian"}]
    assert await main.recruiters(owner) == [{"name": "Jamie"}]
    created = await main.create_recruiter(RecruiterContactIn(name="Jamie"), owner)
    assert created == {"id": "contact-id"}
    updated = await main.update_recruiter(
        __import__("uuid").uuid4(), RecruiterContactPatch(mark_contacted=True), owner
    )
    assert updated == {"updated": True}
    assert await main.today_actions(owner) == {"jobs": [], "recruiter_follow_ups": []}


@pytest.mark.asyncio
async def test_search_profile_endpoints_are_owner_scoped(monkeypatch):
    owner = principal()
    monkeypatch.setattr(
        main, "get_active_search_profile", async_value(main.SearchProfile(min_rate=150))
    )
    monkeypatch.setattr(main, "upsert_active_search_profile", async_value({"id": "profile-id"}))

    loaded = await main.active_search_profile(owner)
    assert loaded.min_rate == 150
    assert await main.save_search_profile(SearchProfileUpdate(min_rate=150), owner) == {
        "id": "profile-id"
    }


@pytest.mark.asyncio
async def test_candidate_match_endpoints_are_owner_scoped_and_tenant_bound(monkeypatch):
    owner = principal()
    candidate = CandidateProfileUpdate(headline="Senior engineer")
    monkeypatch.setattr(main, "get_candidate_profile", async_value(candidate))
    monkeypatch.setattr(
        main,
        "get_job_posting",
        async_value(__import__("tests.factories", fromlist=["make_posting"]).make_posting()),
    )
    monkeypatch.setattr(main, "get_job_evidence", async_value([]))
    monkeypatch.setattr(
        main, "list_candidate_profiles", async_value([{"id": "candidate-id", "profile": candidate}])
    )
    mine = await main.match_me_to_job(__import__("uuid").uuid4(), owner)
    assert mine["candidate_name"] == "My candidate profile"
    all_matches = await main.match_job_to_candidates(__import__("uuid").uuid4(), owner)
    assert all_matches["scope"] == "tenant_only"
    assert all_matches["matches"][0]["candidate_id"] == "candidate-id"


def async_value(value):
    async def result(*_args, **_kwargs):
        return value

    return result
