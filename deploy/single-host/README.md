# Single-host deployment

This profile runs C2CDirect on one server without exposing Docker, PostgreSQL, or n8n directly to
the internet. Cloudflare Tunnel is the only public ingress; Caddy listens on loopback for local
verification.

## Safe first boot

1. Install Docker Desktop or another compatible Docker runtime.
2. Copy `.env.example` to `.env` and generate unique secrets. Never commit `.env`.
3. Keep `AUTH_DISABLED_FOR_LOCAL_DEV=true` and do **not** configure a public tunnel yet.
4. Run `docker compose --env-file deploy/single-host/.env -f deploy/single-host/compose.yml up -d --build` from the repository root.
5. Check `docker compose --env-file deploy/single-host/.env -f deploy/single-host/compose.yml ps`.
6. Visit `http://127.0.0.1:8080` on the server.
7. Run the full API tests and verify database persistence across a restart.

For a smaller private install without n8n, MCP, email OAuth, or a public tunnel, use
`./scripts/setup-core.sh` from the repository root. It supports a zero-cost deterministic mode or an
OpenAI-compatible model endpoint, and exposes live tenant spending in Control Room.

## Before public exposure

- Implement and test tenant provisioning for authenticated users.
- Set `AUTH_DISABLED_FOR_LOCAL_DEV=false` and configure Auth0 issuer, audience, and JWKS URL.
- Configure Cloudflare Access for `automation.<domain>` so only the owner can reach n8n.
- Configure the public site and API hostnames in one remotely managed Cloudflare Tunnel, both targeting `http://caddy:8080`.
- Put API rate limits and request-size limits at Cloudflare.
- Configure Stripe only after authentication and tenant ownership tests pass.
- Run a backup and perform a restore test.

Then set `CLOUDFLARE_TUNNEL_TOKEN` and start the tunnel profile:

`docker compose --env-file deploy/single-host/.env -f deploy/single-host/compose.yml --profile tunnel up -d`

## Backups

Run `deploy/single-host/backup-postgres.sh` daily. Set `C2CDIRECT_BACKUP_DIR` to an external or encrypted offsite-backed directory. A backup on the same internal disk is not sufficient. The script retains 14 days by default.

## Automatic recovery

Every service uses `restart: unless-stopped`. Configure Docker to start when the server account logs in, prevent system sleep, enable restart after power failure, and use a UPS when practical.

## Local security verification

- Only Caddy binds a host port, and it binds `127.0.0.1:8080` only. PostgreSQL, n8n, the API, web, and MCP services remain private on the Compose network.
- The API connects as the non-superuser `c2cdirect_app` role. The PostgreSQL bootstrap account is reserved for migrations, backup, and restore operations.
- Authenticated JWT claims are mapped to durable internal tenant and user IDs before any budget reservation or job write. Row-level-security policies are forced and must pass cross-tenant read and write denial tests.
- MCP is Streamable HTTP at `/mcp`; it rejects missing or invalid bearer tokens and honors issued scopes instead of granting blanket access. Database-backed tools enforce Pro/Team entitlement, an atomic daily plan allowance, tenant RLS, and metadata-only audit records. The generated local bearer token and `MCP_ALLOW_LOCAL_PREMIUM_DEV` override are only for private local testing and are disabled automatically when OIDC authentication is enabled.
- The web interface reads persisted opportunities from the same-origin `/api/v1/jobs` route. Caddy removes the `/api` prefix before proxying to FastAPI.
- n8n intake requires both an authenticated tenant identity and the private webhook secret. Each batch ID is tenant-namespaced and payload-bound; safe retries return the saved summary, altered replays are rejected, existing job fingerprints skip screening, and every new result is persisted. Results below `MINIMUM_INGEST_SCORE` or explicitly rejecting C2C are retained as `passed` instead of appearing as active leads.

## Restore procedure

Never restore over the live database as a first step. Validate into a temporary database:

1. Stop application writes or take a fresh backup from a consistent maintenance window.
2. Create a temporary database such as `c2cdirect_restore_verify` using the PostgreSQL bootstrap account.
3. Run `pg_restore --no-owner --no-privileges` into that temporary database.
4. Compare application row counts, n8n schema tables, extensions, and a representative tenant-owned record.
5. Drop only the temporary validation database after verification.

The backup script writes with mode-600 defaults, validates the dump catalog before publishing the final filename, and retains 14 days. Configure `C2CDIRECT_BACKUP_DIR` on an encrypted external or offsite-backed volume before treating backups as operational. A same-disk backup is only a restore test artifact.

## Public-ingress gate and rate limits

Keep the tunnel profile stopped until all gates pass. At public ingress, configure Cloudflare rate limits by authenticated API identity where available, with IP fallback: 30 screening requests per minute, 120 read requests per minute, and a 1 MiB request-body ceiling. Return `429` with a retry window and monitor rejects without logging request content. MCP must have a separate 60-request-per-minute bearer-token limit. Keep tighter application cost, token, graph-step, and retry budgets as the denial-of-wallet backstop; edge limits do not replace them.

Auth0 issuer, audience, JWKS URL, Cloudflare Access policy, tunnel token, encrypted/offsite backup destination, and alert destinations are owner-controlled prerequisites. Do not start the tunnel until those values are configured and the authenticated smoke tests are rerun with `AUTH_DISABLED_FOR_LOCAL_DEV=false`.
