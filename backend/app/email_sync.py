"""Tenant-isolated ingestion of authorized mailbox job alerts and recruiter messages."""

import re
from datetime import UTC, datetime, timedelta
from hashlib import sha256

import asyncpg
import httpx

from .email_connectors import MailboxMessage, fetch_mailbox_messages
from .email_oauth import decrypt_secret, encrypt_secret, refresh_tokens
from .graph import screening_graph
from .models import JobPostingIn, SearchProfile
from .provenance import JobObservation, ProviderDefinition, ProviderType, assess_provenance
from .repositories import (
    claim_email_message,
    complete_email_message,
    complete_email_sync,
    get_email_connection,
    record_job_observation,
    update_email_tokens,
    upsert_job,
    upsert_provider,
)
from .usage import active_policy, metered_screening


def _sender_address(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"[\w.+-]+@[\w.-]+", value)
    return match.group(0).lower() if match else None


def observation_from_email(provider: str, message: MailboxMessage) -> JobObservation | None:
    body = message.body.strip()
    if len(body) < 40:
        return None
    sender = _sender_address(message.sender_address)
    sender_domain = sender.rsplit("@", 1)[1] if sender else None
    title = re.sub(
        r"^(job alert|opportunity|re)\s*[:\-]\s*", "", message.subject, flags=re.IGNORECASE
    )
    field_end = r"(?=\s+(?:location|rate|duration|type)\s*:|[|;\n]|$)"
    company_match = re.search(
        rf"(?:company|client)\s*:\s*(.{{2,100}}?){field_end}", body, re.IGNORECASE
    )
    company = (
        company_match.group(1).strip() if company_match else (sender_domain or "Unknown company")
    )
    location_match = re.search(rf"location\s*:\s*(.{{2,100}}?){field_end}", body, re.IGNORECASE)
    location = location_match.group(1).strip() if location_match else "Unknown"
    urls = re.findall(r"https?://[^\s<>\"]+", body)
    source_url = urls[0].rstrip(".,);]") if urls else None
    rate_range = re.search(
        r"\$(\d{2,3})(?:\.\d+)?\s*[-–]\s*\$?(\d{2,3})(?:\.\d+)?\s*(?:/|per\s*)?(?:hr|hour)",
        body,
        re.IGNORECASE,
    )
    rates = (
        [int(rate_range.group(1)), int(rate_range.group(2))]
        if rate_range
        else [
            int(value)
            for value in re.findall(
                r"\$(\d{2,3})(?:\.\d+)?\s*(?:/|per\s*)?(?:hr|hour)", body, re.IGNORECASE
            )
        ]
    )
    posting = JobPostingIn(
        source=f"email:{provider}",
        source_url=source_url,
        title=(title or "Job opportunity")[:180],
        company=company[:180],
        description=body,
        location=location[:180],
        rate_min=min(rates) if rates else None,
        rate_max=max(rates) if rates else None,
        recruiter_email=sender,
        posted_at=message.received_at,
    )
    return JobObservation(
        provider_slug=f"{provider}-email",
        provider_job_id=message.provider_message_id,
        posting=posting,
        canonical_url_candidate=source_url,
        end_client_name=company if company_match else None,
        recruiter_email_domain=sender_domain,
        engagement_type="contract" if "contract" in body.lower() else None,
        parser_version="authorized-email-v1",
        confidence=0.65 if company_match else 0.5,
        evidence=[
            {"type": "authorized_mailbox_message", "message_id": message.provider_message_id}
        ],
        warnings=[] if company_match else ["end_client_not_explicit"],
    )


async def sync_email_connection(
    tenant_id: str,
    user_id: str,
    provider: str,
    profile: SearchProfile | None = None,
    *,
    limit: int = 50,
    client: httpx.AsyncClient | None = None,
) -> dict:
    connection = await get_email_connection(tenant_id, user_id, provider)
    if not connection or connection["status"] != "active":
        raise LookupError("Active email connection not found")
    provider_definition = ProviderDefinition(
        slug=f"{provider}-email",
        name=f"Authorized {provider.title()} mailbox",
        provider_type=ProviderType.email_channel,
        intake_method="oauth_readonly",
        canonical_domain="gmail.com" if provider == "gmail" else "outlook.com",
        terms_status="approved",
        baseline_authority=60,
        typical_layer_min=0,
        typical_layer_max=2,
    )
    active_profile = profile or SearchProfile()
    owns_client = client is None
    active_client = client or httpx.AsyncClient(timeout=30, follow_redirects=True)
    try:
        access_token = decrypt_secret(connection["encrypted_access_token"])
        expires_at = connection.get("token_expires_at")
        if expires_at and expires_at <= datetime.now(UTC) + timedelta(minutes=1):
            encrypted_refresh = connection.get("encrypted_refresh_token")
            if not encrypted_refresh:
                raise RuntimeError("Mailbox authorization expired and has no refresh token")
            refreshed = await refresh_tokens(
                provider, decrypt_secret(encrypted_refresh), active_client
            )
            access_token = refreshed["access_token"]
            new_expires_at = datetime.now(UTC) + timedelta(
                seconds=int(refreshed.get("expires_in", 3600))
            )
            await update_email_tokens(
                tenant_id,
                str(connection["id"]),
                encrypt_secret(access_token),
                encrypt_secret(refreshed["refresh_token"])
                if refreshed.get("refresh_token")
                else None,
                new_expires_at,
            )
        cursor, messages = await fetch_mailbox_messages(
            provider,
            access_token,
            active_client,
            limit=limit,
        )
        provider_id = await upsert_provider(tenant_id, provider_definition)
        created = ignored = duplicate = failed = 0
        for message in messages:
            digest = sha256(f"{message.subject}\n{message.body}".encode()).hexdigest()
            receipt_id = await claim_email_message(
                tenant_id,
                str(connection["id"]),
                message.provider_message_id,
                digest,
                internet_message_id=message.internet_message_id,
                sender_address=_sender_address(message.sender_address),
                subject=message.subject,
                received_at=message.received_at,
            )
            if not receipt_id:
                duplicate += 1
                continue
            observation = observation_from_email(provider, message)
            if not observation:
                await complete_email_message(tenant_id, receipt_id, "ignored")
                ignored += 1
                continue
            try:
                result = await metered_screening(
                    tenant_id,
                    screening_graph,
                    observation.posting,
                    active_profile,
                    active_policy(),
                    operation=f"email_{provider}",
                )
                screened = result["result"]
                job_id = await upsert_job(tenant_id, screened)
                assessment = assess_provenance(
                    provider_definition,
                    observation,
                    screened.c2c_status,
                    screened.fit_score,
                    active_profile.min_rate,
                )
                await record_job_observation(
                    tenant_id, provider_id, job_id, observation, assessment
                )
                await complete_email_message(tenant_id, receipt_id, "ingested", job_id)
                created += 1
            except (ValueError, RuntimeError, httpx.HTTPError, asyncpg.PostgresError):
                await complete_email_message(tenant_id, receipt_id, "failed")
                failed += 1
        await complete_email_sync(tenant_id, str(connection["id"]), cursor)
        return {
            "provider": provider,
            "received": len(messages),
            "created": created,
            "ignored": ignored,
            "duplicate": duplicate,
            "failed": failed,
        }
    finally:
        if owns_client:
            await active_client.aclose()
