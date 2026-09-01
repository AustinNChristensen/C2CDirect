import json
from hashlib import sha256
from uuid import UUID

from . import database as database_state
from .database import tenant_connection
from .models import (
    CandidateProfile,
    CandidateProfileUpdate,
    JobCorrectionIn,
    JobDecisionIn,
    JobPostingIn,
    ModelConnectionIn,
    RecruiterContactIn,
    RecruiterContactPatch,
    ScreenedJob,
    SearchProfile,
    SearchProfileUpdate,
    WebSearchConnectionIn,
)
from .provenance import JobObservation, ProvenanceAssessment, ProviderDefinition
from .retrieval import Evidence, role_evidence
from .secret_store import decrypt_secret, encrypt_secret


def _json_list(value) -> list:
    while isinstance(value, str):
        value = json.loads(value)
    return value if isinstance(value, list) else []


async def get_matching_profile(tenant_id: str, user_id: str) -> dict:
    async with tenant_connection(tenant_id) as conn:
        row = await conn.fetchrow(
            """SELECT id,name,profile_json,resume_file_name,resume_content_type,
                      resume_size_bytes,resume_uploaded_at,updated_at
                 FROM search_profiles WHERE user_id=$1 ORDER BY updated_at DESC LIMIT 1""",
            user_id,
        )
        if not row:
            return {**CandidateProfile().model_dump(), "resume": None}
        profile = row["profile_json"]
        while isinstance(profile, str):
            profile = json.loads(profile)
        return {
            **CandidateProfile.model_validate(profile).model_dump(),
            "resume": ({"file_name": row["resume_file_name"], "content_type": row["resume_content_type"], "size_bytes": row["resume_size_bytes"], "uploaded_at": row["resume_uploaded_at"]} if row["resume_file_name"] else None),
        }


async def upsert_matching_profile(tenant_id: str, user_id: str, profile: CandidateProfile) -> None:
    async with tenant_connection(tenant_id) as conn:
        await conn.execute(
            """INSERT INTO search_profiles(tenant_id,user_id,name,profile_json)
               VALUES($1,$2,$3,$4::jsonb)
               ON CONFLICT(tenant_id,user_id) WHERE user_id IS NOT NULL DO UPDATE SET
                 name=excluded.name,profile_json=excluded.profile_json,updated_at=now()""",
            tenant_id, user_id, profile.display_name, profile.model_dump_json(),
        )


async def save_matching_resume(tenant_id: str, user_id: str, file_name: str, content_type: str, content: bytes) -> None:
    async with tenant_connection(tenant_id) as conn:
        await conn.execute(
            """INSERT INTO search_profiles(tenant_id,user_id,name,profile_json,resume_file_name,resume_content_type,resume_size_bytes,resume_bytes,resume_uploaded_at)
               VALUES($1,$2,$3,$4::jsonb,$5,$6,$7,$8,now())
               ON CONFLICT(tenant_id,user_id) WHERE user_id IS NOT NULL DO UPDATE SET
                 resume_file_name=excluded.resume_file_name,resume_content_type=excluded.resume_content_type,
                 resume_size_bytes=excluded.resume_size_bytes,resume_bytes=excluded.resume_bytes,
                 resume_uploaded_at=now(),updated_at=now()""",
            tenant_id, user_id, CandidateProfile().display_name, CandidateProfile().model_dump_json(), file_name, content_type, len(content), content,
        )


async def delete_matching_resume(tenant_id: str, user_id: str) -> None:
    async with tenant_connection(tenant_id) as conn:
        await conn.execute("""UPDATE search_profiles SET resume_file_name=NULL,resume_content_type=NULL,
          resume_size_bytes=NULL,resume_bytes=NULL,resume_uploaded_at=NULL,updated_at=now() WHERE user_id=$1""", user_id)


async def get_model_connection(tenant_id: str) -> dict | None:
    async with tenant_connection(tenant_id) as conn:
        row = await conn.fetchrow(
            """SELECT provider,base_url,model_name,api_key_encrypted,
                      input_cost_per_million,output_cost_per_million,updated_at
                 FROM ai_connections WHERE tenant_id=$1""",
            tenant_id,
        )
    if not row:
        return None
    return {
        "provider": row["provider"],
        "base_url": row["base_url"],
        "model_name": row["model_name"],
        "api_key": decrypt_secret(row["api_key_encrypted"]) if row["api_key_encrypted"] else "",
        "api_key_configured": bool(row["api_key_encrypted"]),
        "input_cost_per_million": float(row["input_cost_per_million"]),
        "output_cost_per_million": float(row["output_cost_per_million"]),
        "updated_at": row["updated_at"].isoformat(),
        "source": "tenant",
    }


async def upsert_model_connection(tenant_id: str, connection: ModelConnectionIn) -> None:
    encrypted_key = encrypt_secret(connection.api_key) if connection.api_key else None
    async with tenant_connection(tenant_id) as conn:
        await conn.execute(
            """INSERT INTO ai_connections(
                 tenant_id,provider,base_url,model_name,api_key_encrypted,
                 input_cost_per_million,output_cost_per_million)
               VALUES($1,$2,$3,$4,$5,$6,$7)
               ON CONFLICT(tenant_id) DO UPDATE SET
                 provider=excluded.provider,base_url=excluded.base_url,
                 model_name=excluded.model_name,
                 api_key_encrypted=CASE
                   WHEN $8 THEN NULL
                   WHEN $5 IS NOT NULL THEN $5
                   ELSE ai_connections.api_key_encrypted
                 END,
                 input_cost_per_million=excluded.input_cost_per_million,
                 output_cost_per_million=excluded.output_cost_per_million,
                 updated_at=now()""",
            tenant_id,
            connection.provider,
            connection.base_url,
            connection.model_name,
            encrypted_key,
            connection.input_cost_per_million,
            connection.output_cost_per_million,
            connection.clear_api_key,
        )


async def delete_model_connection(tenant_id: str) -> None:
    async with tenant_connection(tenant_id) as conn:
        await conn.execute("DELETE FROM ai_connections WHERE tenant_id=$1", tenant_id)


async def get_web_search_connection(tenant_id: str) -> dict | None:
    async with tenant_connection(tenant_id) as conn:
        row = await conn.fetchrow(
            """SELECT provider,base_url,api_key_encrypted,updated_at
                 FROM web_search_connections WHERE tenant_id=$1""",
            tenant_id,
        )
    if not row:
        return None
    return {
        "provider": row["provider"],
        "base_url": row["base_url"],
        "api_key": decrypt_secret(row["api_key_encrypted"]) if row["api_key_encrypted"] else "",
        "api_key_configured": bool(row["api_key_encrypted"]),
        "updated_at": row["updated_at"].isoformat(),
    }


