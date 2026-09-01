# Demonstration guide

This walkthrough demonstrates C2CDirect without production credentials or third-party job data.

## Start the local stack

1. Copy `backend/.env.example` to `backend/.env`.
2. Set `AUTH_DISABLED_FOR_LOCAL_DEV=true` and replace `N8N_WEBHOOK_SECRET=replace-me` with a local
   random value.
3. Start PostgreSQL, the API, and n8n with `docker compose up -d --build`.
4. Start the interface with `pnpm install --frozen-lockfile && pnpm dev`.
5. Open `http://localhost:3000` and confirm `http://localhost:8000/health` returns healthy status.

Do not expose this development configuration to the internet.

## Load fictional opportunities

From a second terminal, provide the same local webhook secret without printing it:

```bash
export C2C_DEMO_WEBHOOK_SECRET='your-local-value'
python3 scripts/seed_demo.py
unset C2C_DEMO_WEBHOOK_SECRET
```

The dataset deliberately contains:

- a strong AI engineering C2C opportunity with a disclosed target rate;
- a JavaScript/TypeScript role that needs rate verification;
- an explicit W2-only rejection that should not enter the active action queue.

Re-running the command is safe: the batch ID and payload are stable, so the ingestion contract returns
the prior result instead of duplicating jobs.

## Suggested portfolio narrative

1. Show deterministic C2C and rate screening with explainable reasons and risks.
2. Show employer/provider provenance and why an ATS is not treated as the employer.
3. Show the PostgreSQL tenant boundary and forced row-level security tests.
4. Show n8n as a controlled intake orchestrator rather than an unaudited automation engine.
5. Show authenticated Streamable HTTP MCP and its server-side entitlements and audit trail.
6. Explain why applications and recruiter outreach remain behind human approval.
7. Explain the open-core boundary in `COMMUNITY.md`.

The fictional records are demonstrations only and must never be presented as open positions.
