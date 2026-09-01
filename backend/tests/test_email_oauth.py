from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from cryptography.fernet import Fernet

from app import email_oauth


@pytest.fixture(autouse=True)
def oauth_settings(monkeypatch):
    monkeypatch.setattr(email_oauth.settings, "email_token_encryption_key", Fernet.generate_key().decode())
    monkeypatch.setattr(email_oauth.settings, "gmail_oauth_client_id", "gmail-client")
    monkeypatch.setattr(email_oauth.settings, "microsoft_oauth_client_id", "microsoft-client")


def test_authorization_url_uses_pkce_and_encrypted_state():
    url = email_oauth.authorization_url("gmail", "tenant", "user")
    params = parse_qs(urlsplit(url).query)

    assert params["code_challenge_method"] == ["S256"]
    assert "code_verifier" not in params
    state = email_oauth.decode_state(params["state"][0], "gmail")
    assert state["tenant_id"] == "tenant"
    assert state["user_id"] == "user"


def test_state_rejects_provider_substitution_and_tampering():
    url = email_oauth.authorization_url("gmail", "tenant", "user")
    state = parse_qs(urlsplit(url).query)["state"][0]

    with pytest.raises(ValueError, match="provider mismatch"):
        email_oauth.decode_state(state, "microsoft")
    with pytest.raises(ValueError, match="Invalid OAuth state"):
        email_oauth.decode_state(state[:-2] + "xx", "gmail")


@pytest.mark.asyncio
async def test_code_exchange_never_sends_encryption_state_as_credential():
    url = email_oauth.authorization_url("gmail", "tenant", "user")
    state = parse_qs(urlsplit(url).query)["state"][0]

    async def handler(request):
        body = request.content.decode()
        assert "code_verifier=" in body
        assert "client_secret" not in body
        return httpx.Response(200, json={"access_token": "access", "refresh_token": "refresh"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        payload, tokens = await email_oauth.exchange_code("gmail", "code", state, client)

    assert payload["tenant_id"] == "tenant"
    assert tokens["access_token"] == "access"


@pytest.mark.asyncio
async def test_refresh_uses_provider_client_and_refresh_token():
    async def handler(request):
        body = request.content.decode()
        assert "refresh_token=refresh" in body
        assert "grant_type=refresh_token" in body
        return httpx.Response(200, json={"access_token": "new-access", "expires_in": 3600})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await email_oauth.refresh_tokens("microsoft", "refresh", client)

    assert result["access_token"] == "new-access"


def test_mail_tokens_are_encrypted_at_rest():
    encrypted = email_oauth.encrypt_secret("mail-access-token")

    assert "mail-access-token" not in encrypted
    assert email_oauth.decrypt_secret(encrypted) == "mail-access-token"


def test_required_read_only_scope_is_enforced():
    assert email_oauth.validate_granted_scopes(
        "gmail", "openid https://www.googleapis.com/auth/gmail.readonly"
    ) == ["https://www.googleapis.com/auth/gmail.readonly", "openid"]

    with pytest.raises(ValueError, match="required read-only"):
        email_oauth.validate_granted_scopes("microsoft", "openid User.Read")
