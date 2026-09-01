# Community and hosted product boundary

## Self-hosted community core

The community edition is intended to include:

- FastAPI and PostgreSQL/pgvector application core
- tenant provisioning and forced row-level security
- explainable C2C, rate, skill, provenance, and quality scoring
- job, provider, recruiter, and pipeline data models
- connector interfaces and reviewed example adapters
- an empty-by-default workspace with user-initiated first-party board scans, bounded Web Scout
  discovery, authorized mailbox intake, and direct CSV/JSON import
- n8n ingestion contracts and inactive example workflows
- local Streamable HTTP MCP with explicit development controls
- human approval for outreach and application actions
- Docker Compose deployment, backup guidance, tests, and evaluation cases

Self-hosters retain their own data and operate their own identity, infrastructure, source agreements,
models, backups, monitoring, and compliance program.

## Paid hosted service

A future hosted service may charge for value that requires ongoing operations or network scale:

- managed infrastructure, upgrades, backups, recovery, monitoring, and support
- managed OIDC, billing, rate limits, audit retention, and authenticated remote MCP
- continuously maintained authorized job, mailbox, VMS, MSP, and prime-vendor connectors
- source reconciliation, freshness monitoring, and higher-confidence provenance investigation
- privacy-safe provider and recruiter reputation derived from sufficient aggregate evidence
- team workflows, service identities, premium model execution, and higher usage limits

Hosted differentiation must come from service, operations, maintained integrations, and defensible
network intelligence. It must not depend on deliberately breaking self-hosting or hiding core formats.

Core does not ship with pre-filled opportunities or a managed job feed. A self-hoster chooses and
operates every source, including a self-hosted SearXNG or user-connected Tavily/Brave search tool.
The hosted product may provide continuously managed sourcing, maintained
connectors, and curated opportunity delivery as paid operational services.

## Data and automation promises

- Raw tenant data is never shared across tenants.
- Provider-network membership is not represented as a direct relationship.
- Logged-in scraping or access-control bypass is not an integration strategy.
- External outreach, submission, or application requires human approval.
- Public examples use fictional data and do not imply that a displayed opportunity is currently open.
