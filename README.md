# C2CDirect

C2CDirect is an open-core opportunity intelligence system for independent engineers and consultancies pursuing high-rate corp-to-corp work. It turns job alerts and recruiter messages into structured, explainable opportunities; ranks them against a candidate profile; tracks the commercial pipeline; and converts recurring skill gaps into portfolio work.

**Find the contract. Verify the chain. Win the work.**

> **Open-core community edition:** this repository is licensed under `AGPL-3.0-only`. The hosted
> product is differentiated through managed operations, maintained integrations, and network
> intelligence. See [LICENSING.md](LICENSING.md), [TRADEMARKS.md](TRADEMARKS.md), and
> [PUBLIC_RELEASE.md](PUBLIC_RELEASE.md) before publishing a mirror.

The product name is written **C2CDirect** in prose and interfaces. See [BRANDING.md](BRANDING.md) for
the wordmark, tagline, edition names, and compatibility-sensitive legacy identifiers.

## What is implemented

- Next.js opportunity, pipeline, editable profile/résumé, Setup, and live Control Room interfaces
- FastAPI/Pydantic API and OpenAPI contract
- LangGraph screening graph with deterministic C2C/rate/skill scoring
- Hybrid retrieval with traceable chunks, citations, metadata filters, and a pgvector boundary
- Prompt-injection detection, PII redaction, tool allowlists, and human approval for outreach
- OpenAI-compatible bring-your-own-model runtime with deterministic fail-safe screening
- Durable background acquisition runs with retry, cooperative cancellation, and run history
- Empty-by-default Core intake through reviewed public sources, authorized recruiter inboxes,
  CSV/JSON import, and optional profile-guided Web Scout search
- Decision feedback and job-field corrections that influence explainable re-screening
- Tenant-scoped data export plus automated PostgreSQL backup and isolated restore verification
- Authenticated Streamable HTTP MCP with tenant-scoped job search, match explanation,
  pipeline updates, approval-gated outreach drafts, per-scope authorization, plan quotas,
  and metadata-only audit events
- Server-Sent Events endpoint for live graph progress without an external queue
- Cost-aware model routing and preflight budget gates
- OpenTelemetry-compatible agent traces
- PostgreSQL tenant isolation with row-level security
- Transactional daily-budget reservations and reconciliation
- JWT/OIDC authentication boundary
- Stripe subscription webhook and plan entitlements
- n8n batch ingestion contract
- Retrieval/evaluation boundaries and automated tests
- CI-enforced unit coverage for the complete AI core (85% minimum; currently 98%)
- Docker Compose development stack

## Run locally

### Simplest: C2CDirect Core

