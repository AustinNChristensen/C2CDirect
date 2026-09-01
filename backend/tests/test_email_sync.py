from datetime import UTC, datetime, timedelta

import pytest

from app import email_sync
from app.email_connectors import MailboxMessage
from app.email_sync import observation_from_email
from app.models import SearchProfile
from app.scoring import screen


@pytest.fixture(autouse=True)
def direct_graph_for_unit_tests(monkeypatch):
    async def run(_tenant, graph, posting, profile, _policy, **_kwargs):
        return await graph.ainvoke({"posting": posting, "profile": profile})

    monkeypatch.setattr(email_sync, "metered_screening", run)


def test_authorized_email_observation_extracts_commercial_evidence():
    observation = observation_from_email(
        "gmail",
        MailboxMessage(
            provider_message_id="message-1",
            sender_address="Recruiter <recruiter@prime.example>",
            subject="Job alert: Staff Agent Engineer",
            body="Company: Direct Client\nLocation: Remote\n12 month C2C contract at $150-$170/hr. Build Python MCP agents. https://client.example/jobs/42",
        ),
    )

    assert observation is not None
    assert observation.posting.title == "Staff Agent Engineer"
    assert observation.posting.company == "Direct Client"
    assert observation.posting.rate_min == 150
    assert observation.posting.rate_max == 170
    assert observation.recruiter_email_domain == "prime.example"
    assert observation.end_client_name == "Direct Client"


def test_short_mail_is_ignored():
    assert (
        observation_from_email(
            "gmail",
            MailboxMessage(provider_message_id="message-1", subject="Hello", body="Too short"),
        )
        is None
    )


@pytest.mark.asyncio
async def test_mailbox_sync_refreshes_ingests_ignores_and_deduplicates(monkeypatch):
    connection = {
        "id": "connection-1",
        "status": "active",
        "encrypted_access_token": "old-access",
        "encrypted_refresh_token": "refresh",
        "token_expires_at": datetime.now(UTC) - timedelta(minutes=1),
    }
    valid = MailboxMessage(
        provider_message_id="valid",
        sender_address="recruiter@prime.example",
        subject="Job alert: Staff Agent Engineer",
        body="Company: Direct Client\nLocation: Remote\nC2C contract at $160/hr using Python, MCP, and AWS.",
    )
    short = MailboxMessage(provider_message_id="short", subject="Hello", body="Too short")
    duplicate = valid.model_copy(update={"provider_message_id": "duplicate"})
    completions = []
    token_updates = []

    async def value(result):
        async def inner(*_args, **_kwargs):
            return result

        return inner

    monkeypatch.setattr(email_sync, "get_email_connection", await value(connection))
    monkeypatch.setattr(email_sync, "decrypt_secret", lambda value: value)
    monkeypatch.setattr(email_sync, "encrypt_secret", lambda value: f"encrypted:{value}")
    monkeypatch.setattr(
        email_sync,
        "refresh_tokens",
        await value(
            {"access_token": "new-access", "refresh_token": "new-refresh", "expires_in": 3600}
        ),
    )

    async def update_tokens(*args):
        token_updates.append(args)

    monkeypatch.setattr(email_sync, "update_email_tokens", update_tokens)
    monkeypatch.setattr(
        email_sync, "fetch_mailbox_messages", await value(("cursor", [valid, short, duplicate]))
    )
    monkeypatch.setattr(email_sync, "upsert_provider", await value("provider-1"))
    claims = iter(["receipt-valid", "receipt-short", None])

    async def claim(*_args, **_kwargs):
        return next(claims)

    monkeypatch.setattr(email_sync, "claim_email_message", claim)

    class Graph:
        async def ainvoke(self, state):
            return {"result": screen(state["posting"], SearchProfile())}

    monkeypatch.setattr(email_sync, "screening_graph", Graph())
    monkeypatch.setattr(email_sync, "upsert_job", await value("job-1"))
    monkeypatch.setattr(email_sync, "record_job_observation", await value("observation-1"))

    async def complete(*args):
        completions.append(args)

    monkeypatch.setattr(email_sync, "complete_email_message", complete)
    monkeypatch.setattr(email_sync, "complete_email_sync", await value(None))

    result = await email_sync.sync_email_connection("tenant", "user", "gmail", client=object())

    assert result == {
        "provider": "gmail",
        "received": 3,
        "created": 1,
        "ignored": 1,
        "duplicate": 1,
        "failed": 0,
    }
    assert token_updates[0][2] == "encrypted:new-access"
    assert [item[2] for item in completions] == ["ingested", "ignored"]
