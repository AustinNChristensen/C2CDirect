# Architecture

## Request path

Source adapters or n8n → FastAPI/Pydantic normalization → prompt-injection and PII guardrails → deterministic eligibility and fit scoring → preflight cost gate → hybrid retrieval with citations → evaluation → human approval boundary → PostgreSQL persistence → dashboard/action queue.

## Tenant and authorization boundary

An OIDC access token supplies `user_id`, `tenant_id`, and roles. The API sets `app.tenant_id` inside every database transaction. PostgreSQL row-level-security policies enforce tenant ownership even if an application query accidentally omits a tenant predicate. Authorization remains server-side.

## Agent control plane

Every run records a trace ID, tenant, operation, graph/prompt/model versions, graph steps, tool calls, latency, retries, token usage, estimated and actual cost, policy decisions, evaluation results, approvals, and status. OpenTelemetry is the portable telemetry contract; LangSmith or another backend is optional.

Cost control uses three stages: estimate before invocation, atomically reserve tenant budget, and reconcile using provider-reported usage. Limits exist at tenant/day, feature/month, run cost, tokens, graph steps, retry count, and approval threshold.

## Retrieval

RAG is limited to evidence-backed fit explanations and outreach grounded in the user's résumé, strategy, portfolio, and approved interaction history. Documents are split into overlapping, traceable chunks. Local development uses deterministic lexical/semantic hybrid ranking; production can replace that implementation with PostgreSQL full-text search plus pgvector without changing the evidence contract. Results carry source identifiers and citations, and evaluation measures groundedness, citation coverage, rank relevance, schema validity, and safety.

## Safety and human control

Untrusted job text is inspected before scoring or retrieval. Prompt-injection patterns quarantine the run; sensitive identifiers are redacted before downstream processing. Agent tools use an allowlist and reject secret-bearing arguments. External actions such as recruiter outreach cannot proceed without explicit human approval.

## Models and protocols

The model router selects an economy, standard, premium, or deterministic-local target based on task complexity, configured providers, and data sensitivity. The first provider adapters are OpenAI and Anthropic; sensitive content can be forced through local rules. MCP exposes narrowly scoped matching and outreach tools using the same validation and approval rules as the API.

FastAPI provides a Server-Sent Events screening route so the interface can display graph progress without adding a separate queue or cache dependency.

## Verification

CI runs unit, graph-path, safety, cost, retrieval, MCP, routing, evaluation, and dataset-regression tests. The AI core must remain above 85% statement coverage; the current suite measures 98%.

## Deployment

The web app can be hosted independently from the API. The API requires PostgreSQL and an HTTP deployment target capable of running Python. Production should use managed secrets, TLS, encrypted backups, outbound allowlists, and an OTLP collector.