async def upsert_web_search_connection(
    tenant_id: str, connection: WebSearchConnectionIn
) -> None:
    encrypted_key = encrypt_secret(connection.api_key) if connection.api_key else None
    async with tenant_connection(tenant_id) as conn:
        await conn.execute(
            """INSERT INTO web_search_connections(tenant_id,provider,base_url,api_key_encrypted)
               VALUES($1,$2,$3,$4)
               ON CONFLICT(tenant_id) DO UPDATE SET
                 provider=excluded.provider,base_url=excluded.base_url,
                 api_key_encrypted=CASE
                   WHEN $5 THEN NULL
                   WHEN $4 IS NOT NULL THEN $4
                   ELSE web_search_connections.api_key_encrypted
                 END,updated_at=now()""",
            tenant_id,
            connection.provider,
            connection.base_url,
            encrypted_key,
            connection.clear_api_key,
        )


async def delete_web_search_connection(tenant_id: str) -> None:
    async with tenant_connection(tenant_id) as conn:
        await conn.execute("DELETE FROM web_search_connections WHERE tenant_id=$1", tenant_id)


async def create_acquisition_run(
    tenant_id: str, user_id: str, kind: str, request: dict
) -> str:
    async with tenant_connection(tenant_id) as conn:
        recent = await conn.fetchval(
            "SELECT count(*) FROM acquisition_runs WHERE created_at>=now()-interval '1 minute'"
        )
        if recent >= 10:
            raise RuntimeError("Acquisition rate limit exceeded")
        run_id = await conn.fetchval(
            """INSERT INTO acquisition_runs(tenant_id,user_id,kind,request_json)
               VALUES($1,$2,$3,$4::jsonb) RETURNING id""",
            tenant_id,
            user_id,
            kind,
            json.dumps(request),
        )
        return str(run_id)


async def list_acquisition_runs(tenant_id: str, limit: int = 20) -> list[dict]:
    async with tenant_connection(tenant_id) as conn:
        rows = await conn.fetch(
            """SELECT id,kind,status,result_json,error_code,attempts,cancel_requested,created_at,
                      started_at,completed_at,updated_at
                 FROM acquisition_runs ORDER BY created_at DESC LIMIT $1""",
            limit,
        )
        return [dict(row) for row in rows]


async def get_acquisition_run(tenant_id: str, run_id: UUID) -> dict:
    async with tenant_connection(tenant_id) as conn:
        row = await conn.fetchrow(
            """SELECT id,kind,status,result_json,error_code,attempts,cancel_requested,created_at,
                      started_at,completed_at,updated_at
                 FROM acquisition_runs WHERE id=$1""",
            run_id,
        )
        if not row:
            raise KeyError(run_id)
        return dict(row)


async def cancel_acquisition_run(tenant_id: str, run_id: UUID) -> None:
    async with tenant_connection(tenant_id) as conn:
        updated = await conn.fetchval(
            """UPDATE acquisition_runs
                  SET cancel_requested=true,
                      status=CASE WHEN status='queued' THEN 'cancelled' ELSE status END,
                      completed_at=CASE WHEN status='queued' THEN now() ELSE completed_at END,
                      updated_at=now()
                 WHERE id=$1 AND status IN('queued','running') RETURNING id""",
            run_id,
        )
        if not updated:
            raise KeyError(run_id)


async def retry_acquisition_run(tenant_id: str, run_id: UUID) -> str:
    async with tenant_connection(tenant_id) as conn:
        row = await conn.fetchrow(
            "SELECT user_id,kind,request_json FROM acquisition_runs WHERE id=$1 AND status IN('failed','cancelled')",
            run_id,
        )
        if not row:
            raise KeyError(run_id)
        new_id = await conn.fetchval(
            """INSERT INTO acquisition_runs(tenant_id,user_id,kind,request_json)
               VALUES($1,$2,$3,$4) RETURNING id""",
            tenant_id,
            row["user_id"],
            row["kind"],
            row["request_json"],
        )
        return str(new_id)


async def claim_acquisition_run() -> dict | None:
    if not database_state.pool:
        raise RuntimeError("Database is not connected")
    async with database_state.pool.acquire() as conn, conn.transaction():
        row = await conn.fetchrow("SELECT * FROM claim_acquisition_run()")
        if not row:
            return None
        claimed = dict(row)
        if isinstance(claimed.get("run_request"), str):
            claimed["run_request"] = json.loads(claimed["run_request"])
        return claimed


async def complete_acquisition_run(
    tenant_id: str, run_id: UUID, status: str, result: dict | None = None, error_code: str | None = None
) -> None:
    async with tenant_connection(tenant_id) as conn:
        await conn.execute(
            """UPDATE acquisition_runs SET status=$2,result_json=$3::jsonb,error_code=$4,
                      completed_at=now(),updated_at=now() WHERE id=$1""",
            run_id,
            status,
            json.dumps(result) if result is not None else None,
            error_code,
        )


async def acquisition_cancel_requested(tenant_id: str, run_id: UUID) -> bool:
    async with tenant_connection(tenant_id) as conn:
        return bool(
            await conn.fetchval(
                "SELECT cancel_requested FROM acquisition_runs WHERE id=$1", run_id
            )
        )


def _json_object(value) -> dict:
    while isinstance(value, str):
        value = json.loads(value)
    return value if isinstance(value, dict) else {}


async def get_active_search_profile(tenant_id: str, user_id: str) -> SearchProfile:
    """Return the user's latest profile, falling back to safe defaults."""
    async with tenant_connection(tenant_id) as conn:
        row = await conn.fetchrow(
            """SELECT profile_json FROM search_profiles
                 WHERE user_id=$1 ORDER BY updated_at DESC LIMIT 1""",
            user_id,
        )
    return SearchProfile.model_validate(row["profile_json"]) if row else SearchProfile()


async def upsert_active_search_profile(
    tenant_id: str, user_id: str, update: SearchProfileUpdate
) -> dict:
    profile = SearchProfile(**update.model_dump(exclude={"name"}))
    async with tenant_connection(tenant_id) as conn:
        row = await conn.fetchrow(
            """INSERT INTO search_profiles(tenant_id,user_id,name,profile_json)
                 VALUES($1,$2,$3,$4::jsonb)
                 ON CONFLICT (tenant_id,user_id,name) DO UPDATE SET
                    profile_json=excluded.profile_json,updated_at=now()
                 RETURNING id,name,profile_json,updated_at""",
            tenant_id,
            user_id,
            update.name,
            profile.model_dump_json(),
        )
    result = dict(row)
    result["profile"] = result.pop("profile_json")
    return result


