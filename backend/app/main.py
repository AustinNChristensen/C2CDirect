import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from hmac import compare_digest
from uuid import UUID, uuid4

import httpx
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic_settings import BaseSettings, SettingsConfigDict

from .application_packages import build_application_package
from .auth import Principal, require_principal
from .auth import settings as auth_settings
from .billing import process_stripe_webhook
from .database import connect, disconnect, provision_principal
from .email_connectors import mailbox_address
from .email_oauth import (
    authorization_url,
    encrypt_secret,
    exchange_code,
    oauth_status,
    provider_config,
    validate_granted_scopes,
)
from .email_sync import sync_email_connection
from .graph import screening_graph
from .ingestion_service import ingest_batch
from .model_runtime import runtime_config, runtime_status, test_connection
from .models import (
    AcquisitionRunIn,
    ApplicationPackageStatusUpdate,
    BudgetPolicy,
    CandidateProfile,
    CandidateProfileUpdate,
    JobCorrectionIn,
    JobDecisionIn,
    JobImportRequest,
    JobPostingIn,
    JobStatusUpdate,
    ModelConnectionIn,
    N8NBatch,
    RecruiterContactIn,
    RecruiterContactPatch,
    SearchProfile,
    SearchProfileUpdate,
    SourceSyncRequest,
    WebScoutRequest,
    WebSearchConnectionIn,
)
from .observability import agent_run
from .outbound_security import validate_outbound_url
from .provider_registry import load_provider_targets, provider_target_summary
from .repositories import (
    cancel_acquisition_run,
    create_acquisition_run,
    create_application_package,
    create_recruiter_contact,
    delete_matching_resume,
    delete_model_connection,
    delete_web_search_connection,
    export_tenant_data,
    get_acquisition_run,
    get_active_search_profile,
    get_candidate_profile,
    get_candidate_profile_record,
    get_feedback_penalties,
    get_job_evidence,
    get_job_posting,
    get_matching_profile,
    get_model_connection,
    get_web_search_connection,
    list_acquisition_runs,
    list_application_packages,
    list_candidate_profiles,
    list_daily_actions,
    list_email_connections,
    list_job_decisions,
    list_jobs,
    list_jobs_for_matching,
    list_providers,
    list_recruiter_contacts,
    list_source_health,
    move_job,
    record_job_decision,
    reindex_job_evidence,
    retry_acquisition_run,
    save_matching_resume,
    update_application_package_status,
    update_job_corrections,
    update_recruiter_contact,
    upsert_active_search_profile,
    upsert_candidate_profile,
    upsert_email_connection,
    upsert_job,
    upsert_matching_profile,
    upsert_model_connection,
    upsert_provider,
    upsert_web_search_connection,
)
from .retrieval import match_candidate_to_role
from .source_registry import load_source_registry, source_registry_summary
from .source_sync import sync_registry
from .usage import active_policy, control_room_summary, metered_screening
from .web_scout import public_connection as public_search_connection
from .web_scout import run_web_scout, test_search_connection


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    n8n_webhook_secret: str = "replace-me"
    n8n_callback_url: str | None = None
    frontend_origin: str = "http://localhost:3000"
    minimum_ingest_score: int = 50
    source_url: str = "https://directc2c.com/#core"


settings = Settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await connect()
    yield
    await disconnect()


app = FastAPI(title="C2CDirect API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def require_active_principal(
    principal: Principal = Depends(require_principal),
) -> Principal:
    return await provision_principal(principal)


def require_owner_write(principal: Principal) -> None:
    if "owner" not in principal.roles or "jobs:write" not in principal.scopes:
        raise HTTPException(403, "Owner role and jobs:write scope required")


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@app.post("/v1/acquisition-runs", status_code=202)
async def queue_acquisition_run(
    request: AcquisitionRunIn,
    principal: Principal = Depends(require_active_principal),
):
    require_owner_write(principal)
    saved = await get_matching_profile(principal.tenant_id, principal.user_id)
    if not saved.get("onboarding_completed"):
        raise HTTPException(409, "Complete the matching profile before acquiring jobs")
    try:
        run_id = await create_acquisition_run(
            principal.tenant_id, principal.user_id, request.kind, request.request
        )
    except RuntimeError as exc:
        raise HTTPException(429, str(exc)) from exc
    return {"id": run_id, "status": "queued"}


