# Intake provider plan

C2CDirect should ingest only through documented APIs, public feeds, or inbox access explicitly
authorized by the mailbox owner. It should not bypass access controls, automate logged-in web pages,
or depend on undocumented scraping.

## Recommended first wave

| Priority | Provider | Intake route | Why it belongs |
|---:|---|---|---|
| 1 | Greenhouse | Public Job Board API | Direct-from-employer published jobs, full descriptions, departments, offices, and stable IDs without authentication for GET requests. |
| 2 | Lever | Public Postings API | Direct published jobs with plain-text descriptions, workplace type, compensation when supplied, and stable hosted/apply URLs. |
| 3 | Ashby | Public Job Postings API | Direct published jobs with optional compensation and structured locations. |
| 4 | SmartRecruiters | Public Posting API | Company-scoped published postings with query and location filters. |
| 5 | Workable | Public account endpoint or scoped API | Public published-job endpoint is suitable for selected employer boards; account API requires an employer-issued `r_jobs` token. |
| 6 | Personio | Public XML career feed | Published openings include descriptions and explicitly support `freelance` employment type. |
| 7 | Gmail | OAuth mailbox watch plus message retrieval | Transport for verified direct-client and prime-vendor recruiter messages already authorized by the user. Gmail supports mailbox watches and push delivery through Pub/Sub. |
| 8 | Microsoft Outlook | OAuth Microsoft Graph mail notifications | Equivalent authorized transport for Microsoft 365 and Outlook users; Graph supports mail APIs and change notifications. |
| 9 | LinkedIn | Authorized daily job-alert email | Discovery coverage without automating LinkedIn pages. Alerts must be canonicalized back to the employer or controlling vendor when possible. |
| 10 | Dice | Authorized job-alert and recruiter email | Strong U.S. contract coverage but variable source depth. Require strict contract/C2C/rate filters and provenance verification before promotion. |

## Expansion wave

| Priority | Provider | Intake route | Notes |
|---:|---|---|---|
| 11 | Adzuna | Search API | Broad U.S. discovery source with structured search. Resolve listings to a canonical employer/prime source and retain required attribution. |
| 12 | Jooble | Search API | Broad discovery source with useful structured fields; do not infer directness from the listing alone. |
| 13 | Careerjet | Public search API | Additional discovery and deduplication evidence; partner/affiliate terms require review before production use. |
| 14 | Remote OK | Public JSON/RSS feed | Remote-heavy discovery; verify attribution, source chain, and feed terms before promotion. |
| 15 | Remotive | Public jobs API | Remote technology discovery; cache and respect documented usage limits. |
| 16 | Jobicy | Public jobs API/RSS | Additional remote discovery feed with scheduled ingestion. |
| 17 | We Work Remotely | Public RSS | Official public feeds requiring attribution; canonicalize outbound postings when possible. |
| 18 | Himalayas | Public JSON API/RSS | Structured remote jobs, salary/location restrictions, cursor pagination, daily refresh, and explicit attribution rules. |
| 19 | USAJOBS | Search API | Authoritative federal source but lower C2C yield; requires an API key. |
| 20 | CareerOneStop | Jobs API | U.S. Department of Labor-backed job data; requires registered API access and may still contain downstream listings. |

## Rollout recommendation

Start with a curated registry of Greenhouse, Lever, Ashby, SmartRecruiters, Workable, and Personio
employer boards, then add verified direct-client and prime-vendor recruiter email through Gmail or
Outlook. Use LinkedIn, Dice, and aggregators for discovery only until Signal resolves the canonical
source and vendor chain. Poll feeds conservatively, retain provider attribution, store provider IDs and
canonical URLs, and send every normalized batch through the same tenant-bound replay and fingerprint
controls.

Do not add automatic application submission in the intake phase. Application or outreach actions must
remain separate, scoped, audited, rate-limited, and human-approved.

## Official references

- [Gmail push notifications](https://developers.google.com/workspace/gmail/api/guides/push)
- [Microsoft Graph mail API](https://developer.microsoft.com/en-us/graph/rest-api)
- [LinkedIn job alerts](https://www.linkedin.com/help/linkedin/answer/a506444)
- [Dice job alerts](https://www.dice.com/support/candidate-help/finding-a-job/job-alerts-and-setting-them-up.html)
- [Adzuna API](https://developer.adzuna.com/overview)
- [Jooble REST API](https://help.jooble.org/en/support/solutions/articles/60001448238-rest-api-documentation)
- [Careerjet API](https://www.careerjet.com/docs/api/careerjet)
- [Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html)
- [Lever Postings API](https://github.com/lever/postings-api)
- [Ashby Job Postings API](https://developers.ashbyhq.com/docs/public-job-posting-api)
- [SmartRecruiters Posting API](https://developers.smartrecruiters.com/docs/endpoints)
- [Workable careers API guidance](https://help.workable.com/hc/en-us/articles/115012771647-Using-the-Workable-API-to-create-a-careers-page)
- [Personio open-position feed](https://developer.personio.de/docs/retrieving-open-job-positions)
- [Remote OK feeds](https://remoteok.com/remote-api-jobs)
- [Remotive public API](https://support.remotive.com/en/article/list-remote-jobs-public-api-105pww2/)
- [Jobicy API/RSS](https://jobicy.com/jobs-rss-feed)
- [We Work Remotely RSS](https://weworkremotely.com/remote-job-rss-feed)
- [Himalayas jobs API](https://himalayas.app/docs/remote-jobs-api)
- [USAJOBS API](https://developer.usajobs.gov/api-reference/)
- [CareerOneStop Web APIs](https://www.careeronestop.org/Developers/WebAPI/web-api.aspx)
