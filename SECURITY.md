# Security Policy

Report vulnerabilities privately through GitHub's **Report a vulnerability** form. Do not publish
vulnerability details in a public issue. If private vulnerability reporting is unavailable, wait for
a private reporting channel to be restored before sharing sensitive details.

Include the affected version, impact, reproduction steps, and any suggested mitigation. Do not attach
real résumés, recruiter messages, credentials, or customer records. Maintainers will acknowledge a
valid report through the private channel and coordinate remediation and disclosure there.

## Controls

- OIDC/JWT verification with issuer, audience, expiry, and signature checks
- Tenant isolation enforced with PostgreSQL row-level security
- Signed, idempotent Stripe and n8n webhook processing
- Encrypted secrets and no credentials committed to source
- Deny-by-default tool permissions and outbound network allowlists
- MCP scope checks, server-side Pro/Team entitlement enforcement, atomic daily quotas, and
  tenant-isolated metadata-only call audits
- Preflight token/cost/step/retry budgets to limit denial-of-wallet risk
- Metadata-only telemetry by default; redact personal and proprietary content
- Immutable audit events for approvals, policy changes, exports, and destructive actions
- Dependency, container, and secret scanning in CI before public release

## Required production review

Threat-model authentication, billing, prompt injection, tool authorization, SSRF, webhook replay, data retention, exports/deletion, backup restoration, and incident response before processing customer data.