@app.get("/v1/acquisition-runs")
async def acquisition_runs(principal: Principal = Depends(require_active_principal)):
    require_owner_write(principal)
    return await list_acquisition_runs(principal.tenant_id)


@app.get("/v1/acquisition-runs/{run_id}")
async def acquisition_run(
    run_id: UUID, principal: Principal = Depends(require_active_principal)
):
    require_owner_write(principal)
    try:
        return await get_acquisition_run(principal.tenant_id, run_id)
    except KeyError:
        raise HTTPException(404, "Acquisition run not found")


@app.post("/v1/acquisition-runs/{run_id}/retry", status_code=202)
async def retry_run(run_id: UUID, principal: Principal = Depends(require_active_principal)):
    require_owner_write(principal)
    try:
        new_id = await retry_acquisition_run(principal.tenant_id, run_id)
    except KeyError:
        raise HTTPException(409, "Only failed or cancelled runs can be retried")
    return {"id": new_id, "status": "queued"}


@app.delete("/v1/acquisition-runs/{run_id}")
async def cancel_run(run_id: UUID, principal: Principal = Depends(require_active_principal)):
    require_owner_write(principal)
    try:
        await cancel_acquisition_run(principal.tenant_id, run_id)
    except KeyError:
        raise HTTPException(409, "Only active runs can be cancelled")
    return {"cancel_requested": True}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "orchestrator": "langgraph",
        "retrieval": "ready",
        "license": "AGPL-3.0-only",
        "source": settings.source_url,
    }


@app.get("/v1/control-room")
async def control_room(principal: Principal = Depends(require_active_principal)):
    connection = await get_model_connection(principal.tenant_id)
    return await control_room_summary(
        principal.tenant_id, active_policy(), runtime_status(connection)
    )


def _public_connection(connection: dict | None) -> dict:
    status = runtime_status(connection)
    return {
        **status,
        "base_url": connection.get("base_url", "") if connection else "",
        "updated_at": connection.get("updated_at") if connection else None,
    }


@app.get("/v1/model-connection")
async def model_connection(principal: Principal = Depends(require_active_principal)):
    require_owner_write(principal)
    return _public_connection(await get_model_connection(principal.tenant_id))