async def upsert_job(tenant_id: str, job: ScreenedJob) -> str:
    p = job.posting
    async with tenant_connection(tenant_id) as conn:
        row = await conn.fetchrow(
            """INSERT INTO jobs(tenant_id,source,source_url,title,company,description,location,rate_min,rate_max,contract_duration,engagement_type,c2c_status,fit_score,screening_json,posted_at,last_source_seen_at)
          VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,now())
          ON CONFLICT(tenant_id,fingerprint) DO UPDATE SET
            source=excluded.source,source_url=excluded.source_url,title=excluded.title,
            company=excluded.company,description=excluded.description,location=excluded.location,
            rate_min=excluded.rate_min,rate_max=excluded.rate_max,
            contract_duration=excluded.contract_duration,engagement_type=excluded.engagement_type,
            c2c_status=excluded.c2c_status,fit_score=excluded.fit_score,
            screening_json=excluded.screening_json,
            posted_at=coalesce(excluded.posted_at,jobs.posted_at),
            last_source_seen_at=now(),updated_at=now()
          RETURNING id""",
            tenant_id,
            p.source,
            str(p.source_url) if p.source_url else None,
            p.title,
            p.company,
            p.description,
            p.location,
            p.rate_min,
            p.rate_max,
            p.contract_duration,
            p.engagement_type,
            job.c2c_status,
            job.fit_score,
            job.model_dump_json(),
            p.posted_at,
        )
        job_id = str(row["id"])
    await index_job_evidence(tenant_id, job_id, job.posting)
    return job_id


async def index_job_evidence(tenant_id: str, job_id: str, posting) -> None:
    """Persist a full role document plus citeable chunks for two-way retrieval."""
    chunks = role_evidence(posting)
    async with tenant_connection(tenant_id) as conn:
        await conn.execute("DELETE FROM job_evidence WHERE job_id=$1", UUID(job_id))
        await conn.executemany(
            """INSERT INTO job_evidence(tenant_id,job_id,citation,section,body,metadata_json)
                 VALUES($1,$2,$3,$4,$5,$6::jsonb)""",
            [
                (
                    tenant_id,
                    UUID(job_id),
                    chunk.citation,
                    (chunk.metadata or {}).get("section", "description"),
                    chunk.text,
                    json.dumps(chunk.metadata or {}),
                )
                for chunk in chunks
            ],
        )


async def upsert_candidate_profile(
    tenant_id: str, user_id: str, update: CandidateProfileUpdate
) -> dict:
    profile_json = update.model_dump(exclude={"name", "headline", "evidence"})
    async with tenant_connection(tenant_id) as conn:
        row = await conn.fetchrow(
            """INSERT INTO candidate_profiles(tenant_id,user_id,name,headline,profile_json)
                 VALUES($1,$2,$3,$4,$5::jsonb)
                 ON CONFLICT(tenant_id,user_id,name) DO UPDATE SET
                   headline=excluded.headline,profile_json=excluded.profile_json,updated_at=now()
                 RETURNING id,name,headline,profile_json,updated_at""",
            tenant_id,
            user_id,
            update.name,
            update.headline,
            json.dumps(profile_json),
        )
        candidate_id = row["id"]
        await conn.execute("DELETE FROM candidate_evidence WHERE candidate_id=$1", candidate_id)
        if update.evidence:
            await conn.executemany(
                """INSERT INTO candidate_evidence(
                     tenant_id,candidate_id,source_ref,kind,heading,body,metadata_json
                   ) VALUES($1,$2,$3,$4,$5,$6,$7::jsonb)""",
                [
                    (
                        tenant_id,
                        candidate_id,
                        item.source_ref,
                        item.kind,
                        item.heading,
                        item.text,
                        json.dumps(item.metadata),
                    )
                    for item in update.evidence
                ],
            )
    result = dict(row)
    result["profile"] = result.pop("profile_json")
    result["evidence_count"] = len(update.evidence)
    return result


async def get_candidate_profile(tenant_id: str, user_id: str) -> CandidateProfileUpdate | None:
    async with tenant_connection(tenant_id) as conn:
        row = await conn.fetchrow(
            """SELECT id,name,headline,profile_json FROM candidate_profiles
                 WHERE user_id=$1 ORDER BY updated_at DESC LIMIT 1""",
            user_id,
        )
        if not row:
            return None
        evidence_rows = await conn.fetch(
            """SELECT source_ref,kind,heading,body,metadata_json FROM candidate_evidence
                 WHERE candidate_id=$1 ORDER BY created_at""",
            row["id"],
        )
    payload = _json_object(row["profile_json"])
    payload.update(
        {
            "name": row["name"],
            "headline": row["headline"],
            "evidence": [
                {
                    "source_ref": item["source_ref"],
                    "kind": item["kind"],
                    "heading": item["heading"],
                    "text": item["body"],
                    "metadata": _json_object(item["metadata_json"]),
                }
                for item in evidence_rows
            ],
        }
    )
    return CandidateProfileUpdate.model_validate(payload)


async def get_candidate_profile_record(tenant_id: str, user_id: str) -> tuple[str, CandidateProfileUpdate] | None:
    """Return the persisted candidate id with its evidence profile for package creation."""
    async with tenant_connection(tenant_id) as conn:
        row = await conn.fetchrow(
            """SELECT id,name,headline,profile_json FROM candidate_profiles
                 WHERE user_id=$1 ORDER BY updated_at DESC LIMIT 1""",
            user_id,
        )
        if not row:
            return None
        evidence_rows = await conn.fetch(
            """SELECT source_ref,kind,heading,body,metadata_json FROM candidate_evidence
                 WHERE candidate_id=$1 ORDER BY created_at""",
            row["id"],
        )
    payload = _json_object(row["profile_json"])
    payload.update(
        {
            "name": row["name"],
            "headline": row["headline"],
            "evidence": [
                {
                    "source_ref": item["source_ref"],
                    "kind": item["kind"],
                    "heading": item["heading"],
                    "text": item["body"],
                    "metadata": _json_object(item["metadata_json"]),
                }
                for item in evidence_rows
            ],
        }
    )
    return str(row["id"]), CandidateProfileUpdate.model_validate(payload)


