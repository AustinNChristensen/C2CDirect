# Intentional non-decisions

Status: **Accepted record of current scope**
Last updated: 2026-08-29

The following choices are deliberately not being made yet:

- **No commercial-license template or external code contributions yet.** The community core is
  AGPL-3.0-only, but commercial terms and a contributor agreement wait for qualified legal review.
- **No automatic application or outreach sending.** Research and drafting are implemented behind a
  human approval boundary.
- **No universal provider blacklist.** Provider and job evidence are modeled separately; insufficient
  data must not become an irreversible reputation judgment.
- **No learned ranking weights yet.** Initial weights are explainable policy defaults until a
  representative, consented evaluation set exists.
- **No claim that employer ATS postings accept C2C.** They establish source proximity, not engagement
  terms.
- **No prohibited scraping.** Logged-in browser automation and access-control bypass are not fallback
  connector strategies.
- **No public tunnel yet.** Authenticated tenant isolation, backup/restore, rate limits, MCP security,
  and owner-controlled production prerequisites remain launch gates.
- **No AWS, Kubernetes, or Redis dependency.** They are not required for the current single-host/local
  architecture.
- **No cross-tenant raw-data sharing.** Any future hosted aggregate reputation requires explicit
  privacy thresholds and a superseding decision.
