import pytest

from app import mcp_access
from app.auth import Principal, settings


def principal(scopes=("mcp:tools", "jobs:read")):
    return Principal("user", "tenant", "owner@example.test", ("owner",), "issuer", scopes)


def test_scope_is_deny_by_default():
    with pytest.raises(PermissionError, match="jobs:write"):
        mcp_access.require_scope(principal(), "jobs:write")


@pytest.mark.asyncio
async def test_premium_tool_is_scoped_metered_and_audited(monkeypatch):
    completed = []
    monkeypatch.setattr(mcp_access, "principal_from_mcp_context", principal)
    monkeypatch.setattr(mcp_access, "provision_principal", _async_return(principal()))
    monkeypatch.setattr(mcp_access, "get_tenant_plan", _async_return("pro"))
    monkeypatch.setattr(mcp_access, "reserve_mcp_call", _async_return("audit-1"))

    async def complete(*args):
        completed.append(args)

    monkeypatch.setattr(mcp_access, "complete_mcp_call", complete)

    async def operation(active_principal):
        return {"tenant_id": active_principal.tenant_id}

    result = await mcp_access.run_premium_tool(
        "request-1", "search_jobs", "jobs:read", operation
    )
    assert result == {"tenant_id": "tenant"}
    assert completed[0][2] == "completed"


@pytest.mark.asyncio
async def test_community_plan_cannot_use_remote_mcp(monkeypatch):
    monkeypatch.setattr(settings, "auth_disabled_for_local_dev", False)
    monkeypatch.setattr(settings, "mcp_allow_local_premium_dev", False)
    monkeypatch.setattr(mcp_access, "principal_from_mcp_context", principal)
    monkeypatch.setattr(mcp_access, "provision_principal", _async_return(principal()))
    monkeypatch.setattr(mcp_access, "get_tenant_plan", _async_return("community"))

    with pytest.raises(PermissionError, match="Pro or Team"):
        await mcp_access.run_premium_tool("request-1", "search_jobs", "jobs:read", _noop)


@pytest.mark.asyncio
async def test_failed_tool_records_failure_without_content(monkeypatch):
    completed = []
    monkeypatch.setattr(mcp_access, "principal_from_mcp_context", principal)
    monkeypatch.setattr(mcp_access, "provision_principal", _async_return(principal()))
    monkeypatch.setattr(mcp_access, "get_tenant_plan", _async_return("team"))
    monkeypatch.setattr(mcp_access, "reserve_mcp_call", _async_return("audit-2"))

    async def complete(*args):
        completed.append(args)

    async def fail(_principal):
        raise ValueError("sensitive message that must not be audited")

    monkeypatch.setattr(mcp_access, "complete_mcp_call", complete)
    with pytest.raises(ValueError):
        await mcp_access.run_premium_tool("request-2", "explain_match", "jobs:read", fail)
    assert completed[0][2] == "failed"
    assert completed[0][4] == "ValueError"
    assert all("sensitive message" not in str(value) for value in completed[0])


async def _noop(_principal):
    return None


def _async_return(value):
    async def return_value(*_args, **_kwargs):
        return value

    return return_value