async def list_candidate_profiles(tenant_id: str) -> list[dict]:
    """Tenant-scoped candidates for role-to-candidate retrieval (no cross-tenant reads)."""
    async with tenant_connection(tenant_id) as conn:
        profiles = await conn.fetch(
            "SELECT id,user_id,name,headline,profile_json FROM candidate_profiles ORDER BY updated_at DESC"
        )
        results = []
        for row in profiles:
            evidence_rows = await conn.fetch(
                """SELECT source_ref,kind,heading,body,metadata_json FROM candidate_evidence
                     WHERE candidate_id=$1 ORDER BY created_at""",
                row["id"],
            )
            payload = _json_object(row["profile_json"])
            payload.update(
                {
                    "name": row["name"],
                    "headline": row["headline"],
                    "evidence": [
                        {
                            "source_ref": item["source_ref"],
                            "kind": item["kind"],
                            "heading": item["heading"],
                            "text": item["body"],
                            "metadata": _json_object(item["metadata_json"]),
                        }
                        for item in evidence_rows
                    ],
                }
            )
            results.append(
                {
                    "id": str(row["id"]),
                    "user_id": str(row["user_id"]),
                    "profile": CandidateProfileUpdate.model_validate(payload),
                }
            )
    return results


async def get_job_posting(tenant_id: str, job_id: UUID) -> JobPostingIn:
    async with tenant_connection(tenant_id) as conn:
        row = await conn.fetchrow(
            """SELECT source,coalesce(canonical_url,source_url) AS source_url,title,company,
                      description,location,rate_min,rate_max,contract_duration,
                      engagement_type,posted_at FROM jobs WHERE id=$1""",
            job_id,
        )
    if not row:
        raise KeyError(job_id)
    return JobPostingIn.model_validate(dict(row))


async def get_job_evidence(tenant_id: str, job_id: UUID) -> list[Evidence]:
    async with tenant_connection(tenant_id) as conn:
        rows = await conn.fetch(
            """SELECT citation,section,body,metadata_json FROM job_evidence
                 WHERE job_id=$1 ORDER BY CASE section WHEN 'metadata' THEN 0 ELSE 1 END,citation""",
            job_id,
        )
    return [
        Evidence(
            row["body"], "role", row["citation"], {"section": row["section"], **_json_object(row["metadata_json"])}
        )
        for row in rows
    ]


async def reindex_job_evidence(tenant_id: str) -> int:
    """Backfill chunks for roles that existed before the evidence index shipped."""
    async with tenant_connection(tenant_id) as conn:
        rows = await conn.fetch(
            """SELECT id,source,coalesce(canonical_url,source_url) AS source_url,title,company,description,
                      location,rate_min,rate_max,posted_at FROM jobs"""
        )
    from .models import JobPostingIn

    for row in rows:
        await index_job_evidence(tenant_id, str(row["id"]), JobPostingIn.model_validate(dict(row)))
    return len(rows)


async def list_jobs_for_matching(tenant_id: str, limit: int = 100) -> list[tuple[str, object, list[Evidence]]]:
    async with tenant_connection(tenant_id) as conn:
        rows = await conn.fetch(
            """SELECT id,source,coalesce(canonical_url,source_url) AS source_url,title,company,description,
                      location,rate_min,rate_max,posted_at FROM jobs WHERE status='new'
                 ORDER BY fit_score DESC,posted_at DESC NULLS LAST LIMIT $1""",
            limit,
        )
    from .models import JobPostingIn

    result = []
    for row in rows:
        job_id = str(row["id"])
        result.append(
            (job_id, JobPostingIn.model_validate(dict(row)), await get_job_evidence(tenant_id, row["id"]))
        )
    return result


async def list_jobs(tenant_id: str, minimum_score: int = 0):
    async with tenant_connection(tenant_id) as conn:
        rows = await conn.fetch(
            """SELECT j.id,j.title,j.company,j.description,j.location,j.rate_min,j.rate_max,
                      j.contract_duration,j.engagement_type,j.c2c_status,
                      j.fit_score,j.status,j.created_at,j.posted_at,j.last_source_seen_at,
                      j.hidden_reason,j.applied_at,j.follow_up_at,j.closed_at,
                      j.source_url,j.canonical_url,
                      j.source_authority,j.provenance_confidence,j.provenance_completeness,
                      j.quality_lane,j.vendor_layer_min,j.vendor_layer_max,j.end_client_name,
                      j.last_verified_at,p.name AS provider_name,p.provider_type,
                      coalesce((j.screening_json->'reasons')::jsonb,'[]'::jsonb) AS reasons,
                      coalesce((j.screening_json->'risks')::jsonb,'[]'::jsonb) AS risks,
                      (SELECT count(*) FROM job_observations o WHERE o.canonical_job_id=j.id) AS observation_count
                 FROM jobs j
                 LEFT JOIN providers p ON p.id=j.canonical_provider_id
                WHERE j.fit_score >= $1
                ORDER BY CASE j.quality_lane WHEN 'direct_prime' THEN 0 WHEN 'needs_verification' THEN 1 ELSE 2 END,
                         j.source_authority DESC,j.fit_score DESC,j.created_at DESC LIMIT 200""",
            minimum_score,
        )
        results = [dict(row) for row in rows]
        for result in results:
            result["reasons"] = _json_list(result.get("reasons"))
            result["risks"] = _json_list(result.get("risks"))
        return results


async def start_source_sync_run(tenant_id: str, target_slug: str, adapter: str, query: str | None) -> str:
    async with tenant_connection(tenant_id) as conn:
        run_id = await conn.fetchval(
            """INSERT INTO source_sync_runs(tenant_id,target_slug,adapter,query,status)
                 VALUES($1,$2,$3,$4,'running') RETURNING id""",
            tenant_id,
            target_slug,
            adapter,
            query,
        )
    return str(run_id)


async def finish_source_sync_run(
    tenant_id: str, run_id: str, *, received: int = 0, selected: int = 0,
    created: int = 0, enriched: int = 0, error_code: str | None = None,
) -> None:
    async with tenant_connection(tenant_id) as conn:
        await conn.execute(
            """UPDATE source_sync_runs SET status=$3,received_count=$4,selected_count=$5,
                   created_count=$6,enriched_count=$7,error_code=$8,completed_at=now()
                 WHERE id=$1 AND tenant_id=$2""",
            UUID(run_id),
            tenant_id,
            "failed" if error_code else "succeeded",
            received,
            selected,
            created,
            enriched,
            error_code,
        )


