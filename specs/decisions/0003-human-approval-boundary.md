# ADR-0003: Human approval for external commercial actions

Status: **Accepted**
Date: 2026-08-29

## Context

Agentic access is valuable for research, ranking, pipeline management, and drafting. Applications and
recruiter communications can create reputational, privacy, and commercial commitments.

## Decision

Agents may ingest, research, normalize, compare, score, explain, save, classify, and draft. Sending
outreach, submitting applications, accepting terms, scheduling on the user's behalf, or making another
external commitment requires explicit human approval scoped to the specific action and payload.

Approval events MUST be authenticated, tenant-bound, auditable, expiring, and non-replayable. A broad
MCP scope alone is not approval.

## Consequences

C2CDirect can provide high-leverage agentic assistance while preserving user control. Fully autonomous
application submission is outside the accepted product boundary unless this ADR is superseded after a
dedicated policy, security, abuse, and user-experience review.
