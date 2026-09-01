import base64
from email.message import EmailMessage

import httpx
import pytest

from app.email_connectors import fetch_gmail_messages, fetch_microsoft_messages


def raw_message():
    message = EmailMessage()
    message["Subject"] = "Job alert: Staff AI Engineer"
    message["From"] = "Recruiter <recruiter@prime.example>"
    message["Message-ID"] = "<message-1@example>"
    message.set_content("Company: Acme\nLocation: Remote\nC2C contract at $155/hr using Python and MCP.")
    return base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip("=")


@pytest.mark.asyncio
async def test_gmail_fetch_is_read_only_and_parses_raw_mime():
    async def handler(request):
        assert request.method == "GET"
        if request.url.path.endswith("/messages"):
            return httpx.Response(200, json={"messages": [{"id": "m1"}]})
        return httpx.Response(200, json={"id": "m1", "raw": raw_message()})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        _, messages = await fetch_gmail_messages("token", client)

    assert messages[0].subject == "Job alert: Staff AI Engineer"
    assert "$155/hr" in messages[0].body


@pytest.mark.asyncio
async def test_microsoft_fetch_requests_only_required_message_fields():
    async def handler(request):
        assert request.method == "GET"
        assert "body" in request.url.params["$select"]
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "id": "m1",
                        "subject": "Contract AI Engineer",
                        "from": {"emailAddress": {"address": "recruiter@prime.example"}},
                        "receivedDateTime": "2026-08-29T12:00:00Z",
                        "body": {"content": "Company: Acme Location: Remote C2C contract at $160/hr."},
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        _, messages = await fetch_microsoft_messages("token", client)

    assert messages[0].provider_message_id == "m1"