async def list_source_health(tenant_id: str) -> list[dict]:
    """Truthful source health: observed success, freshness, and fact coverage—not assumptions."""
    async with tenant_connection(tenant_id) as conn:
        rows = await conn.fetch(
            """WITH runs AS (
                  SELECT target_slug,adapter,max(started_at) AS last_run_at,
                         count(*) FILTER (WHERE status='succeeded') AS successful_runs,
                         count(*) FILTER (WHERE status='failed') AS failed_runs,
                         max(error_code) FILTER (WHERE status='failed') AS last_error
                  FROM source_sync_runs GROUP BY target_slug,adapter
                ), facts AS (
                  SELECT p.slug,
                    count(o.id) AS observations,
                    coalesce(avg((o.rate_max IS NOT NULL OR o.rate_min IS NOT NULL)::int),0) AS rate_coverage,
                    coalesce(avg((o.engagement_type IS NOT NULL)::int),0) AS engagement_coverage,
                    max(o.last_observed_at) AS last_observed_at
                  FROM providers p LEFT JOIN job_observations o ON o.provider_id=p.id
                  GROUP BY p.slug
                )
                SELECT runs.target_slug,runs.adapter,runs.last_run_at,runs.successful_runs,runs.failed_runs,runs.last_error,
                       facts.observations,facts.rate_coverage,facts.engagement_coverage,facts.last_observed_at
                FROM runs LEFT JOIN facts ON facts.slug=('employer-' || runs.adapter || '-' || lower(runs.target_slug))
                ORDER BY runs.last_run_at DESC"""
        )
    return [dict(row) for row in rows]


async def create_application_package(
    tenant_id: str, job_id: str, candidate_id: str, package: dict
) -> dict:
    async with tenant_connection(tenant_id) as conn:
        row = await conn.fetchrow(
            """INSERT INTO application_packages(
                 tenant_id,job_id,candidate_id,resume_evidence_json,role_evidence_json,gaps_json,
                 verification_json,cover_note
               ) VALUES($1,$2,$3,$4::jsonb,$5::jsonb,$6::jsonb,$7::jsonb,$8)
               RETURNING id,status,resume_evidence_json,role_evidence_json,gaps_json,verification_json,
                         cover_note,created_at,updated_at""",
            tenant_id, UUID(job_id), UUID(candidate_id),
            json.dumps(package["resume_evidence"]), json.dumps(package["role_evidence"]),
            json.dumps(package["gaps"]), json.dumps(package["verification"]), package["cover_note"],
        )
    return _application_package_row(row)


async def list_application_packages(tenant_id: str, job_id: str) -> list[dict]:
    async with tenant_connection(tenant_id) as conn:
        rows = await conn.fetch(
            """SELECT id,status,resume_evidence_json,role_evidence_json,gaps_json,verification_json,
                      cover_note,created_at,updated_at
                 FROM application_packages WHERE job_id=$1 ORDER BY updated_at DESC""",
            UUID(job_id),
        )
    return [_application_package_row(row) for row in rows]


async def update_application_package_status(tenant_id: str, package_id: str, status: str) -> None:
    async with tenant_connection(tenant_id) as conn:
        result = await conn.execute(
            "UPDATE application_packages SET status=$3,updated_at=now() WHERE id=$1 AND tenant_id=$2",
            UUID(package_id), tenant_id, status,
        )
    if result.endswith("0"):
        raise KeyError(package_id)


def _application_package_row(row) -> dict:
    result = dict(row)
    for key in ("resume_evidence_json", "role_evidence_json", "gaps_json", "verification_json"):
        result[key.removesuffix("_json")] = _json_list(result.pop(key))
    return result


async def move_job(
    tenant_id: str, job_id: UUID, status: str, hidden_reason: str | None = None, follow_up_at=None
):
    async with tenant_connection(tenant_id) as conn:
        result = await conn.execute(
            """UPDATE jobs SET status=$1, hidden_reason=CASE WHEN $1='passed' THEN $3 ELSE hidden_reason END,
               hidden_at=CASE WHEN $1='passed' THEN now() ELSE hidden_at END,
               applied_at=CASE WHEN $1='submitted' AND applied_at IS NULL THEN now() ELSE applied_at END,
               follow_up_at=coalesce($4, follow_up_at), closed_at=CASE WHEN $1 IN ('offer','rejected','passed') THEN now() ELSE closed_at END,
               updated_at=now() WHERE id=$2""",
            status,
            job_id,
            hidden_reason,
            follow_up_at,
        )
        if result.endswith("0"):
            raise KeyError(job_id)


async def record_job_decision(
    tenant_id: str, user_id: str, job_id: UUID, decision: JobDecisionIn
) -> dict:
    status = "rejected" if decision.outcome == "denied" else "passed"
    async with tenant_connection(tenant_id) as conn:
        updated = await conn.fetchval(
            "UPDATE jobs SET status=$1,updated_at=now() WHERE id=$2 RETURNING id",
            status,
            job_id,
        )
        if updated is None:
            raise KeyError(job_id)
        row = await conn.fetchrow(
            """INSERT INTO job_decisions(tenant_id,job_id,user_id,outcome,reason_code,notes)
               VALUES($1,$2,$3,$4,$5,$6)
               RETURNING id,outcome,reason_code,notes,created_at""",
            tenant_id,
            job_id,
            user_id,
            decision.outcome,
            decision.reason_code,
            decision.notes,
        )
        return dict(row)


async def list_job_decisions(tenant_id: str, job_id: UUID) -> list[dict]:
    async with tenant_connection(tenant_id) as conn:
        exists = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM jobs WHERE id=$1)", job_id)
        if not exists:
            raise KeyError(job_id)
        rows = await conn.fetch(
            """SELECT id,outcome,reason_code,notes,created_at
                 FROM job_decisions WHERE job_id=$1 ORDER BY created_at DESC""",
            job_id,
        )
        return [dict(row) for row in rows]


async def get_feedback_penalties(tenant_id: str) -> dict[str, int]:
    async with tenant_connection(tenant_id) as conn:
        rows = await conn.fetch(
            """SELECT reason_code,count(*)::int AS uses
                 FROM job_decisions
                WHERE created_at>=now()-interval '180 days'
                GROUP BY reason_code"""
        )
        return {row["reason_code"]: row["uses"] for row in rows}


async def update_job_corrections(
    tenant_id: str, job_id: UUID, correction: JobCorrectionIn
) -> None:
    values = correction.model_dump(exclude_unset=True, exclude_none=True)
    if not values:
        raise ValueError("At least one correction is required")
    assignments = []
    arguments = [job_id]
    for field, value in values.items():
        arguments.append(value)
        assignments.append(f"{field}=${len(arguments)}")
    async with tenant_connection(tenant_id) as conn:
        updated = await conn.fetchval(
            f"UPDATE jobs SET {','.join(assignments)},updated_at=now() WHERE id=$1 RETURNING id",
            *arguments,
        )
        if not updated:
            raise KeyError(job_id)


