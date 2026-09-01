# C2CDirect specifications

This directory is the durable source of truth for how C2CDirect behaves, why important choices were
made, and which choices have deliberately not been made. Product behavior and implementation should
conform to accepted specifications. Supporting research belongs in `docs/`; current implementation
details belong in code and operational runbooks.

## Structure

- `product/`: product principles, commercial boundaries, and user promises.
- `domain/`: canonical concepts, records, invariants, and scoring semantics.
- `ingestion/`: source intake, normalization, provenance, and quality gates.
- `decisions/`: numbered architecture and product decision records.
- `open-questions.md`: unresolved choices with the evidence needed to resolve them.
- `intentional-non-decisions.md`: choices deliberately deferred or rejected for the current scope.
- `templates/decision-record.md`: required format for new decisions.

## Authority and language

The words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are normative. When code and
an accepted specification disagree, the discrepancy must be resolved explicitly: either correct the
implementation or supersede the specification with a reviewed decision record.

Specification statuses:

- **Draft**: proposed and safe to discuss, but not yet binding.
- **Accepted**: binding for new implementation and changes.
- **Implemented**: accepted and verified in the product.
- **Superseded**: retained for history and linked to its replacement.
- **Rejected**: considered and intentionally not adopted.

## Making a decision

1. Describe the user or system problem and the constraints.
2. Separate facts and evidence from assumptions.
3. List realistic alternatives and their tradeoffs.
4. Record the decision, consequences, security/privacy impact, open questions, and validation plan.
5. Give the record a sequential identifier; never reuse or silently rewrite an accepted decision.
6. Update affected normative specifications and tests in the same change when practical.

Small reversible implementation details do not require a decision record. Decisions that affect data
ownership, tenancy, security, billing, licensing, public interfaces, provider trust, automated actions,
or the open-core boundary do.

## Current specification map

- [Product principles](product/principles.md)
- [Provider and job provenance](domain/provenance.md)
- [Intake quality and canonicalization](ingestion/job-quality.md)
- [Curated source registry](ingestion/source-registry.md)
- [C2C source network](ingestion/c2c-source-network.md)
- [2026-08-29 live source evaluation](ingestion/2026-08-29-live-source-evaluation.md)
- [Open-core and hosted-product boundary](decisions/0001-open-core-boundary.md)
- [Two-level provenance](decisions/0002-provider-and-job-provenance.md)
- [Human approval for external action](decisions/0003-human-approval-boundary.md)
- [Authorized mailbox intake](decisions/0004-authorized-mailbox-intake.md)
- [Personal-first C2C sourcing](decisions/0005-personal-first-sourcing.md)
- [Open questions](open-questions.md)
- [Intentional non-decisions](intentional-non-decisions.md)
