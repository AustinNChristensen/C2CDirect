"""Bounded web discovery through a user-selected search service."""

import html
import re
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from .graph import screening_graph
from .ingestion_service import ingest_batch
from .models import JobPostingIn, N8NBatch, SearchProfile

DEFAULT_ENDPOINTS = {
    "tavily": "https://api.tavily.com",
    "brave": "https://api.search.brave.com",
}
REVIEWED_JOB_HOSTS = (
    "ashbyhq.com",
    "greenhouse.io",
    "jobvite.com",
    "lever.co",
    "myworkdayjobs.com",
    "smartrecruiters.com",
    "workable.com",
)


def public_connection(connection: dict | None) -> dict:
    provider = connection.get("provider", "disabled") if connection else "disabled"
    return {
        "provider": provider,
        "base_url": connection.get("base_url", "") if connection else "",
        "api_key_configured": bool(connection and connection.get("api_key")),
        "configured": provider != "disabled" and bool(
            (connection or {}).get("base_url") or DEFAULT_ENDPOINTS.get(provider)
        ),
        "updated_at": connection.get("updated_at") if connection else None,
    }


def build_query(profile: SearchProfile, focus: str = "", domains: list[str] | None = None) -> str:
    roles = focus.strip() or " OR ".join(f'"{role}"' for role in ("AI Engineer", "Software Engineer"))
    skills = " OR ".join(profile.core_skills[:3] + profile.ai_skills[:3])
    domain_filter = " ".join(f"site:{domain}" for domain in (domains or []))
    return " ".join(
        part for part in (
            f"({roles})",
            f"({skills})" if skills else "",
            '(contract OR contractor OR "corp to corp" OR C2C)',
            domain_filter,
        ) if part
    )[:1200]


async def test_search_connection(connection: dict) -> dict:
    try:
        results = await search(connection, "software engineer contract", 1)
        return {"ok": True, "message": "Search service connected", "sample_results": len(results)}
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        return {"ok": False, "message": "Could not reach the search service", "error": type(exc).__name__}


async def search(connection: dict, query: str, limit: int) -> list[dict]:
    provider = connection.get("provider", "disabled")
    base_url = (connection.get("base_url") or DEFAULT_ENDPOINTS.get(provider, "")).rstrip("/")
    api_key = connection.get("api_key", "")
    if provider == "disabled" or not base_url:
        raise ValueError("Web search is not configured")
    if provider in {"tavily", "brave"} and not api_key:
        raise ValueError("The selected search provider requires an API key")
    async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
        if provider == "tavily":
            response = await client.post(
                f"{base_url}/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "search_depth": "advanced",
                    "max_results": limit,
                    "include_raw_content": "markdown",
                },
            )
            response.raise_for_status()
            return response.json().get("results", [])[:limit]
        if provider == "brave":
            response = await client.get(
                f"{base_url}/res/v1/web/search",
                params={"q": query, "count": limit},
                headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
            )
            response.raise_for_status()
            return response.json().get("web", {}).get("results", [])[:limit]
        if provider == "searxng":
            response = await client.get(
                f"{base_url}/search",
                params={"q": query, "format": "json", "categories": "general"},
            )
            response.raise_for_status()
            return response.json().get("results", [])[:limit]
    raise ValueError("Unsupported search provider")


def reviewed_job_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and any(
        host == suffix or host.endswith(f".{suffix}") for suffix in REVIEWED_JOB_HOSTS
    )


def plain_text(document: str) -> str:
    document = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", document, flags=re.IGNORECASE | re.DOTALL)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", document)).split())


async def hydrate_results(results: list[dict]) -> list[dict]:
    """Fetch full text only from reviewed ATS hosts; never follow redirects."""
    hydrated = []
    async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
        for result in results:
            item = dict(result)
            url = str(item.get("url", ""))
            existing = str(item.get("raw_content") or "")
            if len(existing) >= 500 or not reviewed_job_url(url):
                hydrated.append(item)
                continue
            try:
                response = await client.get(
                    url,
                    headers={"Accept": "text/html", "User-Agent": "C2CDirect-Core/0.1"},
                )
                content_type = response.headers.get("content-type", "").lower()
                if response.status_code == 200 and "text/html" in content_type:
                    text = plain_text(response.text[:1_000_000])
                    if len(text) >= 100:
                        item["raw_content"] = text[:30000]
            except httpx.HTTPError:
                pass
            hydrated.append(item)
    return hydrated


def company_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").removeprefix("www.")
    segments = [segment for segment in parsed.path.split("/") if segment]
    if host in {"jobs.lever.co", "boards.greenhouse.io", "jobs.ashbyhq.com", "apply.workable.com"} and segments:
        return segments[0].replace("-", " ").replace("_", " ").title()
    labels = host.split(".")
    label = labels[1] if len(labels) > 2 and labels[0] in {"apply", "career", "careers", "job", "jobs"} else labels[0]
    return label.replace("-", " ").title()


def postings_from_results(results: list[dict]) -> list[JobPostingIn]:
    postings = []
    seen = set()
    for result in results:
        url = str(result.get("url", "")).strip()
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or url in seen:
            continue
        seen.add(url)
        title = str(result.get("title") or "Contract opportunity").strip()[:180]
        raw = result.get("raw_content") or result.get("content") or result.get("description") or ""
        description = " ".join(str(raw).split())[:30000]
        if len(description) < 40:
            description = f"{title}. Public web search result from {parsed.hostname}. {description}".strip()
        if len(description) < 40:
            continue
        company = company_from_url(url)
        postings.append(
            JobPostingIn(
                source="web_scout",
                source_url=url,
                title=title,
                company=company or "Unknown employer",
                description=description,
                location="Unknown",
            )
        )
    return postings


async def run_web_scout(
    tenant_id: str,
    connection: dict,
    profile: SearchProfile,
    focus: str,
    domains: list[str],
    max_results: int,
) -> dict:
    query = build_query(profile, focus, domains)
    results = await search(connection, query, max_results)
    results = await hydrate_results(results)
    postings = postings_from_results(results)
    if not postings:
        return {"query": query, "discovered": len(results), "screened": 0, "persisted": 0, "duplicates": 0, "qualified": 0, "job_ids": []}
    batch = N8NBatch(
        run_id=f"web-scout:{uuid4()}",
        jobs=postings,
        retain_all_in_pipeline=True,
    )
    summary = await ingest_batch(
        tenant_id,
        batch,
        screening_graph,
        provider="web_scout",
        profile=profile,
    )
    return {"query": query, "discovered": len(results), **summary}