async def export_tenant_data(tenant_id: str, user_id: str) -> dict:
    async with tenant_connection(tenant_id) as conn:
        profile = await conn.fetchrow(
            """SELECT profile_json,resume_file_name,resume_content_type,resume_size_bytes,
                      resume_uploaded_at,updated_at FROM search_profiles WHERE user_id=$1""",
            user_id,
        )
        jobs = await conn.fetch(
            """SELECT id,source,source_url,title,company,description,location,rate_min,rate_max,
                      contract_duration,engagement_type,c2c_status,fit_score,status,screening_json,
                      created_at,updated_at FROM jobs ORDER BY created_at"""
        )
        decisions = await conn.fetch(
            "SELECT job_id,outcome,reason_code,notes,created_at FROM job_decisions ORDER BY created_at"
        )
        recruiters = await conn.fetch(
            """SELECT name,email,company,relationship_stage,source,notes,last_contacted_at,
                      next_follow_up_at,created_at,updated_at FROM recruiter_contacts ORDER BY created_at"""
        )
        runs = await conn.fetch(
            """SELECT id,kind,status,result_json,error_code,attempts,created_at,started_at,
                      completed_at FROM acquisition_runs ORDER BY created_at"""
        )
    return {
        "format": "c2cdirect-core-export-v1",
        "profile": dict(profile) if profile else None,
        "jobs": [dict(row) for row in jobs],
        "decisions": [dict(row) for row in decisions],
        "recruiters": [dict(row) for row in recruiters],
        "acquisition_runs": [dict(row) for row in runs],
    }


async def find_job_by_fingerprint(tenant_id: str, fingerprint: str) -> str | None:
    async with tenant_connection(tenant_id) as conn:
        job_id = await conn.fetchval("SELECT id FROM jobs WHERE fingerprint=$1", fingerprint)
        return str(job_id) if job_id else None


async def claim_ingestion_event(
    tenant_id: str, provider: str, event_id: str, payload_sha256: str
) -> tuple[str, dict | None]:
    """Claim a tenant-namespaced provider event or return its prior state."""
    internal_id = f"{provider}:{tenant_id}:{event_id}"
    async with tenant_connection(tenant_id) as conn:
        inserted = await conn.fetchval(
            """INSERT INTO webhook_events(id,tenant_id,provider,event_type,payload_sha256,status)
               VALUES($1,$2,$3,'job_batch',$4,'processing')
               ON CONFLICT(id) DO NOTHING RETURNING id""",
            internal_id,
            tenant_id,
            provider,
            payload_sha256,
        )
        if inserted:
            return "claimed", None
        row = await conn.fetchrow(
            "SELECT payload_sha256,status,response_json FROM webhook_events WHERE id=$1",
            internal_id,
        )
        if not row or row["payload_sha256"] != payload_sha256:
            raise ValueError("Ingestion event ID was reused with a different payload")
        if row["status"] == "failed":
            await conn.execute(
                "UPDATE webhook_events SET status='processing',response_json=NULL WHERE id=$1",
                internal_id,
            )
            return "claimed", None
        response = json.loads(row["response_json"]) if row["response_json"] else None
        return str(row["status"]), response


async def complete_ingestion_event(
    tenant_id: str, provider: str, event_id: str, status: str, response: dict
):
    internal_id = f"{provider}:{tenant_id}:{event_id}"
    async with tenant_connection(tenant_id) as conn:
        await conn.execute(
            """UPDATE webhook_events
                  SET status=$1,response_json=$2,processed_at=now()
                WHERE id=$3""",
            status,
            json.dumps(response),
            internal_id,
        )


async def get_tenant_plan(tenant_id: str) -> str:
    async with tenant_connection(tenant_id) as conn:
        plan = await conn.fetchval("SELECT plan FROM tenants WHERE id=$1", tenant_id)
        if plan is None:
            raise KeyError(tenant_id)
        return str(plan)


async def reserve_mcp_call(
    tenant_id: str,
    user_id: str,
    request_id: str,
    tool_name: str,
    scopes: tuple[str, ...],
    daily_limit: int,
) -> str:
    """Atomically reserve one metered MCP call and create its audit record."""
    async with tenant_connection(tenant_id) as conn:
        audit_id = await conn.fetchval(
            "SELECT reserve_mcp_call($1,$2,$3,$4,$5,$6)",
            tenant_id,
            user_id,
            request_id,
            tool_name,
            list(scopes),
            daily_limit,
        )
        if audit_id is None:
            raise OverflowError("Daily MCP call allowance exhausted")
        return str(audit_id)


async def complete_mcp_call(
    tenant_id: str, audit_id: str, status: str, latency_ms: int, error_code: str | None = None
):
    async with tenant_connection(tenant_id) as conn:
        await conn.execute(
            """UPDATE mcp_audit_events
                  SET status=$1, latency_ms=$2, error_code=$3, completed_at=now()
                WHERE id=$4""",
            status,
            latency_ms,
            error_code,
            audit_id,
        )


async def upsert_provider(tenant_id: str, provider: ProviderDefinition) -> str:
    async with tenant_connection(tenant_id) as conn:
        provider_id = await conn.fetchval(
            """INSERT INTO providers(
                 tenant_id,slug,name,provider_type,intake_method,canonical_domain,terms_status,
                 baseline_authority,typical_layer_min,typical_layer_max,direct_source_capable
               ) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
               ON CONFLICT(tenant_id,slug) DO UPDATE SET
                 name=excluded.name,provider_type=excluded.provider_type,
                 intake_method=excluded.intake_method,canonical_domain=excluded.canonical_domain,
                 terms_status=excluded.terms_status,baseline_authority=excluded.baseline_authority,
                 typical_layer_min=excluded.typical_layer_min,
                 typical_layer_max=excluded.typical_layer_max,
                 direct_source_capable=excluded.direct_source_capable,updated_at=now()
               RETURNING id""",
            tenant_id,
            provider.slug,
            provider.name,
            provider.provider_type,
            provider.intake_method,
            provider.canonical_domain,
            provider.terms_status,
            provider.baseline_authority,
            provider.typical_layer_min,
            provider.typical_layer_max,
            provider.direct_source_capable,
        )
        return str(provider_id)


async def list_providers(tenant_id: str) -> list[dict]:
    async with tenant_connection(tenant_id) as conn:
        rows = await conn.fetch(
            """SELECT id,slug,name,provider_type,intake_method,terms_status,baseline_authority,
                      typical_layer_min,typical_layer_max,direct_source_capable,last_verified_at
                 FROM providers ORDER BY baseline_authority DESC,name"""
        )
        return [dict(row) for row in rows]


