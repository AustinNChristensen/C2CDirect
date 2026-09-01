"""Read-only Gmail and Microsoft Graph mailbox adapters for authorized job intake."""

import base64
import html
import re
from datetime import UTC, datetime, timedelta
from email import policy
from email.parser import BytesParser

import httpx
from pydantic import BaseModel


class MailboxMessage(BaseModel):
    provider_message_id: str
    internet_message_id: str | None = None
    sender_address: str | None = None
    subject: str
    body: str
    received_at: datetime | None = None


def _decode_websafe(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _gmail_message(item: dict) -> MailboxMessage:
    raw = _decode_websafe(item["raw"])
    message = BytesParser(policy=policy.default).parsebytes(raw)
    body = message.get_body(preferencelist=("plain", "html"))
    content = body.get_content() if body else ""
    if body and body.get_content_type() == "text/html":
        content = re.sub(r"<[^>]+>", " ", content)
    received = message.get("date")
    return MailboxMessage(
        provider_message_id=item["id"],
        internet_message_id=message.get("message-id"),
        sender_address=message.get("from"),
        subject=message.get("subject") or "Job opportunity",
        body=" ".join(html.unescape(content).split()),
        received_at=received.datetime if received and hasattr(received, "datetime") else None,
    )


async def fetch_gmail_messages(
    token: str, client: httpx.AsyncClient, *, limit: int = 50
) -> tuple[str | None, list[MailboxMessage]]:
    headers = {"authorization": f"Bearer {token}"}
    response = await client.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages",
        headers=headers,
        params={"maxResults": limit, "q": 'newer_than:14d (c2c OR contract OR recruiter OR "job alert")'},
    )
    response.raise_for_status()
    listing = response.json()
    messages = []
    for item in listing.get("messages", [])[:limit]:
        detail = await client.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{item['id']}",
            headers=headers,
            params={"format": "raw"},
        )
        detail.raise_for_status()
        messages.append(_gmail_message(detail.json()))
    return listing.get("nextPageToken"), messages


async def fetch_microsoft_messages(
    token: str, client: httpx.AsyncClient, *, limit: int = 50
) -> tuple[str | None, list[MailboxMessage]]:
    headers = {"authorization": f"Bearer {token}", "prefer": 'outlook.body-content-type="text"'}
    cutoff = (datetime.now(UTC) - timedelta(days=14)).isoformat().replace("+00:00", "Z")
    response = await client.get(
        "https://graph.microsoft.com/v1.0/me/messages",
        headers=headers,
        params={
            "$top": limit,
            "$filter": f"receivedDateTime ge {cutoff}",
            "$select": "id,internetMessageId,subject,from,receivedDateTime,body",
            "$orderby": "receivedDateTime desc",
        },
    )
    response.raise_for_status()
    payload = response.json()
    messages = [
        MailboxMessage(
            provider_message_id=item["id"],
            internet_message_id=item.get("internetMessageId"),
            sender_address=((item.get("from") or {}).get("emailAddress") or {}).get("address"),
            subject=item.get("subject") or "Job opportunity",
            body=" ".join(((item.get("body") or {}).get("content") or "").split()),
            received_at=item.get("receivedDateTime"),
        )
        for item in payload.get("value", [])
    ]
    return payload.get("@odata.nextLink"), messages


async def mailbox_address(provider: str, token: str, client: httpx.AsyncClient) -> str | None:
    headers = {"authorization": f"Bearer {token}"}
    if provider == "gmail":
        response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo", headers=headers
        )
        response.raise_for_status()
        return response.json().get("email")
    response = await client.get(
        "https://graph.microsoft.com/v1.0/me", headers=headers, params={"$select": "mail,userPrincipalName"}
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("mail") or payload.get("userPrincipalName")


async def fetch_mailbox_messages(
    provider: str, token: str, client: httpx.AsyncClient, *, limit: int = 50
) -> tuple[str | None, list[MailboxMessage]]:
    if provider == "gmail":
        return await fetch_gmail_messages(token, client, limit=limit)
    if provider == "microsoft":
        return await fetch_microsoft_messages(token, client, limit=limit)
    raise ValueError("Unsupported email provider")