**Prerequisites:** Docker Engine or Docker Desktop must be installed and running. Visit [docs.docker.com](https://docs.docker.com/get-docker/) for installation instructions.

Clone the public repository and run the guided setup script:

```bash
git clone https://github.com/AustinNChristensen/C2CDirect.git
cd C2CDirect
./scripts/setup-core.sh
```

The setup script is interactive and will prompt you for:

1. **Model configuration**: Press Enter at the model URL prompt for zero-cost deterministic screening, or provide an OpenAI-compatible endpoint (such as Ollama at `http://host.docker.internal:11434/v1`, vLLM, LM Studio, or LocalAI). If you provide a URL, you'll be asked for the model name, optional API key, and cost estimates.

2. **Web Scout search**: Choose whether to include private SearXNG search (default: yes).

The script generates private database credentials, runs migrations, builds and starts all Core services, and waits for health checks to pass before reporting the URL. Core listens at `http://127.0.0.1:8080` by default.

**Non-interactive installation:** Set `C2CDIRECT_NONINTERACTIVE=true` to skip prompts and use
environment variables instead: `C2CDIRECT_MODEL_BASE_URL`, `C2CDIRECT_MODEL_NAME`,
`C2CDIRECT_MODEL_API_KEY`, `C2CDIRECT_MODEL_INPUT_COST_PER_MILLION`,
`C2CDIRECT_MODEL_OUTPUT_COST_PER_MILLION`, and `C2CDIRECT_WEB_SEARCH` (`Y`/`n`).

After launch, open **Setup** at `http://127.0.0.1:8080` for the shortest first-run path:

1. Confirm your matching profile and commercial targets (role, location, skills, minimum rate).
2. Choose deterministic rules or test and save an OpenAI-compatible AI brain configuration.
3. Import jobs using **CSV/JSON upload** in Setup. Use `examples/demo-jobs.json` for a quick start with fictional sample opportunities, or prepare your own job data following the CSV/JSON format described below.

**CSV/JSON format**: Upload files with headers/fields including `title`, `company`, `description`, `location`, `rate_min`, `rate_max`, `source`, `source_url`, `contract_duration`, `engagement_type`, and `recruiter_email`. JSON may be an array of job objects or an object containing a `jobs` array. See `examples/demo-jobs.json` for a working example with fictional opportunities.

Core starts with an empty opportunity database by design. It does not include a managed or pre-filled job feed. After completing Setup, you can:

- Import CSV/JSON files (up to 250 jobs per batch)
- Run profile-guided scans against reviewed public first-party ATS boards
- Connect an authorized read-only recruiter inbox for automated intake
- Use Web Scout through SearXNG, Tavily, or Brave for profile-guided job search

Every acquired job goes through validation, commercial-term extraction, deduplication, screening, and persistence using your selected model or deterministic rules. Control Room reports runtime status, token usage, spend estimates, recent runs, and budget utilization. API keys are encrypted and never returned to the browser.

Core acquisition runs are durable: you can leave the page, inspect history, retry failures, or request a safe stop. See [deploy/core/README.md](deploy/core/README.md) for upgrades, authentication, backups, verified restores, and production-exposure guidance.

**Note:** The portfolio-friendly walkthrough at [docs/DEMO.md](docs/DEMO.md) describes the full **development stack** (`docker compose up` + `pnpm dev` + n8n), not the Core deployment. Follow that guide only if you're developing C2CDirect itself or demonstrating the complete architecture. For self-hosting, use Core.

### Development stack

1. Copy `backend/.env.example` to `backend/.env` and set `AUTH_DISABLED_FOR_LOCAL_DEV=true`.
2. Set a strong `N8N_ENCRYPTION_KEY` in your shell or `.env`.
3. Run `docker compose up --build`.
4. Run `pnpm install && pnpm dev` for the web app.
5. Open the web app, API docs at `http://localhost:8000/docs`, and n8n at `http://localhost:5678`.

For a guided, portfolio-friendly walkthrough using fictional data, follow
[docs/DEMO.md](docs/DEMO.md). No third-party account or paid model is required for the deterministic
screening demonstration.

## Community and hosted editions

The self-hosted core is a real product, not a crippled sample. It includes the data model, tenant
isolation, provenance, deterministic screening, local deployment, connector interfaces, n8n
contracts, and human-approval boundaries. The hosted business is differentiated by managed
operations, maintained authorized connectors, cross-provider intelligence, support, managed identity
and billing, and authenticated remote MCP. See [COMMUNITY.md](COMMUNITY.md) for the complete boundary.

## Safety and data-source policy

Use official APIs, licensed feeds, RSS, recruiter email alerts, manual URL submission, and user-authorized inbox integrations. Do not bypass access controls or violate a source's terms. Never place résumé contents, job descriptions, prompts, or model outputs into unrestricted telemetry; production defaults should capture metadata and hashes, with content capture explicitly opted into and redacted.

## Repository status

The community code is licensed under GNU AGPL version 3 only. Optional commercial licenses may be
offered separately by the copyright holder; none is included in this repository. The canonical public
source is [AustinNChristensen/C2CDirect](https://github.com/AustinNChristensen/C2CDirect).

The community repository remains self-hostable. Hosted remote MCP and agent access are paid Pro/Team
features enforced from the tenant plan on the server; client UI state and token possession alone never
grant access. Local maintainers can exercise the same MCP surface privately with the explicit
`MCP_ALLOW_LOCAL_PREMIUM_DEV` development switch, which is ignored whenever OIDC authentication is
enabled.

See [ARCHITECTURE.md](ARCHITECTURE.md), [SECURITY.md](SECURITY.md), [SUPPORT.md](SUPPORT.md),
[CONTRIBUTING.md](CONTRIBUTING.md), and [ROADMAP.md](ROADMAP.md).
The researched, terms-aware connector sequence is in
[docs/INTAKE_PROVIDERS.md](docs/INTAKE_PROVIDERS.md).
Normative product behavior, accepted decisions, open questions, and intentional non-decisions live in
the [specification index](specs/README.md).

## AI quality checks

The AI stack is tested as one controlled system: guardrails → deterministic scoring → cost gate →
hybrid retrieval → cited evaluation → approval decision. The suite also tests individual components,
unsafe inputs, PII handling, model fallback behavior, MCP tool authorization, retrieval chunking, and
dataset regressions.

```bash
cd backend
pytest tests --cov=app.graph --cov=app.guardrails --cov=app.retrieval \
  --cov=app.model_routing --cov=app.mcp_tools --cov=app.evaluations \
  --cov=app.costs --cov=app.scoring --cov-report=term-missing --cov-fail-under=85
```
