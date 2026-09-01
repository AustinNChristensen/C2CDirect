# ADR-0002: Store provenance for providers and job observations

Status: **Accepted**
Date: 2026-08-29

## Context

The same provider can deliver both excellent direct opportunities and low-quality reposts. Conversely,
an aggregator can reveal an opportunity whose canonical source is excellent. A single source field or
provider reputation score cannot represent this accurately.

## Decision

Signal will store provider provenance, immutable provider-specific job observations, canonical
opportunities, and evidence-bearing provenance-chain edges. Provider quality supplies a baseline prior;
job-level evidence determines the opportunity's final provenance assessment.

Canonical opportunities will retain all observations and may change their selected canonical source
without changing identity. Confidence will be stored independently from asserted values.

## Alternatives rejected

- **Only score providers:** too coarse and vulnerable to reputation inheritance.
- **Only score jobs:** loses useful historical provider behavior and adapter governance.
- **Overwrite one job row:** destroys contradictory evidence and source history.
- **Treat every sighting as a job:** creates duplicate board noise and repeated screening cost.

## Consequences

The data model is more explicit and requires canonicalization logic. In return, rankings are
explainable, duplicates become evidence, and provider performance can improve future intake decisions.
