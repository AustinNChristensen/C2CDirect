# 0005 — Personal-first C2C sourcing

Status: Implemented

## Context

C2CDirect may later support a staffing business and a paid hosted product. Its immediate purpose is
to help its owner win a high-quality C2C engagement and demonstrate production-grade FastAPI,
PostgreSQL, n8n, provenance, and MCP engineering.

## Decision

The current product MUST optimize for one consultant's opportunity pipeline. It MAY track providers,
recruiters, requisitions, follow-ups, and source evidence. It MUST NOT add candidate representation,
payroll, timesheets, employer-of-record, or client billing workflows yet.

A provider listed in a recognized supplier network is a **relationship target**, not proof that C2C
Signal or its owner has a direct client, prime-vendor, or VMS relationship. That relationship MUST be
recorded as verified only after direct evidence is retained.

The daily n8n action queue MAY rank jobs and due recruiter follow-ups. It MUST NOT send outreach,
submit a candidate, or apply for a role without human approval.

## Consequences

- The system remains useful immediately without pretending to be a staffing agency.
- Provider and recruiter data can support a hosted premium tier without mixing tenant data.
- Agency operations remain a future, separately reviewed expansion.

## Validation

- Provider targets expose evidence and access state.
- Recruiter contacts and action queues are tenant-isolated.
- The n8n workflow is read-only and inactive by default.
- Direct ATS jobs identify the employer as provider, not the ATS software vendor.
