# Live source evaluation — 2026-08-29

## Run

- Scope: localhost-only single-host deployment
- Public exposure: disabled
- Sources queried: reviewed priority 1–3 Greenhouse and Ashby boards
- Maximum selected postings: 200
- Result: 200 selected, 199 canonical jobs created, 1 existing job enriched
- Canonicalization behavior: the duplicate was not rescreened or duplicated

## Quality result

| Measure | Count |
| --- | ---: |
| Explicit C2C confirmation | 2 |
| C2C likely from contract language | 12 |
| C2C unknown | 186 |
| Needs-verification lane | 83 |
| Low-quality lane | 117 |
| Rate disclosed | 2 |

The result validates an important product decision: authoritative employer feeds provide strong source
provenance but weak commercial evidence for C2C searches. Missing rates are not labeled as low pay;
they remain verification work. Low scores primarily reflect missing C2C/rate evidence or weak profile
fit, not distrust of the first-party source.

## Follow-up decision

Keep first-party feeds as the canonical job anchor, but use authorized recruiter and job-alert email to
collect rate, engagement type, controlling vendor, and end-client evidence. Never promote an employer
ATS posting to confirmed C2C merely because it is direct.
