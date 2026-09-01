"""Authorization, entitlement, metering, and audit boundaries for MCP tools."""

from collections.abc import Awaitable, Callable
from time import monotonic
from typing import Any

from mcp.server.auth.middleware.auth_context import get_access_token

from .auth import Principal, settings
from .database import provision_principal
from .entitlements import PLANS, Plan
from .repositories import complete_mcp_call, get_tenant_plan, reserve_mcp_call


def principal_from_mcp_context() -> Principal:
    token = get_access_token()
    if token is None:
        raise PermissionError("Authenticated MCP access is required")
    claims = token.claims or {}
    tenant_id = claims.get("tenant_id")
    if not token.subject or not tenant_id:
        raise PermissionError("The MCP token is missing identity or tenant claims")
    return Principal(
        user_id=token.subject,
        tenant_id=str(tenant_id),
        email=claims.get("email"),
        roles=tuple(claims.get("roles", [])),
        issuer=str(claims.get("issuer", "unknown")),
        scopes=tuple(token.scopes),
    )


def require_scope(principal: Principal, scope: str):
    if scope not in principal.scopes:
        raise PermissionError(f"MCP token requires the '{scope}' scope")


async def run_premium_tool(
    request_id: str,
    tool_name: str,
    required_scope: str,
    operation: Callable[[Principal], Awaitable[Any]],
) -> Any:
    """Run a tool only after identity, plan, scope, quota, and audit checks pass."""
    external_principal = principal_from_mcp_context()
    require_scope(external_principal, required_scope)
    principal = await provision_principal(external_principal)
    plan = Plan(await get_tenant_plan(principal.tenant_id))
    entitlement = PLANS[plan]
    local_override = (
        settings.auth_disabled_for_local_dev
        and settings.mcp_allow_local_premium_dev
        and principal.issuer == "local"
    )
    if not entitlement.remote_mcp and not local_override:
        raise PermissionError("Remote MCP access requires a Pro or Team plan")
    daily_limit = entitlement.daily_mcp_calls if entitlement.remote_mcp else 1_000
    audit_id = await reserve_mcp_call(
        principal.tenant_id,
        principal.user_id,
        request_id,
        tool_name,
        principal.scopes,
        daily_limit,
    )
    started = monotonic()
    try:
        result = await operation(principal)
    except Exception as exc:
        await complete_mcp_call(
            principal.tenant_id,
            audit_id,
            "failed",
            round((monotonic() - started) * 1000),
            type(exc).__name__,
        )
        raise
    await complete_mcp_call(
        principal.tenant_id, audit_id, "completed", round((monotonic() - started) * 1000)
    )
    return result