async def create_recruiter_contact(tenant_id: str, contact: RecruiterContactIn) -> str:
    async with tenant_connection(tenant_id) as conn:
        provider_id = None
        if contact.provider_slug:
            provider_id = await conn.fetchval(
                "SELECT id FROM providers WHERE slug=$1", contact.provider_slug
            )
            if provider_id is None:
                raise KeyError(contact.provider_slug)
        contact_id = await conn.fetchval(
            """INSERT INTO recruiter_contacts(
                 tenant_id,provider_id,name,email,company,relationship_stage,source,notes,next_follow_up_at
               ) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9) RETURNING id""",
            tenant_id,
            provider_id,
            contact.name,
            contact.email,
            contact.company,
            contact.relationship_stage,
            contact.source,
            contact.notes,
            contact.next_follow_up_at,
        )
        return str(contact_id)


async def list_recruiter_contacts(tenant_id: str) -> list[dict]:
    async with tenant_connection(tenant_id) as conn:
        rows = await conn.fetch(
            """SELECT r.id,r.name,r.email,r.company,r.relationship_stage,r.source,r.notes,
                      r.last_contacted_at,r.next_follow_up_at,r.created_at,p.slug AS provider_slug,
                      p.name AS provider_name
                 FROM recruiter_contacts r LEFT JOIN providers p ON p.id=r.provider_id
                ORDER BY CASE r.relationship_stage WHEN 'active' THEN 0 WHEN 'connected' THEN 1 ELSE 2 END,
                         r.next_follow_up_at NULLS LAST,r.created_at DESC"""
        )
        return [dict(row) for row in rows]


async def update_recruiter_contact(
    tenant_id: str, contact_id: UUID, patch: RecruiterContactPatch
) -> None:
    async with tenant_connection(tenant_id) as conn:
        result = await conn.execute(
            """UPDATE recruiter_contacts SET
                 relationship_stage=coalesce($1,relationship_stage),notes=coalesce($2,notes),
                 next_follow_up_at=CASE WHEN $3::boolean THEN $4 ELSE next_follow_up_at END,
                 last_contacted_at=CASE WHEN $5 THEN now() ELSE last_contacted_at END,updated_at=now()
               WHERE id=$6""",
            patch.relationship_stage,
            patch.notes,
            "next_follow_up_at" in patch.model_fields_set,
            patch.next_follow_up_at,
            patch.mark_contacted,
            contact_id,
        )
        if result.endswith("0"):
            raise KeyError(contact_id)


async def list_daily_actions(tenant_id: str) -> dict:
    """Return a concise, evidence-first morning queue.

    This deliberately separates *work that is due* from *roles worth reviewing*.
    A high fit score or an approved package is not represented as an application,
    interview, or relationship claim.
    """
    async with tenant_connection(tenant_id) as conn:
        priority_roles = await conn.fetch(
            """SELECT j.id,j.title,j.company,j.fit_score,j.c2c_status,j.quality_lane,
                      coalesce(j.canonical_url,j.source_url) AS application_url,
                      j.rate_min,j.rate_max,j.location,j.posted_at,j.last_source_seen_at,
                      p.provider_type
                 FROM jobs j
                 LEFT JOIN providers p ON p.id=j.canonical_provider_id
                WHERE j.status IN ('new','saved')
                  AND j.c2c_status <> 'rejected'
                  AND j.quality_lane <> 'low_quality'
                  AND coalesce(j.last_source_seen_at,j.created_at) >= now() - interval '21 days'
                ORDER BY CASE j.status WHEN 'saved' THEN 0 ELSE 1 END,
                         CASE j.c2c_status WHEN 'confirmed' THEN 0 WHEN 'likely' THEN 1 ELSE 2 END,
                         j.fit_score DESC,j.posted_at DESC NULLS LAST
                LIMIT 8"""
        )
        application_reviews = await conn.fetch(
            """SELECT ap.id AS package_id,ap.status AS package_status,ap.updated_at,
                      j.id AS job_id,j.title,j.company,j.fit_score,j.c2c_status,
                      coalesce(j.canonical_url,j.source_url) AS application_url
                 FROM application_packages ap
                 JOIN jobs j ON j.id=ap.job_id
                WHERE ap.status IN ('draft','approved')
                  AND j.status NOT IN ('passed','rejected')
                ORDER BY CASE ap.status WHEN 'approved' THEN 0 ELSE 1 END,
                         ap.updated_at DESC
                LIMIT 8"""
        )
        application_follow_ups = await conn.fetch(
            """SELECT id,title,company,status,follow_up_at,applied_at,
                      coalesce(canonical_url,source_url) AS application_url
                 FROM jobs
                WHERE status IN ('submitted','interview')
                  AND follow_up_at IS NOT NULL AND follow_up_at <= now()
                ORDER BY follow_up_at,id LIMIT 20"""
        )
        recruiter_follow_ups = await conn.fetch(
            """SELECT id,name,email,company,relationship_stage,next_follow_up_at
                 FROM recruiter_contacts WHERE relationship_stage NOT IN ('paused','avoid')
                  AND next_follow_up_at IS NOT NULL AND next_follow_up_at <= now()
                ORDER BY next_follow_up_at LIMIT 20"""
        )
        return {
            "priority_roles": [dict(row) for row in priority_roles],
            "application_reviews": [dict(row) for row in application_reviews],
            "application_follow_ups": [dict(row) for row in application_follow_ups],
            "recruiter_follow_ups": [dict(row) for row in recruiter_follow_ups],
        }


async def find_job_by_canonical_key(tenant_id: str, key: str) -> dict | None:
    async with tenant_connection(tenant_id) as conn:
        row = await conn.fetchrow(
            """SELECT id,fit_score,c2c_status,source_authority,quality_lane
                 FROM jobs WHERE canonical_key=$1""",
            key,
        )
        return dict(row) if row else None


