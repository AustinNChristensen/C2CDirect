# ADR-0001: Open-core and hosted-product boundary

Status: **Implemented**
Date: 2026-08-29

## Context

Signal must support a public, self-hostable repository while preserving a valuable managed offering.
Artificially crippling the community edition would undermine trust and adoption; giving away managed
operations and cross-network intelligence would make the hosted business difficult to sustain.

## Decision

The public core will contain the domain models, tenant isolation, ingestion contracts, provenance
schema, deterministic scoring, provider adapter interfaces, local deployment, and human approval
boundaries required for meaningful self-hosting.

The hosted product may charge for managed infrastructure, continuously maintained connectors,
cross-provider canonicalization, privacy-safe provider/recruiter reputation, operational monitoring,
managed authentication and billing, premium model execution, support, and authenticated remote MCP or
agent access.

Server-side entitlements MUST protect paid hosted capabilities. The community repository is licensed
under `AGPL-3.0-only`; the copyright holder MAY offer separate commercial licenses. Project names,
logos, and hosted-service branding remain governed separately by the trademark guidelines.

## Consequences

Community users can understand, run, and extend the core. Hosted differentiation must come from
service quality, network intelligence, operations, and convenience rather than hidden data formats or
deliberate incompatibility.
