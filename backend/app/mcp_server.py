"""Authenticated Streamable HTTP MCP adapter for premium C2CDirect access."""

from contextlib import asynccontextmanager
from time import time
from uuid import UUID

import jwt
from fastapi import HTTPException
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import Context, FastMCP

from .auth import decode_access_token, settings, verify_local_mcp_token
from .database import connect, disconnect
from .mcp_access import run_premium_tool
from .mcp_tools import explain_match as explain_match_impl
from .mcp_tools import request_outreach as request_outreach_impl
from .repositories import list_jobs, move_job

VALID_JOB_STATUSES = {
    "new",
    "saved",
    "contacted",
    "submitted",
    "interview",
    "offer",
    "rejected",
    "passed",
}


class C2CTokenVerifier:
    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            principal = verify_local_mcp_token(token) or decode_access_token(token)
        except (jwt.PyJWTError, HTTPException, KeyError, ValueError):
            return None
        return AccessToken(
            token=token,
            client_id=principal.user_id,
            subject=principal.user_id,
            scopes=list(principal.scopes),
            expires_at=int(time()) + 3600,
            claims={
                "tenant_id": principal.tenant_id,
                "roles": list(principal.roles),
                "email": principal.email,
                "issuer": principal.issuer,
            },
        )


@asynccontextmanager
async def lifespan(_: FastMCP):
    await connect()
    yield {}
    await disconnect()


mcp = FastMCP(
    "C2CDirect",
    host="0.0.0.0",
    port=8001,
    streamable_http_path="/mcp",
    stateless_http=True,
    json_response=True,
    token_verifier=C2CTokenVerifier(),
    lifespan=lifespan,
    auth=AuthSettings(
        issuer_url=settings.jwt_issuer or "https://localhost",
        resource_server_url="http://localhost:8080/mcp",
        required_scopes=["mcp:tools"],
    ),
)


@mcp.tool(description="List this tenant's screened jobs, ordered by strongest fit.")
async def search_jobs(ctx: Context, minimum_score: int = 0) -> list[dict]:
    if not 0 <= minimum_score <= 100:
        raise ValueError("minimum_score must be between 0 and 100")

    async def operation(principal):
        rows = await list_jobs(principal.tenant_id, minimum_score)
        return [
            {key: value.isoformat() if hasattr(value, "isoformat") else value for key, value in row.items()}
            for row in rows
        ]

    return await run_premium_tool(ctx.request_id, "search_jobs", "jobs:read", operation)


@mcp.tool(description="Explain a job's C2C fit with cited evidence. This does not contact anyone.")
async def explain_match(ctx: Context, posting: dict, profile: dict | None = None) -> dict:
    async def operation(_principal):
        return explain_match_impl(posting, profile)

    return await run_premium_tool(ctx.request_id, "explain_match", "jobs:read", operation)


@mcp.tool(description="Move one tenant-owned job through the application pipeline.")
async def update_job_status(ctx: Context, job_id: str, status: str) -> dict:
    if status not in VALID_JOB_STATUSES:
        raise ValueError("Invalid job status")
    parsed_job_id = UUID(job_id)

    async def operation(principal):
        try:
            await move_job(principal.tenant_id, parsed_job_id, status)
        except KeyError as exc:
            raise ValueError("Job not found in this tenant") from exc
        return {"updated": True, "job_id": job_id, "status": status}

    return await run_premium_tool(ctx.request_id, "update_job_status", "jobs:write", operation)


@mcp.tool(description="Draft outreach for human approval. The tool never sends the message.")
async def draft_outreach(ctx: Context, job_id: str, message: str) -> dict:
    async def operation(_principal):
        return request_outreach_impl(job_id, message, approved=False)

    return await run_premium_tool(ctx.request_id, "draft_outreach", "outreach:draft", operation)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