async def record_job_observation(
    tenant_id: str,
    provider_id: str,
    job_id: str,
    observation: JobObservation,
    assessment: ProvenanceAssessment,
) -> str:
    """Persist source evidence and promote better canonical provenance."""
    posting = observation.posting
    description_hash = sha256(posting.description.encode()).hexdigest()
    async with tenant_connection(tenant_id) as conn:
        observation_id = await conn.fetchval(
            """INSERT INTO job_observations(
                 tenant_id,provider_id,canonical_job_id,provider_job_id,requisition_id,
                 observed_url,canonical_url_candidate,title,company,end_client_name,location,
                 description_sha256,source_payload_sha256,engagement_type,rate_min,rate_max,
                 recruiter_email_domain,parser_version,confidence,evidence_json,warnings
               ) VALUES(
                 $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21
               ) ON CONFLICT(tenant_id,provider_id,source_payload_sha256) DO UPDATE
                 SET last_observed_at=now()
               RETURNING id""",
            tenant_id,
            provider_id,
            job_id,
            observation.provider_job_id,
            observation.requisition_id,
            str(posting.source_url) if posting.source_url else None,
            observation.canonical_url_candidate,
            posting.title,
            posting.company,
            observation.end_client_name,
            posting.location,
            description_hash,
            observation.payload_hash(),
            observation.engagement_type,
            posting.rate_min,
            posting.rate_max,
            observation.recruiter_email_domain,
            observation.parser_version,
            observation.confidence,
            json.dumps(observation.evidence),
            observation.warnings,
        )
        await conn.execute(
            """UPDATE jobs SET
                 canonical_key=$1,
                 canonical_provider_id=CASE WHEN source_authority <= $2 THEN $3 ELSE canonical_provider_id END,
                 source_authority=greatest(source_authority,$2),
                 provenance_confidence=CASE WHEN source_authority <= $2 THEN $4 ELSE provenance_confidence END,
                 provenance_completeness=greatest(provenance_completeness,$5),
                 quality_lane=CASE WHEN source_authority <= $2 THEN $6 ELSE quality_lane END,
                 vendor_layer_min=CASE WHEN source_authority <= $2 THEN $7 ELSE vendor_layer_min END,
                 vendor_layer_max=CASE WHEN source_authority <= $2 THEN $8 ELSE vendor_layer_max END,
                 end_client_name=coalesce(end_client_name,$9),
                 canonical_url=CASE WHEN source_authority <= $2 THEN $10 ELSE canonical_url END,
                 last_verified_at=now(),last_source_seen_at=now(),
                 posted_at=coalesce(posted_at,$12),updated_at=now()
               WHERE id=$11""",
            assessment.canonical_key,
            assessment.source_authority,
            provider_id,
            assessment.confidence,
            assessment.completeness,
            assessment.quality_lane,
            assessment.layer_min,
            assessment.layer_max,
            observation.end_client_name,
            assessment.canonical_url,
            job_id,
            posting.posted_at,
        )
        return str(observation_id)


async def upsert_email_connection(
    tenant_id: str,
    user_id: str,
    provider: str,
    mailbox_address: str | None,
    encrypted_access_token: str,
    encrypted_refresh_token: str | None,
    token_expires_at,
    scopes: list[str],
) -> str:
    async with tenant_connection(tenant_id) as conn:
        connection_id = await conn.fetchval(
            """INSERT INTO email_connections(
                 tenant_id,user_id,provider,mailbox_address,encrypted_access_token,
                 encrypted_refresh_token,token_expires_at,scopes,status
               ) VALUES($1,$2,$3,$4,$5,$6,$7,$8,'active')
               ON CONFLICT(tenant_id,user_id,provider) DO UPDATE SET
                 mailbox_address=coalesce(excluded.mailbox_address,email_connections.mailbox_address),
                 encrypted_access_token=excluded.encrypted_access_token,
                 encrypted_refresh_token=coalesce(excluded.encrypted_refresh_token,email_connections.encrypted_refresh_token),
                 token_expires_at=excluded.token_expires_at,scopes=excluded.scopes,
                 status='active',updated_at=now()
               RETURNING id""",
            tenant_id,
            user_id,
            provider,
            mailbox_address,
            encrypted_access_token,
            encrypted_refresh_token,
            token_expires_at,
            scopes,
        )
        return str(connection_id)


async def list_email_connections(tenant_id: str, user_id: str) -> list[dict]:
    async with tenant_connection(tenant_id) as conn:
        rows = await conn.fetch(
            """SELECT id,provider,mailbox_address,scopes,status,last_synced_at,created_at,updated_at
                 FROM email_connections WHERE user_id=$1 ORDER BY provider""",
            user_id,
        )
        return [dict(row) for row in rows]


async def get_email_connection(tenant_id: str, user_id: str, provider: str) -> dict | None:
    async with tenant_connection(tenant_id) as conn:
        row = await conn.fetchrow(
            """SELECT id,provider,mailbox_address,encrypted_access_token,encrypted_refresh_token,
                      token_expires_at,scopes,status,sync_cursor
                 FROM email_connections WHERE user_id=$1 AND provider=$2""",
            user_id,
            provider,
        )
        return dict(row) if row else None


async def update_email_tokens(
    tenant_id: str,
    connection_id: str,
    encrypted_access_token: str,
    encrypted_refresh_token: str | None,
    token_expires_at,
) -> None:
    async with tenant_connection(tenant_id) as conn:
        await conn.execute(
            """UPDATE email_connections SET encrypted_access_token=$1,
                      encrypted_refresh_token=coalesce($2,encrypted_refresh_token),
                      token_expires_at=$3,status='active',updated_at=now() WHERE id=$4""",
            encrypted_access_token,
            encrypted_refresh_token,
            token_expires_at,
            connection_id,
        )


async def claim_email_message(
    tenant_id: str,
    connection_id: str,
    provider_message_id: str,
    content_sha256: str,
    *,
    internet_message_id: str | None = None,
    sender_address: str | None = None,
    subject: str | None = None,
    received_at=None,
) -> str | None:
    async with tenant_connection(tenant_id) as conn:
        receipt_id = await conn.fetchval(
            """INSERT INTO email_message_receipts(
                 tenant_id,connection_id,provider_message_id,internet_message_id,sender_address,
                 subject,received_at,content_sha256
               ) VALUES($1,$2,$3,$4,$5,$6,$7,$8)
               ON CONFLICT(tenant_id,connection_id,provider_message_id) DO NOTHING RETURNING id""",
            tenant_id,
            connection_id,
            provider_message_id,
            internet_message_id,
            sender_address,
            subject,
            received_at,
            content_sha256,
        )
        return str(receipt_id) if receipt_id else None


async def complete_email_message(
    tenant_id: str, receipt_id: str, status: str, job_id: str | None = None
) -> None:
    async with tenant_connection(tenant_id) as conn:
        await conn.execute(
            "UPDATE email_message_receipts SET status=$1,canonical_job_id=$2 WHERE id=$3",
            status,
            job_id,
            receipt_id,
        )


async def complete_email_sync(tenant_id: str, connection_id: str, cursor: str | None) -> None:
    async with tenant_connection(tenant_id) as conn:
        await conn.execute(
            """UPDATE email_connections SET sync_cursor=coalesce($1,sync_cursor),
                      last_synced_at=now(),updated_at=now() WHERE id=$2""",
            cursor,
            connection_id,
        )
