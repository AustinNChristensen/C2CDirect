import httpx
import pytest

from app.connectors import ConnectorTarget, connector_for


async def fetch(adapter, body):
    async def handler(request):
        assert request.url.host in {
            "boards-api.greenhouse.io",
            "api.lever.co",
            "api.ashbyhq.com",
        }
        return httpx.Response(200, json=body)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        target = ConnectorTarget(adapter=adapter, slug="acme", organization_name="Acme")
        return await connector_for(target, client).fetch(target)


@pytest.mark.asyncio
async def test_greenhouse_normalizes_official_posting():
    observations = await fetch(
        "greenhouse",
        {
            "jobs": [
                {
                    "id": 42,
                    "requisition_id": "REQ-42",
                    "title": "Senior AI Engineer",
                    "updated_at": "2026-08-28T12:00:00Z",
                    "location": {"name": "Remote"},
                    "absolute_url": "https://boards.greenhouse.io/acme/jobs/42",
                    "content": "<p>Twelve month contract building production AI systems with Python, agents, APIs, and PostgreSQL.</p>",
                }
            ]
        },
    )
    assert observations[0].requisition_id == "REQ-42"
    assert observations[0].end_client_name == "Acme"
    assert observations[0].provider_slug == "employer-greenhouse-acme"
    assert "<p>" not in observations[0].posting.description


@pytest.mark.asyncio
async def test_lever_normalizes_hourly_compensation():
    observations = await fetch(
        "lever",
        [
            {
                "id": "job-1",
                "text": "Staff AI Engineer",
                "descriptionPlain": "Long contract description for production AI platforms using Python, TypeScript, MCP, and PostgreSQL.",
                "hostedUrl": "https://jobs.lever.co/acme/job-1",
                "categories": {"location": "Remote", "commitment": "Contract"},
                "salaryRange": {"min": 140, "max": 170, "interval": "hour"},
            }
        ],
    )
    assert observations[0].posting.rate_min == 140
    assert observations[0].provider_slug == "employer-lever-acme"
    assert observations[0].engagement_type == "Contract"


@pytest.mark.asyncio
async def test_ashby_ignores_unlisted_jobs_and_reads_compensation():
    observations = await fetch(
        "ashby",
        {
            "jobs": [
                {"id": "hidden", "isListed": False},
                {
                    "id": "visible",
                    "isListed": True,
                    "title": "Principal Agent Engineer",
                    "descriptionPlain": "Build a secure agent platform with Python, FastAPI, MCP, evaluation, and observability for enterprise customers.",
                    "location": "Remote - US",
                    "jobUrl": "https://jobs.ashbyhq.com/acme/visible",
                    "employmentType": "Contract",
                    "compensation": {"min": 150, "max": 185, "interval": "hour"},
                },
            ]
        },
    )
    assert len(observations) == 1
    assert observations[0].posting.rate_max == 185
    assert observations[0].provider_slug == "employer-ashby-acme"
