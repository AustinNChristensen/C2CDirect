"""Tenant-safe, replay-safe intake pipeline shared by webhook providers."""

from hashlib import sha256
from uuid import UUID

from .ingestion import content_fingerprint, enrich_posting
from .models import C2CStatus, N8NBatch, SearchProfile
from .repositories import (
    claim_ingestion_event,
    complete_ingestion_event,
    find_job_by_fingerprint,
    move_job,
    upsert_job,
)
from .usage import active_policy, metered_screening


def batch_payload_hash(batch: N8NBatch) -> str:
    payload = batch.model_dump_json(exclude_none=False)
    return sha256(payload.encode()).hexdigest()


async def ingest_batch(
    tenant_id: str,
    batch: N8NBatch,
    screening_graph,
    minimum_score: int = 50,
    provider: str = "n8n",
    profile: SearchProfile | None = None,
) -> dict:
    state, previous = await claim_ingestion_event(
        tenant_id, provider, batch.run_id, batch_payload_hash(batch)
    )
    if state == "completed":
        return {**(previous or {}), "replayed": True}
    if state != "claimed":
        raise RuntimeError("Ingestion batch is already being processed")

    screened = 0
    persisted = 0
    duplicates = 0
    qualified = 0
    job_ids: list[str] = []
    try:
        for raw_posting in batch.jobs:
            posting = enrich_posting(raw_posting)
            fingerprint = content_fingerprint(posting)
            existing_id = await find_job_by_fingerprint(tenant_id, fingerprint)
            if existing_id and not batch.refresh_existing:
                duplicates += 1
                job_ids.append(existing_id)
                continue
            result = await metered_screening(
                tenant_id,
                screening_graph,
                posting,
                profile or SearchProfile(),
                active_policy(),
                operation=f"ingest_{provider}",
            )
            screened_job = result["result"]
            screened += 1
            job_id = await upsert_job(tenant_id, screened_job)
            persisted += 1
            if existing_id:
                duplicates += 1
            job_ids.append(job_id)
            is_qualified = (
                screened_job.fit_score >= minimum_score
                and screened_job.c2c_status != C2CStatus.rejected
            )
            if is_qualified:
                qualified += 1
            if batch.retain_all_in_pipeline:
                await move_job(tenant_id, UUID(job_id), "new")
            elif not is_qualified:
                await move_job(tenant_id, UUID(job_id), "passed")
        summary = {
            "run_id": batch.run_id,
            "received": len(batch.jobs),
            "screened": screened,
            "persisted": persisted,
            "duplicates": duplicates,
            "qualified": qualified,
            "retained_in_pipeline": len(batch.jobs) if batch.retain_all_in_pipeline else qualified,
            "job_ids": job_ids,
            "replayed": False,
        }
        await complete_ingestion_event(tenant_id, provider, batch.run_id, "completed", summary)
        return summary
    except Exception as exc:
        await complete_ingestion_event(
            tenant_id,
            provider,
            batch.run_id,
            "failed",
            {"run_id": batch.run_id, "error_code": type(exc).__name__},
        )
        raise
