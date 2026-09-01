"""Apply versioned SQL migrations and provision the least-privileged app role."""

import asyncio
import os
from pathlib import Path

import asyncpg

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"


async def migrate() -> None:
    database_url = os.environ.get("MIGRATION_DATABASE_URL", "")
    app_password = os.environ.get("APP_DATABASE_PASSWORD", "")
    if not database_url or not app_password:
        raise RuntimeError("MIGRATION_DATABASE_URL and APP_DATABASE_PASSWORD are required")
    conn = await asyncpg.connect(database_url, command_timeout=120)
    try:
        await conn.execute("SELECT pg_advisory_lock(hashtext('c2cdirect:migrations'))")
        quoted_password = await conn.fetchval("SELECT quote_literal($1)", app_password)
        exists = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='c2cdirect_app')")
        if exists:
            await conn.execute(f"ALTER ROLE c2cdirect_app LOGIN PASSWORD {quoted_password}")
        else:
            await conn.execute(
                f"CREATE ROLE c2cdirect_app LOGIN PASSWORD {quoted_password} "
                "NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT"
            )
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations(
                 version text PRIMARY KEY,
                 applied_at timestamptz NOT NULL DEFAULT now()
               )"""
        )
        for path in sorted(MIGRATIONS.glob("*.sql")):
            applied = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM schema_migrations WHERE version=$1)", path.name
            )
            if applied:
                continue
            async with conn.transaction():
                await conn.execute(path.read_text())
                await conn.execute(
                    "INSERT INTO schema_migrations(version) VALUES($1)", path.name
                )
            print(f"Applied {path.name}", flush=True)
    finally:
        try:
            await conn.execute("SELECT pg_advisory_unlock(hashtext('c2cdirect:migrations'))")
        finally:
            await conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
