"""Direct-source synchronization into canonical tenant opportunities."""

import re

import httpx

from .connectors import ConnectorTarget, connector_for
from .graph import screening_graph
from .ingestion import enrich_posting
from .models import SearchProfile
from .provenance import assess_provenance, canonical_key
from .repositories import (
    find_job_by_canonical_key,
    finish_source_sync_run,
    record_job_observation,
    start_source_sync_run,
    upsert_job,
    upsert_provider,
)
from .usage import active_policy, metered_screening


async def sync_target(
    tenant_id: str,
    target: ConnectorTarget,
    profile: SearchProfile | None = None,
    client: httpx.AsyncClient | None = None,
    max_observations: int | None = None,
    relevant_only: bool = False,
    query: str | None = None,
) -> dict:
    owns_client = client is None
    active_client = client or httpx.AsyncClient(timeout=30, follow_redirects=True)
    active_profile = profile or SearchProfile()
    run_id = await start_source_sync_run(tenant_id, target.slug, target.adapter, query)
    try:
        connector = connector_for(target, active_client)
        provider = connector.provider_for(target)
        provider_id = await upsert_provider(tenant_id, provider)
        observations = await connector.fetch(target)
        received = len(observations)
        if query:
            observations = [item for item in observations if observation_matches_query(item, query)]
        if relevant_only:
            observations = sorted(
                (item for item in observations if observation_relevance(item, active_profile) >= 3),
                key=lambda item: observation_relevance(item, active_profile),
                reverse=True,
            )
        if max_observations is not None:
            observations = observations[:max_observations]
        created = 0
        enriched = 0
        observation_ids = []
        for observation in observations:
            observation = observation.model_copy(
                update={"posting": enrich_posting(observation.posting)}
            )
            existing = await find_job_by_canonical_key(tenant_id, canonical_key(observation))
            result = await metered_screening(
                tenant_id,
                screening_graph,
                observation.posting,
                active_profile,
                active_policy(),
                operation=f"source_{target.adapter}",
            )
            screened_job = result["result"]
            c2c_status = screened_job.c2c_status
            fit_score = screened_job.fit_score
            job_id = await upsert_job(tenant_id, screened_job)
            if existing:
                enriched += 1
            else:
                created += 1
            assessment = assess_provenance(
                provider,
                observation,
                c2c_status,
                fit_score,
                active_profile.min_rate,
            )
            observation_ids.append(
                await record_job_observation(
                    tenant_id, provider_id, job_id, observation, assessment
                )
            )
        result = {
            "adapter": target.adapter,
            "target": target.slug,
            "received": received,
            "selected": len(observations),
            "skipped": received - len(observations),
            "created": created,
            "enriched": enriched,
            "observation_ids": observation_ids,
        }
        await finish_source_sync_run(
            tenant_id, run_id, received=received, selected=len(observations),
            created=created, enriched=enriched,
        )
        return result
    except Exception as exc:
        await finish_source_sync_run(tenant_id, run_id, error_code=type(exc).__name__)
        raise
    finally:
        if owns_client:
            await active_client.aclose()


def observation_relevance(observation, profile: SearchProfile) -> int:
    """Cheap pre-screen that limits persistence to plausibly relevant engineering work."""
    posting = observation.posting
    title = posting.title.lower()
    text = f"{title} {posting.description}".lower()
    location = posting.location.lower()
    score = 0
    if any(term in title for term in ("engineer", "developer", "architect", "consultant")):
        score += 2
    if any(term in title for term in ("ai", "ml", "agent", "platform", "full stack", "backend")):
        score += 2
    skill_hits = sum(skill.lower() in text for skill in profile.core_skills + profile.ai_skills)
    score += min(3, skill_hits)
    if any(term in location for term in ("remote", "united states", "usa", "denver", "utah")):
        score += 1
    if any(term in title for term in ("sales", "account executive", "recruiter", "marketing")):
        score -= 4
    return score


def observation_matches_query(observation, query: str) -> bool:
    """Match an explicit founder search against title, company, and posting text.

    This intentionally searches only the reviewed source registry. It does not
    pretend to be a general-web or logged-in job-board search.
    """
    terms = [term for term in re.findall(r"[a-z0-9+#.]+", query.lower()) if len(term) > 1]
    if not terms:
        return True
    posting = observation.posting
    haystack = f"{posting.title} {posting.company} {posting.description}".lower()
    return all(term in haystack for term in terms)


async def sync_registry(
    tenant_id: str,
    targets: list[ConnectorTarget],
    profile: SearchProfile | None = None,
    *,
    total_limit: int = 200,
    per_target_limit: int = 20,
    query: str | None = None,
) -> dict:
    """Synchronize a reviewed registry with explicit bounds and partial-failure reporting."""
    active_profile = profile or SearchProfile()
    results = []
    remaining = total_limit
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        for target in targets:
            if not target.enabled or remaining <= 0:
                continue
            try:
                result = await sync_target(
                    tenant_id,
                    target,
                    active_profile,
                    client,
                max_observations=min(per_target_limit, remaining),
                relevant_only=True,
                query=query,
                )
            except httpx.HTTPError as exc:
                results.append(
                    {"adapter": target.adapter, "target": target.slug, "error": type(exc).__name__}
                )
                continue
            results.append(result)
            remaining -= result["selected"]
    return {
        "limit": total_limit,
        "selected": total_limit - remaining,
        "created": sum(item.get("created", 0) for item in results),
        "enriched": sum(item.get("enriched", 0) for item in results),
        "query": query,
        "targets": results,
    }
