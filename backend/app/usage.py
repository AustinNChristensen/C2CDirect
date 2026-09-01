from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException
from pydantic_settings import BaseSettings, SettingsConfigDict

from .database import tenant_connection
from .model_runtime import runtime_estimate, runtime_status
from .models import BudgetPolicy, CostEstimate, JobPostingIn, SearchProfile
from .repositories import get_model_connection


class UsageSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    daily_ai_budget_usd: float = 10
    max_run_cost_usd: float = 0.10
    max_run_tokens: int = 12_000


settings = UsageSettings()


def active_policy() -> BudgetPolicy:
    return BudgetPolicy(
        daily_limit_usd=settings.daily_ai_budget_usd,
        per_run_limit_usd=settings.max_run_cost_usd,
        max_total_tokens=settings.max_run_tokens,
    )


@dataclass
class Reservation:
    id: str
    reserved_usd: float


async def reserve_budget(
    tenant_id: str,
    estimate: CostEstimate,
    policy: BudgetPolicy,
    operation: str = "screen_job",
    provider: str = "deterministic",
) -> Reservation:
    if not estimate.allowed:
        raise HTTPException(429, estimate.gate_reason or "Run blocked")
    async with tenant_connection(tenant_id) as conn:
        row = await conn.fetchrow(
            """
          SELECT id,reserved_usd FROM reserve_ai_budget($1,$2,$3,$4)
        """,
            tenant_id,
            datetime.now(UTC).date(),
            estimate.estimated_cost_usd,
            policy.daily_limit_usd,
        )
        if not row:
            raise HTTPException(429, "Tenant daily AI budget exhausted")
        await conn.execute(
            """UPDATE budget_reservations
                  SET operation=$3,provider=$4,model=$5
                WHERE tenant_id=$1 AND id=$2""",
            tenant_id,
            row["id"],
            operation,
            provider,
            estimate.model,
        )
        return Reservation(str(row["id"]), float(row["reserved_usd"]))


async def reconcile_budget(
    tenant_id: str, reservation_id: str, actual_usd: float, input_tokens: int, output_tokens: int
):
    async with tenant_connection(tenant_id) as conn:
        await conn.execute(
            "SELECT reconcile_ai_budget($1,$2,$3,$4,$5)",
            tenant_id,
            reservation_id,
            actual_usd,
            input_tokens,
            output_tokens,
        )


async def release_budget(tenant_id: str, reservation_id: str) -> None:
    async with tenant_connection(tenant_id) as conn:
        await conn.execute(
            "UPDATE budget_reservations SET status='released',reconciled_at=now() WHERE tenant_id=$1 AND id=$2 AND status='reserved'",
            tenant_id,
            reservation_id,
        )


async def metered_screening(
    tenant_id: str,
    graph,
    posting: JobPostingIn,
    profile: SearchProfile,
    policy: BudgetPolicy | None = None,
    operation: str = "screen_job",
):
    active = policy or active_policy()
    config = await get_model_connection(tenant_id)
    preflight = runtime_estimate(max(500, len(posting.description) // 3), 600, active, config)
    runtime = runtime_status(config)
    reservation = await reserve_budget(
        tenant_id,
        preflight,
        active,
        operation=operation,
        provider=runtime["provider"],
    )
    try:
        result = await graph.ainvoke(
            {
                "posting": posting,
                "profile": profile,
                "policy": active,
                "runtime_config": config or {},
            }
        )
    except Exception:
        await release_budget(tenant_id, reservation.id)
        raise
    estimate = result["cost_estimate"]
    usage = result.get("model_usage")
    await reconcile_budget(
        tenant_id,
        reservation.id,
        usage.actual_cost_usd if usage else estimate.estimated_cost_usd,
        usage.input_tokens if usage else estimate.estimated_input_tokens,
        usage.output_tokens if usage else estimate.estimated_output_tokens,
    )
    return result


async def control_room_summary(tenant_id: str, policy: BudgetPolicy, runtime: dict) -> dict:
    async with tenant_connection(tenant_id) as conn:
        totals = await conn.fetchrow(
            """SELECT
                 coalesce(sum(actual_usd) FILTER (WHERE usage_date=current_date AND status='reconciled'),0) today_spend,
                 coalesce(sum(actual_usd) FILTER (WHERE usage_date>=current_date-29 AND status='reconciled'),0) month_spend,
                 coalesce(avg(actual_usd) FILTER (WHERE usage_date>=current_date-29 AND status='reconciled'),0) average_cost,
                 coalesce(sum(input_tokens) FILTER (WHERE usage_date>=current_date-29 AND status='reconciled'),0) input_tokens,
                 coalesce(sum(output_tokens) FILTER (WHERE usage_date>=current_date-29 AND status='reconciled'),0) output_tokens,
                 count(*) FILTER (WHERE usage_date=current_date AND status='reconciled') today_runs,
                 count(*) FILTER (WHERE usage_date>=current_date-29 AND status='reconciled') month_runs,
                 count(*) FILTER (WHERE status='released' AND usage_date>=current_date-29) failed_runs
               FROM budget_reservations WHERE tenant_id=$1""",
            tenant_id,
        )
        daily_rows = await conn.fetch(
            """SELECT usage_date,
                      coalesce(sum(actual_usd) FILTER (WHERE status='reconciled'),0) spend,
                      count(*) FILTER (WHERE status='reconciled') runs
                 FROM budget_reservations
                WHERE tenant_id=$1 AND usage_date>=current_date-13
                GROUP BY usage_date ORDER BY usage_date""",
            tenant_id,
        )
        recent_rows = await conn.fetch(
            """SELECT id,operation,provider,model,status,input_tokens,output_tokens,
                      coalesce(actual_usd,reserved_usd) cost_usd,created_at,reconciled_at
                 FROM budget_reservations WHERE tenant_id=$1
                ORDER BY created_at DESC LIMIT 10""",
            tenant_id,
        )
    return {
        "runtime": runtime,
        "policy": policy.model_dump(),
        "today_spend": float(totals["today_spend"]),
        "month_spend": float(totals["month_spend"]),
        "average_cost": float(totals["average_cost"]),
        "input_tokens": int(totals["input_tokens"]),
        "output_tokens": int(totals["output_tokens"]),
        "today_runs": int(totals["today_runs"]),
        "month_runs": int(totals["month_runs"]),
        "failed_runs": int(totals["failed_runs"]),
        "daily": [
            {
                "date": row["usage_date"].isoformat(),
                "spend": float(row["spend"]),
                "runs": int(row["runs"]),
            }
            for row in daily_rows
        ],
        "recent_runs": [
            {
                **dict(row),
                "id": str(row["id"]),
                "cost_usd": float(row["cost_usd"]),
                "created_at": row["created_at"].isoformat(),
                "reconciled_at": (
                    row["reconciled_at"].isoformat() if row["reconciled_at"] else None
                ),
            }
            for row in recent_rows
        ],
    }
