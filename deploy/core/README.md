# C2CDirect Core deployment

This directory contains the private, self-hosted C2CDirect Core stack. It starts PostgreSQL,
repeatable schema migrations, the API, a durable acquisition worker, the web application, and a
local Caddy gateway. Private Web Scout search through SearXNG is optional.

## Install or upgrade

From the repository root, run:

```bash
./scripts/setup-core.sh
```

The first run creates `deploy/core/.env` with private generated credentials. Later runs preserve
that configuration, apply every pending migration once, rebuild changed services, and restart the
stack. Core listens only on `127.0.0.1:8080` by default. Set `CORE_PORT` in the private `.env` file
if that port is already used.

The default deterministic brain has no model cost. Setup can instead connect an OpenAI-compatible
endpoint such as Ollama, LM Studio, vLLM, or LocalAI. Configuration secrets are encrypted before
storage and are never returned to the browser.

## First use

1. Open **Setup** at `http://127.0.0.1:8080` and save a matching profile with at least one role, location, and skill.
2. Test and save an AI brain, or keep deterministic screening.
3. Import CSV/JSON using the upload interface in Setup (see `examples/demo-jobs.json` for a fictional sample), run the reviewed public-source scan, connect an authorized recruiter inbox, or configure Web Scout.
4. Watch background runs in Acquisition history. Failed and cancelled runs can be retried. Active runs support a safe stop that finishes the current item before recording cancellation.

Core intentionally starts with no jobs. Managed job delivery is reserved for the hosted product.

## Back up and verify recovery

Create a compressed PostgreSQL backup:

```bash
./deploy/core/backup.sh
```

Verify a backup by restoring it into an isolated temporary database without changing live data:

```bash
./deploy/core/restore-verify.sh /path/to/c2cdirect-backup.dump
```

The Control Room also provides a tenant-scoped JSON export for portable job, profile, decision,
recruiter, and run-history data. Résumé file contents are intentionally excluded.

## Production exposure

The default install is single-user and loopback-only, with local authentication explicitly enabled.
Do not expose it directly to the internet. Before remote access, set
`AUTH_DISABLED_FOR_LOCAL_DEV=false`, configure OIDC/JWT validation, or place it behind a trusted
identity proxy and set `TRUSTED_PROXY_IDENTITY_HEADER=true`. Terminate TLS at the access layer and
keep PostgreSQL, the worker, and SearXNG private.

Hosted mode rejects model and search endpoints on private networks to prevent server-side request
forgery. Loopback and LAN model endpoints remain available only in explicit local-development mode.

## Operations

- Health check: `GET http://127.0.0.1:8080/api/health` (via gateway; API container serves this at `/health`)
- Upgrade: rerun `./scripts/setup-core.sh`
- Stop: `docker compose --env-file deploy/core/.env -f deploy/core/compose.yml down`
- Clean-install verification: `./scripts/core-smoke.sh`

Never commit `deploy/core/.env`, backups, résumé files, OAuth credentials, or database volumes.
