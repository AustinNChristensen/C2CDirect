from dataclasses import dataclass
from functools import lru_cache
from hmac import compare_digest

import jwt
from fastapi import Header, HTTPException
from jwt import PyJWKClient
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    jwt_issuer: str = ""
    jwt_audience: str = "c2cdirect-api"
    jwt_jwks_url: str = ""
    auth_disabled_for_local_dev: bool = False
    mcp_local_bearer_token: str = ""
    mcp_allow_local_premium_dev: bool = False
    trusted_proxy_identity_header: bool = False


settings = AuthSettings()


@dataclass(frozen=True)
class Principal:
    user_id: str
    tenant_id: str
    email: str | None
    roles: tuple[str, ...]
    issuer: str = "local"
    scopes: tuple[str, ...] = ()


def _token_scopes(claims: dict) -> tuple[str, ...]:
    """Normalize OAuth scope and Auth0-style permissions claims."""
    raw_scope = claims.get("scope", "")
    scopes = set(raw_scope.split()) if isinstance(raw_scope, str) else set(raw_scope or [])
    scopes.update(claims.get("permissions", []) or [])
    return tuple(sorted(str(scope) for scope in scopes))


@lru_cache
def jwks_client():
    return PyJWKClient(settings.jwt_jwks_url)


async def require_principal(
    authorization: str = Header(default=""),
    proxy_identity: str = Header(default="", alias="cf-access-jwt-assertion"),
) -> Principal:
    if settings.auth_disabled_for_local_dev:
        return Principal(
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-000000000001",
            "local@example.com",
            ("owner",),
            "local",
            ("mcp:tools", "jobs:read", "jobs:write", "outreach:draft"),
        )
    if authorization.startswith("Bearer "):
        return decode_access_token(authorization.removeprefix("Bearer "))
    if settings.trusted_proxy_identity_header and proxy_identity:
        return decode_access_token(proxy_identity, tenant_from_subject=True)
    raise HTTPException(401, "Missing bearer token")


def decode_access_token(token: str, *, tenant_from_subject: bool = False) -> Principal:
    try:
        key = jwks_client().get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except Exception as exc:
        raise HTTPException(401, "Invalid access token") from exc
    tenant = claims.get("tenant_id") or (claims.get("sub") if tenant_from_subject else None)
    if not tenant:
        raise HTTPException(403, "Token has no tenant")
    return Principal(
        claims["sub"],
        tenant,
        claims.get("email"),
        tuple(claims.get("roles", [])) or (("owner",) if tenant_from_subject else ()),
        claims["iss"],
        _token_scopes(claims)
        or (("mcp:tools", "jobs:read", "jobs:write", "outreach:draft") if tenant_from_subject else ()),
    )


def verify_local_mcp_token(token: str) -> Principal | None:
    if not settings.auth_disabled_for_local_dev or not settings.mcp_local_bearer_token:
        return None
    if not compare_digest(token, settings.mcp_local_bearer_token):
        return None
    return Principal(
        "00000000-0000-0000-0000-000000000001",
        "00000000-0000-0000-0000-000000000001",
        "local@example.com",
        ("owner",),
        "local",
        ("mcp:tools", "jobs:read", "jobs:write", "outreach:draft"),
    )
