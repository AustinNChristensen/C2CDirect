# Intake quality and canonicalization

Status: **Accepted**
Last updated: 2026-08-29

## Source preference

When multiple observations represent the same opportunity, Signal SHOULD prefer:

1. an official end-client career system or posting;
2. a verified end-client recruiter;
3. a verified prime vendor controlling or filling the requisition;
4. a known MSP/VMS record;
5. an aggregator that links to one of the above;
6. an unverified staffing repost;
7. an unknown multi-layer repost.

Direct employer postings can establish requisition existence but do not establish C2C eligibility.
Verified prime-vendor evidence MAY therefore supplement an employer posting without replacing it as
the canonical source.

## Intake stages

Every provider adapter MUST pass through:

1. authorization and terms check;
2. tenant resolution;
3. replay/idempotency claim;
4. payload validation and normalization;
5. observation fingerprinting;
6. exact and probabilistic duplicate detection;
7. canonical-source resolution;
8. provenance and confidence assessment;
9. C2C, rate, fit, safety, and freshness evaluation;
10. persistence with evidence;
11. active-board, verification-queue, or low-quality disposition.

Duplicate observations SHOULD enrich one canonical opportunity rather than produce multiple board
cards or consume repeated AI screening budget.

## Quality lanes

- **Direct/Prime:** end client or prime relationship verified; zero or one commercial intermediary;
  rate and C2C meet configured confidence thresholds.
- **Needs verification:** potentially valuable but client, rate, C2C status, freshness, or vendor chain
  remains materially uncertain.
- **Low quality:** multiple/unknown layers, stale or contradictory data, hidden client without adequate
  evidence, rate below the tenant floor, or misleading source behavior.

Tenants MAY tune thresholds, but hosted defaults MUST NOT silently promote unknown provenance to the
Direct/Prime lane.

## Ranking

Ranking MUST keep role fit separate from opportunity quality. A recommended composite MAY include:

`role fit + source authority + C2C confidence + rate quality + freshness - layer penalty - stale/repost penalty - missing-client penalty`

Initial layer penalties are policy defaults, not learned facts:

- direct end client: `0`
- verified prime vendor: `-8`
- MSP/VMS: `-15`
- second-tier subcontractor: `-30`
- unknown or multiple layers: `-45`

Scores MUST expose their components and evidence. Outcome data SHOULD calibrate weights only after a
representative, consented evaluation set exists.

## Hard gates

Signal MUST quarantine or suppress observations with prohibited acquisition, unresolved malicious
content, known scams, altered replay identifiers, or invalid tenant attribution. It SHOULD suppress
active-board placement for expired jobs, explicit non-C2C roles when C2C is required, and rates below
the tenant's hard floor.

Provider research and initial rollout ordering are maintained in
[`docs/INTAKE_PROVIDERS.md`](../../docs/INTAKE_PROVIDERS.md).
