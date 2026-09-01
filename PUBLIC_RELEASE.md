# Public release checklist

C2CDirect is maintained privately while its public community edition is prepared. This file is the
release gate: do not mirror or publish the repository until every blocking item is complete.

## Blocking publication details

- [x] Adopt `AGPL-3.0-only` for the community repository.
- [x] Adopt interim trademark guidelines separating code rights from project branding.
- [x] Choose the final product and repository name: C2CDirect.
- [x] Choose the public repository owner: `AustinNChristensen`.
- [x] Keep `directc2c.com` as the current canonical site domain during the C2CDirect rebrand.
- [x] Enable GitHub private vulnerability reporting before the public announcement.

## Technical release gate

- [x] No production secrets or customer records are tracked in the current tree.
- [x] Build the public candidate as a new one-commit repository with no private Git history.
- [x] Environment templates contain placeholders only.
- [x] Generated resumes, local output, database dumps, and private deployment values are ignored.
- [x] Fictional demo records are clearly marked and contain no recruiter or applicant data.
- [x] Community and hosted-product boundaries are documented.
- [x] CI runs lint, builds, tests, and secret scanning.
- [x] Add a repeatable full-history secret, license, lint, build, test, and Compose release gate.
- [x] Review locked dependency and referenced container-image licenses; record the result in
  `docs/THIRD_PARTY_LICENSES.md`.
- [x] Repeat `./scripts/release-gate.sh` on the exact commit immediately before publication.
- [x] Add the owner-approved `LICENSE`, licensing explanation, notice, and trademark guidelines.
- [x] Create `AustinNChristensen/C2CDirect` from the approved candidate without changing private Origin.
- [x] Enable branch protection, secret scanning, dependency alerts, and private vulnerability reports.

## Beta rehearsal

- [x] Complete a clean Docker Core smoke test covering migrations, onboarding, import, screening,
  persistence, backup creation, and isolated restore verification.
- [ ] Have a new user follow only the public setup guide and record unclear steps.
- [ ] Validate at least one user-configured model, one real Web Scout provider, and one authorized
  mailbox OAuth connection with non-production test data.

## Never publish

- `.env` files, OAuth credentials, API keys, tunnel tokens, signing keys, or database passwords
- database backups or Docker volumes
- resumes, recruiter messages, mailbox content, customer data, or production job descriptions
- live tenant identifiers, access tokens, MCP bearer tokens, or telemetry payloads

The public release should be a reviewed mirror or export of an approved commit. The private Origin
remains the operational source of truth until the owner deliberately changes that policy.
