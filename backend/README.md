# C2CDirect API

The backend is intentionally portfolio-grade: FastAPI exposes structured endpoints, Pydantic validates every job, LangGraph orchestrates safety, screening, cost control, hybrid retrieval, evaluation, and approval, and an n8n-secured webhook supports scheduled ingestion. Retrieval is deterministic locally and uses the same traceable chunk/citation contract intended for LangChain + PostgreSQL/pgvector in production.

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload --port 8000
```

Open `/docs` for the generated API explorer. Post jobs to `/v1/screen`, or send batches from n8n to `/v1/ingest/n8n` with the `X-Webhook-Secret` header.

Core onboarding endpoints:

- `GET|PUT|DELETE /v1/model-connection` reads or saves the tenant model configuration without ever
  returning the API key.
- `POST /v1/model-connection/test` checks an OpenAI-compatible `/v1/models` endpoint before saving.
- `POST /v1/jobs/import` accepts an owner-authenticated batch of up to 250 jobs and routes it through
  the same validation, screening, deduplication, and persistence path used by automated intake.
- `POST /v1/acquisition-runs` queues durable public-source, web, inbox, or import work. Run endpoints
  expose history, retry, and cooperative cancellation without tying work to a browser request.
- `PATCH /v1/jobs/{id}/corrections` saves corrected commercial terms and location, while
  `POST /v1/jobs/{id}/rescreen` reapplies the current profile and learned decision feedback.
- `GET /v1/export` returns the current tenant's portable Core data without résumé bytes or secrets.
- `GET|PUT|DELETE /v1/web-search-connection` configures an encrypted SearXNG, Tavily, or Brave
  search tool, while `POST /v1/web-scout/search` runs bounded, profile-guided discovery and sends
  gathered public requisitions through the tenant's AI screening pipeline.

Model API keys are encrypted with `C2CDIRECT_CONFIG_ENCRYPTION_KEY`, which the guided Core setup
generates automatically.

For a completely self-hosted stack, point Web Scout at a private SearXNG instance. Search runs only
when an owner requests it; Core does not crawl continuously or ship with pre-filled results.

Use `/v1/screen/stream` for Server-Sent Events progress. Run `python -m app.mcp_server` to expose the safe `explain_match` and approval-aware `request_outreach` MCP tools.

The AI-core unit suite has a CI-enforced 85% minimum and currently covers 98% of the graph, guardrails, retrieval, provider routing, MCP tools, evaluations, cost controls, and scoring code.

## Recommended n8n workflow

Schedule Trigger → approved job-source connectors/RSS/email intake → normalize fields → HTTP POST batch to FastAPI → filter `fit_score >= 75` → save to database → daily digest/recruiter follow-up queue.

Respect each source's terms, robots rules, and API restrictions. Prefer official feeds, recruiter emails, licensed aggregators, and manually supplied postings over unauthorized scraping.
