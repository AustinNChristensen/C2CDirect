from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
from pydantic_settings import BaseSettings, SettingsConfigDict

from .auth import Principal


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql://postgres:postgres@localhost:5432/c2cdirect"


settings = DatabaseSettings()
pool: asyncpg.Pool | None = None


async def connect():
    global pool
    pool = await asyncpg.create_pool(
        settings.database_url, min_size=1, max_size=10, command_timeout=30
    )


async def disconnect():
    global pool
    if pool:
        await pool.close()
        pool = None


async def provision_principal(principal: Principal) -> Principal:
    """Resolve signed external identity claims to durable internal tenant/user IDs."""
    if not pool:
        raise RuntimeError("Database is not connected")
    role = "owner" if "owner" in principal.roles else "member"
    async with pool.acquire() as conn, conn.transaction():
        identity = await conn.fetchrow(
            """
            SELECT internal_tenant_id, internal_user_id
              FROM provision_identity($1, $2, $3, $4, $5)
            """,
            principal.issuer,
            principal.tenant_id,
            principal.user_id,
            principal.email,
            role,
        )
        tenant_id = identity["internal_tenant_id"]
        user_id = identity["internal_user_id"]
    return Principal(
        str(user_id),
        str(tenant_id),
        principal.email,
        principal.roles,
        principal.issuer,
        principal.scopes,
    )


@asynccontextmanager
async def tenant_connection(tenant_id: str) -> AsyncIterator[asyncpg.Connection]:
    if not pool:
        raise RuntimeError("Database is not connected")
    async with pool.acquire() as conn, conn.transaction():
        await conn.execute("SELECT set_config('app.tenant_id', $1, true)", tenant_id)
        yield conn
