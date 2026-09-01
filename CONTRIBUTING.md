# Contributing

External code contributions are temporarily paused while the project finalizes a contributor
agreement that preserves both AGPL distribution and optional commercial licensing. Please
open an issue for proposed changes instead of submitting implementation code. Documentation feedback,
reproducible bug reports, and responsible security reports are welcome.

Once contributions reopen, changes must remain focused, include tests, avoid job-source integrations
that violate source terms, and document new telemetry or personal-data collection. All graph changes
must include an evaluation case and cost-impact note.

Run the web build, Python tests, formatting, type checks, and migration review before submitting. Never include production credentials, customer records, résumés, recruiter messages, or proprietary job descriptions in fixtures.

Changes affecting data ownership, tenancy, security, billing, licensing, public interfaces, provider
trust, automated external actions, or the open-core boundary must update `specs/` and include or
supersede a numbered decision record. Accepted decisions are never silently rewritten.
