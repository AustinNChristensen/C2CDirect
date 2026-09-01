from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app import auth
from app.auth import require_principal, settings, verify_local_mcp_token


def test_local_mcp_token_requires_authentication(monkeypatch):
    monkeypatch.setattr(settings, "auth_disabled_for_local_dev", True)
    monkeypatch.setattr(settings, "mcp_local_bearer_token", "local-test-token")

    assert verify_local_mcp_token("wrong-token") is None
    principal = verify_local_mcp_token("local-test-token")
    assert principal is not None
    assert principal.tenant_id == "00000000-0000-0000-0000-000000000001"
    assert principal.roles == ("owner",)


def test_local_mcp_token_is_never_accepted_when_auth_is_enabled(monkeypatch):
    monkeypatch.setattr(settings, "auth_disabled_for_local_dev", False)
    monkeypatch.setattr(settings, "mcp_local_bearer_token", "local-test-token")

    assert verify_local_mcp_token("local-test-token") is None


@pytest.mark.asyncio
async def test_authenticated_jwt_claims_create_a_principal(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class SigningKey:
        key = private_key.public_key()

    class JwksClient:
        def get_signing_key_from_jwt(self, _token):
            return SigningKey()

    issuer = "https://identity.test/"
    monkeypatch.setattr(settings, "auth_disabled_for_local_dev", False)
    monkeypatch.setattr(settings, "jwt_issuer", issuer)
    monkeypatch.setattr(settings, "jwt_audience", "c2cdirect-api")
    monkeypatch.setattr(auth, "jwks_client", lambda: JwksClient())
    token = jwt.encode(
        {
            "sub": "auth0|user-1",
            "tenant_id": "organization-1",
            "email": "owner@example.test",
            "roles": ["owner"],
            "scope": "mcp:tools jobs:read",
            "permissions": ["jobs:write"],
            "iss": issuer,
            "aud": "c2cdirect-api",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
    )

    principal = await require_principal(f"Bearer {token}")
    assert principal.user_id == "auth0|user-1"
    assert principal.tenant_id == "organization-1"
    assert principal.issuer == issuer
    assert principal.scopes == ("jobs:read", "jobs:write", "mcp:tools")


@pytest.mark.asyncio
async def test_trusted_proxy_identity_is_opt_in(monkeypatch):
    monkeypatch.setattr(settings, "auth_disabled_for_local_dev", False)
    monkeypatch.setattr(settings, "trusted_proxy_identity_header", True)
    expected = auth.Principal("user", "user", None, ("owner",), scopes=("jobs:write",))
    monkeypatch.setattr(auth, "decode_access_token", lambda *_args, **_kwargs: expected)

    principal = await require_principal(
        authorization="", proxy_identity="signed-access-token"
    )
    assert principal == expected
