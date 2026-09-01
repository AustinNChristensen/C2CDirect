"""OAuth PKCE and encrypted token handling for authorized mailbox intake."""

import base64
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmailOAuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    email_token_encryption_key: str = ""
    email_oauth_redirect_base: str = "http://127.0.0.1:8080/api/v1/email/oauth"
    gmail_oauth_client_id: str = ""
    microsoft_oauth_client_id: str = ""


settings = EmailOAuthSettings()


def oauth_status() -> dict:
    return {
        "redirect_base": settings.email_oauth_redirect_base,
        "providers": {
            "gmail": {"configured": bool(settings.gmail_oauth_client_id)},
            "microsoft": {"configured": bool(settings.microsoft_oauth_client_id)},
        },
    }


@dataclass(frozen=True)
class OAuthProvider:
    name: str
    client_id: str
    authorize_url: str
    token_url: str
    scopes: tuple[str, ...]


def provider_config(provider: str) -> OAuthProvider:
    providers = {
        "gmail": OAuthProvider(
            "gmail",
            settings.gmail_oauth_client_id,
            "https://accounts.google.com/o/oauth2/v2/auth",
            "https://oauth2.googleapis.com/token",
            ("openid", "email", "https://www.googleapis.com/auth/gmail.readonly"),
        ),
        "microsoft": OAuthProvider(
            "microsoft",
            settings.microsoft_oauth_client_id,
            "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            ("openid", "email", "offline_access", "User.Read", "Mail.Read"),
        ),
    }
    try:
        return providers[provider]
    except KeyError as exc:
        raise ValueError("Unsupported email provider") from exc


def validate_granted_scopes(provider: str, raw_scopes: str | list[str]) -> list[str]:
    granted = set(raw_scopes.split() if isinstance(raw_scopes, str) else raw_scopes)
    required = {
        "gmail": {"https://www.googleapis.com/auth/gmail.readonly"},
        "microsoft": {"Mail.Read"},
    }
    missing = required.get(provider, set()) - granted
    if missing:
        raise ValueError("Provider did not grant the required read-only mailbox scope")
    return sorted(granted)


def _fernet() -> Fernet:
    if not settings.email_token_encryption_key:
        raise RuntimeError("Email token encryption is not configured")
    return Fernet(settings.email_token_encryption_key.encode())


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError("Stored email credential could not be decrypted") from exc


def _challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(sha256(verifier.encode()).digest()).rstrip(b"=").decode()


def authorization_url(provider: str, tenant_id: str, user_id: str) -> str:
    config = provider_config(provider)
    if not config.client_id:
        raise RuntimeError(f"{provider} OAuth client is not configured")
    verifier = secrets.token_urlsafe(64)
    state = _fernet().encrypt(
        json.dumps(
            {
                "provider": provider,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "verifier": verifier,
                "expires_at": int((datetime.now(UTC) + timedelta(minutes=10)).timestamp()),
            }
        ).encode()
    ).decode()
    redirect_uri = f"{settings.email_oauth_redirect_base}/{provider}/callback"
    params = {
        "client_id": config.client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": " ".join(config.scopes),
        "state": state,
        "code_challenge": _challenge(verifier),
        "code_challenge_method": "S256",
    }
    if provider == "gmail":
        params.update({"access_type": "offline", "prompt": "consent"})
    return f"{config.authorize_url}?{urlencode(params)}"


def decode_state(state: str, expected_provider: str) -> dict:
    try:
        payload = json.loads(_fernet().decrypt(state.encode()).decode())
    except (InvalidToken, json.JSONDecodeError) as exc:
        raise ValueError("Invalid OAuth state") from exc
    if payload.get("provider") != expected_provider:
        raise ValueError("OAuth provider mismatch")
    if payload.get("expires_at", 0) < datetime.now(UTC).timestamp():
        raise ValueError("OAuth state expired")
    return payload


async def exchange_code(
    provider: str, code: str, state: str, client: httpx.AsyncClient | None = None
) -> tuple[dict, dict]:
    payload = decode_state(state, provider)
    config = provider_config(provider)
    data = {
        "client_id": config.client_id,
        "code": code,
        "code_verifier": payload["verifier"],
        "grant_type": "authorization_code",
        "redirect_uri": f"{settings.email_oauth_redirect_base}/{provider}/callback",
    }
    owns_client = client is None
    active_client = client or httpx.AsyncClient(timeout=30)
    try:
        response = await active_client.post(config.token_url, data=data)
        response.raise_for_status()
        return payload, response.json()
    finally:
        if owns_client:
            await active_client.aclose()


async def refresh_tokens(
    provider: str, refresh_token: str, client: httpx.AsyncClient
) -> dict:
    config = provider_config(provider)
    response = await client.post(
        config.token_url,
        data={
            "client_id": config.client_id,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": " ".join(config.scopes) if provider == "microsoft" else None,
        },
    )
    response.raise_for_status()
    return response.json()
