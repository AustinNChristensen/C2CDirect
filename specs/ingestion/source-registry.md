# Curated source registry

## Purpose

The source registry is the reviewed top of the pipeline. A valid public API endpoint is necessary but
not sufficient: each target also carries priority, geography, C2C signal, tags, and a written rationale.
Runtime synchronization accepts only fixed Greenhouse, Lever, and Ashby hosts and a validated slug;
arbitrary URLs are not executable connector configuration.

## Priority policy

1. Agent/AI consultancies and small first-party boards with unusually strong profile fit.
2. AI infrastructure, developer platforms, remote engineering companies, and delivery consultancies.
3. Larger authoritative boards used only for selective technical discovery.
4. Broad remote boards that are useful for market intelligence but produce substantial noise.
5. Reserved for disabled or experimental sources.

`c2cdirect` describes prior engagement likelihood and never overrides posting evidence. An employer
ATS is close to the job owner, but it does not imply that the employer accepts C2C.

## Bounded synchronization

- Owner role and `jobs:write` scope are required.
- A run may select no more than 200 postings and no more than 50 per target.
- The default run selects at most 20 relevant engineering postings per source.
- Role/skill relevance is applied before persistence; commercial quality is assessed after screening.
- Partial source failures are recorded in the result without discarding successful targets.
- Repeated canonical opportunities are enriched with another observation instead of rescreened.

## Registry maintenance

Review endpoint validity, terms status, geography, and rationale before enabling a target. Disable a
source rather than silently changing its slug. Record material policy changes as an ADR.
