import pytest

from app import web_scout
from app.models import SearchProfile


def test_query_uses_profile_focus_and_domain_bounds():
    query = web_scout.build_query(
        SearchProfile(core_skills=["TypeScript"], ai_skills=["LangGraph"]),
        "Agentic AI Engineer",
        ["jobs.example.com"],
    )
    assert "Agentic AI Engineer" in query
    assert "TypeScript" in query
    assert "LangGraph" in query
    assert "site:jobs.example.com" in query
    assert "corp to corp" in query


def test_results_become_safe_https_postings_and_dedupe():
    results = [
        {
            "title": "Senior AI Engineer - Contract",
            "url": "https://jobs.example.com/req/123",
            "raw_content": "Remote contract opportunity accepting C2C with Python and LangGraph. " * 2,
        },
        {
            "title": "Duplicate",
            "url": "https://jobs.example.com/req/123",
            "content": "duplicate result with enough description content to otherwise be accepted",
        },
        {
            "title": "Unsafe",
            "url": "http://localhost/internal",
            "content": "must never become an intake posting even with sufficient content",
        },
    ]
    postings = web_scout.postings_from_results(results)
    assert len(postings) == 1
    assert postings[0].source == "web_scout"
    assert postings[0].company == "Example"
    assert postings[0].source_url.host == "jobs.example.com"


def test_only_reviewed_https_job_hosts_can_be_hydrated():
    assert web_scout.reviewed_job_url("https://jobs.lever.co/acme/123")
    assert web_scout.reviewed_job_url("https://boards.greenhouse.io/acme/jobs/123")
    assert not web_scout.reviewed_job_url("https://example.com/internal")
    assert not web_scout.reviewed_job_url("http://jobs.lever.co/acme/123")


@pytest.mark.asyncio
async def test_web_scout_routes_discovery_through_ingestion(monkeypatch):
    async def found(*_args, **_kwargs):
        return [
            {
                "title": "AI Engineer Contract",
                "url": "https://careers.example.com/jobs/1",
                "content": "Remote C2C contract using Python, RAG, and LangGraph for production systems.",
            }
        ]

    captured = {}

    async def ingested(tenant_id, batch, graph, **kwargs):
        captured.update(tenant_id=tenant_id, batch=batch, graph=graph, kwargs=kwargs)
        return {"persisted": 1, "duplicates": 0, "qualified": 1, "job_ids": ["job"]}

    monkeypatch.setattr(web_scout, "search", found)
    monkeypatch.setattr(web_scout, "ingest_batch", ingested)
    profile = SearchProfile()
    result = await web_scout.run_web_scout(
        "tenant",
        {"provider": "searxng", "base_url": "https://search.example.com"},
        profile,
        "AI Engineer",
        [],
        10,
    )
    assert result["discovered"] == 1
    assert result["persisted"] == 1
    assert captured["tenant_id"] == "tenant"
    assert captured["kwargs"]["provider"] == "web_scout"
    assert captured["kwargs"]["profile"] is profile
