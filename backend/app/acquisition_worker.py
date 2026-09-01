"""Durable acquisition worker for public sources, web, mail, and imports."""

import asyncio
import logging
from uuid import UUID

from .database import connect, disconnect
from .email_sync import sync_email_connection
from .graph import screening_graph
from .ingestion_service import ingest_batch
from .models import N8NBatch, SearchProfile
from .repositories import (
    acquisition_cancel_requested,
    claim_acquisition_run,
    complete_acquisition_run,
    get_feedback_penalties,
    get_matching_profile,
    get_web_search_connection,
)
from .source_registry import load_source_registry
from .source_sync import sync_registry
from .web_scout import run_web_scout

logger = logging.getLogger("c2cdirect.acquisition")


def search_profile(saved: dict, feedback: dict[str, int] | None = None) -> SearchProfile:
    return SearchProfile(
        min_rate=saved["min_rate"],
        target_rate=saved["target_rate"],
        locations=saved["locations"],
        core_skills=[item.lower() for item in saved["core_skills"]],
        ai_skills=[item.lower() for item in saved["ai_skills"]],
        require_c2c=saved["require_c2c"],
        target_roles=saved["target_roles"],
        seniority_levels=saved["seniority_levels"],
        work_modes=saved["work_modes"],
        feedback_penalties=feedback or {},
    )


async def execute(run: dict) -> dict:
    tenant_id = str(run["run_tenant_id"])
    user_id = str(run["run_user_id"])
    request = run["run_request"] or {}
    saved = await get_matching_profile(tenant_id, user_id)
    if not saved.get("onboarding_completed"):
        raise ValueError("Profile setup is incomplete")
    profile = search_profile(saved, await get_feedback_penalties(tenant_id))
    kind = run["run_kind"]
    if kind == "public_sources":
        priorities = request.get("priorities", [1, 2, 3])
        selected = set(request.get("source_slugs", []))
        targets = [
            target
            for target in load_source_registry()
            if target.priority in priorities and (not selected or target.slug in selected)
        ]
        return await sync_registry(
            tenant_id,
            targets,
            profile,
            total_limit=min(int(request.get("total_limit", 200)), 200),
            per_target_limit=min(int(request.get("per_target_limit", 20)), 50),
        )
    if kind == "web_scout":
        connection = await get_web_search_connection(tenant_id)
        if not connection or connection.get("provider") == "disabled":
            raise ValueError("Web search is not configured")
        focus = str(request.get("focus", "")) or " OR ".join(
            f'"{role}"' for role in saved["target_roles"][:5]
        )
        return await run_web_scout(
            tenant_id,
            connection,
            profile,
            focus,
            list(request.get("domains", []))[:10],
            min(int(request.get("max_results", 20)), 50),
        )
    if kind == "email_sync":
        return await sync_email_connection(
            tenant_id,
            user_id,
            str(request.get("provider")),
            profile,
            limit=min(int(request.get("limit", 50)), 100),
        )
    if kind == "import":
        batch = N8NBatch.model_validate(
            {
                "run_id": f"core-import:{run['run_id']}",
                "jobs": request.get("jobs", []),
                "refresh_existing": bool(request.get("refresh_existing", False)),
                "retain_all_in_pipeline": True,
            }
        )
        return await ingest_batch(
            tenant_id,
            batch,
            screening_graph,
            provider="manual_import",
            profile=profile,
        )
    raise ValueError("Unsupported acquisition kind")


async def worker() -> None:
    await connect()
    try:
        while True:
            run = await claim_acquisition_run()
            if not run:
                await asyncio.sleep(1)
                continue
            tenant_id = str(run["run_tenant_id"])
            run_id = UUID(str(run["run_id"]))
            try:
                result = await execute(run)
                if await acquisition_cancel_requested(tenant_id, run_id):
                    await complete_acquisition_run(tenant_id, run_id, "cancelled", result)
                else:
                    await complete_acquisition_run(tenant_id, run_id, "completed", result)
            except Exception as exc:
                logger.exception("Acquisition run %s failed", run_id)
                await complete_acquisition_run(
                    tenant_id, run_id, "failed", error_code=type(exc).__name__
                )
    finally:
        await disconnect()


if __name__ == "__main__":
    asyncio.run(worker())