@app.post("/v1/model-connection/test")
async def test_model_connection(
    connection: ModelConnectionIn,
    principal: Principal = Depends(require_active_principal),
):
    require_owner_write(principal)
    try:
        validate_outbound_url(
            connection.base_url, allow_private=auth_settings.auth_disabled_for_local_dev
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    existing = await get_model_connection(principal.tenant_id)
    payload = connection.model_dump()
    if not payload.get("api_key") and existing and existing.get("api_key"):
        payload["api_key"] = existing["api_key"]
    return await test_connection(runtime_config(payload))


@app.put("/v1/model-connection")
async def save_model_connection(
    connection: ModelConnectionIn,
    principal: Principal = Depends(require_active_principal),
):
    require_owner_write(principal)
    try:
        validate_outbound_url(
            connection.base_url, allow_private=auth_settings.auth_disabled_for_local_dev
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    await upsert_model_connection(principal.tenant_id, connection)
    return _public_connection(await get_model_connection(principal.tenant_id))


@app.delete("/v1/model-connection")
async def reset_model_connection(principal: Principal = Depends(require_active_principal)):
    require_owner_write(principal)
    await delete_model_connection(principal.tenant_id)
    return _public_connection(None)


@app.get("/v1/web-search-connection")
async def web_search_connection(principal: Principal = Depends(require_active_principal)):
    require_owner_write(principal)
    return public_search_connection(await get_web_search_connection(principal.tenant_id))


@app.post("/v1/web-search-connection/test")
async def test_web_search_connection(
    connection: WebSearchConnectionIn,
    principal: Principal = Depends(require_active_principal),
):
    require_owner_write(principal)
    try:
        validate_outbound_url(
            connection.base_url, allow_private=auth_settings.auth_disabled_for_local_dev
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    existing = await get_web_search_connection(principal.tenant_id)
    payload = connection.model_dump()
    if not payload.get("api_key") and existing and existing.get("api_key"):
        payload["api_key"] = existing["api_key"]
    return await test_search_connection(payload)


@app.put("/v1/web-search-connection")
async def save_web_search_connection(
    connection: WebSearchConnectionIn,
    principal: Principal = Depends(require_active_principal),
):
    require_owner_write(principal)
    try:
        validate_outbound_url(
            connection.base_url, allow_private=auth_settings.auth_disabled_for_local_dev
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    await upsert_web_search_connection(principal.tenant_id, connection)
    return public_search_connection(await get_web_search_connection(principal.tenant_id))


@app.delete("/v1/web-search-connection")
async def reset_web_search_connection(
    principal: Principal = Depends(require_active_principal),
):
    require_owner_write(principal)
    await delete_web_search_connection(principal.tenant_id)
    return public_search_connection(None)


@app.post("/v1/screen")
async def screen_job(
    posting: JobPostingIn,
    profile: SearchProfile | None = None,
    principal: Principal = Depends(require_active_principal),
):
    with agent_run("screen_job", principal.tenant_id) as (run, span):
        policy = active_policy()
        result = await metered_screening(
            principal.tenant_id,
            screening_graph,
            posting,
            profile or SearchProfile(),
            policy,
        )
        estimate = result["cost_estimate"]
        usage = result.get("model_usage")
        actual_cost = usage.actual_cost_usd if usage else estimate.estimated_cost_usd
        input_tokens = usage.input_tokens if usage else estimate.estimated_input_tokens
        output_tokens = usage.output_tokens if usage else estimate.estimated_output_tokens
        span.set_attributes(
            {
                "gen_ai.request.model": estimate.model,
                "gen_ai.usage.input_tokens": input_tokens,
                "gen_ai.usage.output_tokens": output_tokens,
                "app.estimated_cost_usd": estimate.estimated_cost_usd,
                "app.actual_cost_usd": actual_cost,
                "app.cost_gate_allowed": estimate.allowed,
            }
        )
        run.update(
            {
                "model": estimate.model,
                "estimated_cost_usd": estimate.estimated_cost_usd,
                "policy_decisions": [estimate.gate_reason or "allowed"],
            }
        )
        job_id = await upsert_job(principal.tenant_id, result["result"])
        return {
            "id": job_id,
            "job": result["result"],
            "evidence": result["evidence"],
            "citations": result.get("citations", []),
            "cost": estimate,
            "trace": run,
            "evaluation": result.get("evaluation"),
            "model_target": result.get("model_target"),
            "model_usage": result.get("model_usage"),
            "approval_required": result.get("approval_required", False),
        }


@app.post("/v1/screen/stream")
async def stream_screen_job(
    posting: JobPostingIn,
    profile: SearchProfile | None = None,
    principal: Principal = Depends(require_active_principal),
):
    """Stream observable progress without requiring an external queue or Redis."""

    async def events():
        yield _sse("stage", {"name": "guardrails", "status": "running"})
        result = await metered_screening(
            principal.tenant_id,
            screening_graph,
            posting,
            profile or SearchProfile(),
            active_policy(),
            operation="screen_job_stream",
        )
        yield _sse("stage", {"name": "screening", "status": "complete"})
        yield _sse("stage", {"name": "retrieval_and_evaluation", "status": "complete"})
        payload = {
            "job": result["result"].model_dump(mode="json"),
            "evidence": result.get("evidence", []),
            "citations": result.get("citations", []),
            "cost": result["cost_estimate"].model_dump(mode="json"),
            "evaluation": (
                result["evaluation"].model_dump(mode="json") if result.get("evaluation") else None
            ),
            "model_target": vars(result["model_target"]),
            "approval_required": result.get("approval_required", False),
        }
        yield _sse("result", payload)

    return StreamingResponse(events(), media_type="text/event-stream")


async def notify_n8n(payload: dict):
    if settings.n8n_callback_url:
        async with httpx.AsyncClient(timeout=20) as client:
            await client.post(settings.n8n_callback_url, json=payload)


@app.post("/v1/ingest/n8n")
async def ingest_n8n(
    batch: N8NBatch,
    background: BackgroundTasks,
    x_webhook_secret: str = Header(default=""),
    principal: Principal = Depends(require_active_principal),
):
    if not compare_digest(x_webhook_secret, settings.n8n_webhook_secret):
        raise HTTPException(401, "Invalid webhook secret")
    try:
        payload = await ingest_batch(
            principal.tenant_id,
            batch,
            screening_graph,
            minimum_score=settings.minimum_ingest_score,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(409, str(exc)) from exc
    background.add_task(notify_n8n, payload)
    return payload


@app.post("/v1/jobs/import")
async def import_jobs(
    request: JobImportRequest,
    principal: Principal = Depends(require_active_principal),
):
    require_owner_write(principal)
    batch = N8NBatch(
        run_id=f"manual-{uuid4()}",
        jobs=request.jobs,
        refresh_existing=request.refresh_existing,
        retain_all_in_pipeline=request.retain_all_in_pipeline,
    )
    try:
        return await ingest_batch(
            principal.tenant_id,
            batch,
            screening_graph,
            minimum_score=settings.minimum_ingest_score,
            provider="manual",
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/v1/control-plane/policy")
def control_plane_policy():
    return BudgetPolicy()


@app.get("/v1/jobs")
async def jobs(minimum_score: int = 0, principal: Principal = Depends(require_active_principal)):
    return await list_jobs(principal.tenant_id, minimum_score)


@app.get("/v1/profile")
async def candidate_profile(principal: Principal = Depends(require_active_principal)):
    return await get_matching_profile(principal.tenant_id, principal.user_id)


@app.put("/v1/profile")
async def update_candidate_profile(
    profile: CandidateProfile, principal: Principal = Depends(require_active_principal)
):
    await upsert_matching_profile(principal.tenant_id, principal.user_id, profile)
    return await get_matching_profile(principal.tenant_id, principal.user_id)


@app.post("/v1/profile/resume")
async def upload_candidate_resume(
    resume: UploadFile = File(...), principal: Principal = Depends(require_active_principal)
):
    allowed = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "text/plain": ".txt",
    }
    content_type = resume.content_type or ""
    file_name = (resume.filename or "resume").split("/")[-1].split("\\")[-1][:180]
    if content_type not in allowed or not file_name.lower().endswith(allowed[content_type]):
        raise HTTPException(422, "Resume must be a PDF, DOCX, or plain-text file")
    content = await resume.read(5 * 1024 * 1024 + 1)
    if not content or len(content) > 5 * 1024 * 1024:
        raise HTTPException(422, "Resume must be between 1 byte and 5 MB")
    if content_type == "application/pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(422, "The uploaded file is not a valid PDF")
    if content_type.endswith("document") and not content.startswith(b"PK"):
        raise HTTPException(422, "The uploaded file is not a valid DOCX")
    if content_type == "text/plain" and b"\x00" in content:
        raise HTTPException(422, "The uploaded file is not plain text")
    await save_matching_resume(
        principal.tenant_id, principal.user_id, file_name, content_type, content
    )
    return await get_matching_profile(principal.tenant_id, principal.user_id)


@app.delete("/v1/profile/resume")
async def remove_candidate_resume(principal: Principal = Depends(require_active_principal)):
    await delete_matching_resume(principal.tenant_id, principal.user_id)
    return {"deleted": True}


@app.get("/v1/search-profile")
async def active_search_profile(principal: Principal = Depends(require_active_principal)):
    require_owner_write(principal)
    return await get_active_search_profile(principal.tenant_id, principal.user_id)


@app.put("/v1/search-profile")
async def save_search_profile(
    profile: SearchProfileUpdate, principal: Principal = Depends(require_active_principal)
):
    require_owner_write(principal)
    return await upsert_active_search_profile(principal.tenant_id, principal.user_id, profile)


@app.get("/v1/candidates/me")
async def my_candidate_profile(principal: Principal = Depends(require_active_principal)):
    require_owner_write(principal)
    profile = await get_candidate_profile(principal.tenant_id, principal.user_id)
    if not profile:
        raise HTTPException(404, "No candidate evidence profile has been loaded")
    return profile


@app.put("/v1/candidates/me")
async def save_candidate_profile(
    profile: CandidateProfileUpdate, principal: Principal = Depends(require_active_principal)
):
    require_owner_write(principal)
    return await upsert_candidate_profile(principal.tenant_id, principal.user_id, profile)


@app.get("/v1/jobs/{job_id}/match")
async def match_me_to_job(job_id: UUID, principal: Principal = Depends(require_active_principal)):
    require_owner_write(principal)
    profile = await get_candidate_profile(principal.tenant_id, principal.user_id)
    if not profile:
        raise HTTPException(409, "Load a candidate evidence profile before matching roles")
    try:
        posting = await get_job_posting(principal.tenant_id, job_id)
    except KeyError as exc:
        raise HTTPException(404, "Job not found") from exc
    chunks = await get_job_evidence(principal.tenant_id, job_id)
    return {
        "candidate_name": profile.name,
        "job_id": str(job_id),
        **match_candidate_to_role(posting, profile, profile.evidence, chunks),
    }


@app.post("/v1/jobs/{job_id}/application-packages")
async def create_job_application_package(
    job_id: UUID, principal: Principal = Depends(require_active_principal)
):
    """Assemble an approval-only application brief from cited evidence, never auto-submit it."""
    require_owner_write(principal)
    candidate = await get_candidate_profile_record(principal.tenant_id, principal.user_id)
    if not candidate:
        raise HTTPException(409, "Load a candidate evidence profile before creating an application package")
    candidate_id, profile = candidate
    try:
        posting = await get_job_posting(principal.tenant_id, job_id)
    except KeyError as exc:
        raise HTTPException(404, "Job not found") from exc
    chunks = await get_job_evidence(principal.tenant_id, job_id)
    match = match_candidate_to_role(posting, profile, profile.evidence, chunks)
    if match["qualification"] == "blocked":
        raise HTTPException(409, {"message": "Hard filters block this role", "disqualifiers": match["disqualifiers"]})
    package = build_application_package(posting, profile, match)
    return await create_application_package(principal.tenant_id, str(job_id), candidate_id, package)


@app.get("/v1/jobs/{job_id}/application-packages")
async def job_application_packages(
    job_id: UUID, principal: Principal = Depends(require_active_principal)
):
    require_owner_write(principal)
    return await list_application_packages(principal.tenant_id, str(job_id))


@app.patch("/v1/application-packages/{package_id}")
async def set_application_package_status(
    package_id: UUID,
    update: ApplicationPackageStatusUpdate,
    principal: Principal = Depends(require_active_principal),
):
    require_owner_write(principal)
    try:
        await update_application_package_status(principal.tenant_id, str(package_id), update.status)
    except KeyError as exc:
        raise HTTPException(404, "Application package not found") from exc
    return {"updated": True}


@app.get("/v1/jobs/{job_id}/candidates")
async def match_job_to_candidates(
    job_id: UUID, principal: Principal = Depends(require_active_principal)
):
    """Role-to-candidate direction. Results are strictly within the active tenant."""
    require_owner_write(principal)
    try:
        posting = await get_job_posting(principal.tenant_id, job_id)
    except KeyError as exc:
        raise HTTPException(404, "Job not found") from exc
    candidates = await list_candidate_profiles(principal.tenant_id)
    chunks = await get_job_evidence(principal.tenant_id, job_id)
    return {
        "job_id": str(job_id),
        "matches": [
            {
                "candidate_id": candidate["id"],
                "candidate_name": candidate["profile"].name,
                "headline": candidate["profile"].headline,
                **match_candidate_to_role(
                    posting, candidate["profile"], candidate["profile"].evidence, chunks
                ),
            }
            for candidate in candidates
        ],
        "scope": "tenant_only",
    }


@app.get("/v1/candidates/me/roles")
async def match_roles_to_me(
    limit: int = 50, principal: Principal = Depends(require_active_principal)
):
    """Candidate-to-roles direction over persisted full-role documents and chunks."""
    require_owner_write(principal)
    if limit < 1 or limit > 100:
        raise HTTPException(422, "limit must be between 1 and 100")
    profile = await get_candidate_profile(principal.tenant_id, principal.user_id)
    if not profile:
        raise HTTPException(409, "Load a candidate evidence profile before matching roles")
    matches = []
    for job_id, posting, chunks in await list_jobs_for_matching(principal.tenant_id, limit):
        result = match_candidate_to_role(posting, profile, profile.evidence, chunks)
        if result["qualification"] != "blocked":
            matches.append({"job_id": job_id, "title": posting.title, "company": posting.company, **result})
    matches.sort(
        key=lambda item: (item["qualification"] == "strong", len(item["matched_evidence"])),
        reverse=True,
    )
    return {"candidate_name": profile.name, "matches": matches, "scope": "tenant_only"}


@app.post("/v1/evidence/reindex")
async def rebuild_role_evidence(principal: Principal = Depends(require_active_principal)):
    require_owner_write(principal)
    return {"indexed_roles": await reindex_job_evidence(principal.tenant_id)}


@app.get("/v1/sources")
async def sources(principal: Principal = Depends(require_active_principal)):
    require_owner_write(principal)
    return {
        "summary": source_registry_summary(),
        "sources": [target.model_dump() for target in load_source_registry(enabled_only=False)],
    }


@app.get("/v1/sources/health")
async def source_health(principal: Principal = Depends(require_active_principal)):
    """Source reliability from completed syncs and observed field coverage."""
    require_owner_write(principal)
    return await list_source_health(principal.tenant_id)


@app.post("/v1/sources/sync")
async def synchronize_sources(
    request: SourceSyncRequest,
    principal: Principal = Depends(require_active_principal),
):
    require_owner_write(principal)
    targets = [
        target
        for target in load_source_registry()
        if target.priority in request.priorities
        and (not request.source_slugs or target.slug in request.source_slugs)
    ]
    saved = await get_matching_profile(principal.tenant_id, principal.user_id)
    profile = SearchProfile(
        min_rate=saved["min_rate"],
        target_rate=saved["target_rate"],
        locations=saved["locations"],
        core_skills=[item.lower() for item in saved["core_skills"]],
        ai_skills=[item.lower() for item in saved["ai_skills"]],
        require_c2c=saved["require_c2c"],
        target_roles=saved["target_roles"],
        seniority_levels=saved["seniority_levels"],
        work_modes=saved["work_modes"],
        feedback_penalties=await get_feedback_penalties(principal.tenant_id),
    )
    return await sync_registry(
        principal.tenant_id,
        targets,
        profile,
        total_limit=request.total_limit,
        per_target_limit=request.per_target_limit,
        query=request.query,
    )


@app.post("/v1/web-scout/search")
async def search_web_for_jobs(
    request: WebScoutRequest,
    principal: Principal = Depends(require_active_principal),
):
    require_owner_write(principal)
    connection = await get_web_search_connection(principal.tenant_id)
    if not connection or connection.get("provider") == "disabled":
        raise HTTPException(409, "Connect a web search service before running Web Scout")
    saved = await get_matching_profile(principal.tenant_id, principal.user_id)
    profile = SearchProfile(
        min_rate=saved["min_rate"],
        target_rate=saved["target_rate"],
        locations=saved["locations"],
        core_skills=[item.lower() for item in saved["core_skills"]],
        ai_skills=[item.lower() for item in saved["ai_skills"]],
        require_c2c=saved["require_c2c"],
    )
    try:
        return await run_web_scout(
            principal.tenant_id,
            connection,
            profile,
            request.focus
            or " OR ".join(f'"{role}"' for role in saved["target_roles"][:5]),
            request.domains,
            request.max_results,
        )
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "Web Scout could not complete this search") from exc


@app.get("/v1/providers/targets")
async def provider_targets(principal: Principal = Depends(require_active_principal)):
    require_owner_write(principal)
    return {
        "summary": provider_target_summary(),
        "providers": [target.model_dump(mode="json") for target in load_provider_targets()],
        "relationship_claim": "target_only_until_verified",
    }


@app.post("/v1/providers/seed")
async def seed_provider_targets(principal: Principal = Depends(require_active_principal)):
    require_owner_write(principal)
    seeded = []
    for target in load_provider_targets():
        if target.enabled:
            seeded.append(await upsert_provider(principal.tenant_id, target.provider_definition()))
    return {"seeded": len(seeded), "provider_ids": seeded}


@app.get("/v1/providers")
async def providers(principal: Principal = Depends(require_active_principal)):
    require_owner_write(principal)
    return await list_providers(principal.tenant_id)


@app.get("/v1/recruiters")
async def recruiters(principal: Principal = Depends(require_active_principal)):
    require_owner_write(principal)
    return await list_recruiter_contacts(principal.tenant_id)


@app.post("/v1/recruiters")
async def create_recruiter(
    contact: RecruiterContactIn, principal: Principal = Depends(require_active_principal)
):
    require_owner_write(principal)
    try:
        contact_id = await create_recruiter_contact(principal.tenant_id, contact)
    except KeyError as exc:
        raise HTTPException(404, "Provider target must be seeded first") from exc
    return {"id": contact_id}


@app.patch("/v1/recruiters/{contact_id}")
async def update_recruiter(
    contact_id: UUID,
    patch: RecruiterContactPatch,
    principal: Principal = Depends(require_active_principal),
):
    require_owner_write(principal)
    try:
        await update_recruiter_contact(principal.tenant_id, contact_id, patch)
    except KeyError:
        raise HTTPException(404, "Recruiter contact not found")
    return {"updated": True}


@app.get("/v1/actions/today")
async def today_actions(principal: Principal = Depends(require_active_principal)):
    require_owner_write(principal)
    return await list_daily_actions(principal.tenant_id)


@app.get("/v1/email/connections")
async def email_connections(principal: Principal = Depends(require_active_principal)):
    require_owner_write(principal)
    return await list_email_connections(principal.tenant_id, principal.user_id)


@app.get("/v1/email/oauth/status")
async def email_oauth_status(principal: Principal = Depends(require_active_principal)):
    require_owner_write(principal)
    return oauth_status()


@app.get("/v1/email/oauth/{provider}/start")
async def start_email_oauth(
    provider: str, principal: Principal = Depends(require_active_principal)
):
    require_owner_write(principal)
    try:
        provider_config(provider)
        url = authorization_url(provider, principal.tenant_id, principal.user_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"authorization_url": url}


@app.get("/v1/email/oauth/{provider}/callback", response_class=HTMLResponse)
async def finish_email_oauth(provider: str, code: str, state: str):
    try:
        state_payload, tokens = await exchange_code(provider, code, state)
        access_token = tokens["access_token"]
        async with httpx.AsyncClient(timeout=30) as client:
            address = await mailbox_address(provider, access_token, client)
        expires_at = datetime.now(UTC) + timedelta(seconds=int(tokens.get("expires_in", 3600)))
        scopes = validate_granted_scopes(provider, str(tokens.get("scope", "")))
        await upsert_email_connection(
            state_payload["tenant_id"],
            state_payload["user_id"],
            provider,
            address,
            encrypt_secret(access_token),
            encrypt_secret(tokens["refresh_token"]) if tokens.get("refresh_token") else None,
            expires_at,
            scopes,
        )
    except (ValueError, RuntimeError, KeyError, httpx.HTTPError) as exc:
        raise HTTPException(400, "Email authorization could not be completed") from exc
    return HTMLResponse(
        """<!doctype html><html><head><title>Mailbox connected</title></head>
        <body><h1>Mailbox connected</h1><p>This window will close automatically.</p>
        <script>if(window.opener){window.opener.postMessage({type:'c2c-email-connected'},window.location.origin)};window.close()</script>
        </body></html>"""
    )


@app.post("/v1/email/{provider}/sync")
async def synchronize_email(
    provider: str,
    limit: int = 50,
    principal: Principal = Depends(require_active_principal),
):
    require_owner_write(principal)
    if provider not in {"gmail", "microsoft"}:
        raise HTTPException(404, "Unsupported email provider")
    if limit < 1 or limit > 100:
        raise HTTPException(422, "limit must be between 1 and 100")
    try:
        return await sync_email_connection(
            principal.tenant_id, principal.user_id, provider, limit=limit
        )
    except LookupError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.patch("/v1/jobs/{job_id}/status")
async def update_job_status(
    job_id: UUID, update: JobStatusUpdate, principal: Principal = Depends(require_active_principal)
):
    require_owner_write(principal)
    try:
        await move_job(
            principal.tenant_id, job_id, update.status, update.hidden_reason, update.follow_up_at
        )
    except KeyError:
        raise HTTPException(404, "Job not found")
    return {"updated": True}


@app.get("/v1/jobs/{job_id}/decisions")
async def job_decisions(job_id: UUID, principal: Principal = Depends(require_active_principal)):
    try:
        return await list_job_decisions(principal.tenant_id, job_id)
    except KeyError:
        raise HTTPException(404, "Job not found")


@app.post("/v1/jobs/{job_id}/decisions", status_code=201)
async def create_job_decision(
    job_id: UUID,
    decision: JobDecisionIn,
    principal: Principal = Depends(require_active_principal),
):
    require_owner_write(principal)
    try:
        return await record_job_decision(principal.tenant_id, principal.user_id, job_id, decision)
    except KeyError:
        raise HTTPException(404, "Job not found")


@app.post("/v1/jobs/{job_id}/rescreen")
async def rescreen_job(
    job_id: UUID, principal: Principal = Depends(require_active_principal)
):
    require_owner_write(principal)
    try:
        posting = await get_job_posting(principal.tenant_id, job_id)
    except KeyError:
        raise HTTPException(404, "Job not found")
    saved = await get_matching_profile(principal.tenant_id, principal.user_id)
    profile = SearchProfile(
        min_rate=saved["min_rate"],
        target_rate=saved["target_rate"],
        locations=saved["locations"],
        core_skills=[item.lower() for item in saved["core_skills"]],
        ai_skills=[item.lower() for item in saved["ai_skills"]],
        require_c2c=saved["require_c2c"],
        target_roles=saved["target_roles"],
        seniority_levels=saved["seniority_levels"],
        work_modes=saved["work_modes"],
        feedback_penalties=await get_feedback_penalties(principal.tenant_id),
    )
    result = await metered_screening(
        principal.tenant_id,
        screening_graph,
        posting,
        profile,
        active_policy(),
        operation="rescreen_job",
    )
    await upsert_job(principal.tenant_id, result["result"])
    return result["result"]


@app.patch("/v1/jobs/{job_id}/corrections")
async def correct_job(
    job_id: UUID,
    correction: JobCorrectionIn,
    principal: Principal = Depends(require_active_principal),
):
    require_owner_write(principal)
    try:
        await update_job_corrections(principal.tenant_id, job_id, correction)
    except KeyError:
        raise HTTPException(404, "Job not found")
    return {"updated": True}


@app.get("/v1/export")
async def export_core_data(principal: Principal = Depends(require_active_principal)):
    require_owner_write(principal)
    payload = json.dumps(
        await export_tenant_data(principal.tenant_id, principal.user_id),
        default=str,
        indent=2,
    ).encode()
    return StreamingResponse(
        iter([payload]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=c2cdirect-core-export.json"},
    )


@app.post("/v1/billing/stripe-webhook")
async def stripe_webhook(
    request: Request, stripe_signature: str = Header(alias="stripe-signature")
):
    return await process_stripe_webhook(await request.body(), stripe_signature)
