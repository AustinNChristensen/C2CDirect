# Provider and job provenance

Status: **Accepted**
Last updated: 2026-08-29

## Core rule

Provenance MUST be stored at both the provider level and the individual job level. Provider reputation
is a prior, never proof that a particular job is direct, accurate, current, C2C-compatible, or well
paid. Job-specific evidence MUST be able to strengthen or override the provider baseline.

## Provider provenance record

A provider represents an organization or delivery channel that produces job observations. It SHOULD
contain:

- stable provider ID, canonical name, domains, and provider type;
- provider type: end client, employer ATS, prime vendor, MSP/VMS, staffing vendor, aggregator,
  marketplace, email channel, public agency, or manual source;
- ownership and relationship evidence;
- supported intake mechanism and its authorization/terms status;
- typical vendor depth and direct-source capability;
- C2C reliability and rate-transparency history;
- canonical-link, duplicate, and stale-post performance;
- recruiter-domain verification policy;
- response, submission, interview, and misrepresentation outcomes when lawfully available;
- baseline source-authority score, confidence, evidence references, and last verified time.

Provider metrics MUST distinguish measured history from manually assigned policy. Aggregate hosted
metrics MUST meet privacy thresholds and MUST NOT expose another tenant's private activity.

## Job observation

Every sighting of a job is an immutable observation from one provider. It SHOULD contain:

- provider ID and provider-native job/requisition identifier;
- observed URL, canonical URL candidate, and observation time;
- source title, company/client names, description hash, location, engagement type, and rate data;
- recruiter identity/domain when supplied;
- source-specific evidence and attribution requirements;
- payload/content hash and parser version;
- normalization warnings and confidence.

Raw observations MUST NOT be overwritten merely because a later provider supplies different values.
Sensitive message contents MAY be retained only under the tenant's data policy.

## Canonical opportunity

A canonical opportunity groups observations believed to represent the same requisition. It SHOULD
contain:

- canonical opportunity ID and selected canonical observation;
- end client and the evidence supporting that identity;
- known chain of end client, MSP/VMS, prime vendor, subvendors, recruiter, and delivery provider;
- minimum, maximum, unit, employment basis, and confidence for compensation;
- C2C status, evidence, and confidence;
- estimated vendor-layer count with lower/upper bounds when uncertain;
- freshness, first seen, last seen, and last verified timestamps;
- provenance completeness and source-quality scores;
- unresolved questions and contradictory observations.

Canonicalization MUST retain links to every contributing observation. A better source MAY replace the
canonical observation without changing the canonical opportunity ID.

## Provenance chain

The chain is an ordered graph, not a free-form label. Nodes identify organizations/channels; edges
describe relationships such as `owns_requisition`, `manages_program`, `prime_vendor`, `subvendor`,
`recruits_for`, `published_by`, or `observed_via`. Each edge carries evidence, confidence, first/last
seen, and verification method.

Layer count MUST count commercial intermediaries between the worker's company and the end client. The
delivery channel itself does not add a layer unless it participates commercially.

## Confidence and evidence

Confidence MUST be represented separately from the value it qualifies. Allowed evidence classes
SHOULD include official posting, provider API, verified-domain communication, signed/authorized user
confirmation, consistent cross-source observation, heuristic inference, and unverified claim.

No score may transform `unknown` into `confirmed` without supporting evidence.
