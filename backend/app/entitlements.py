from dataclasses import dataclass
from enum import StrEnum

from fastapi import HTTPException


class Plan(StrEnum):
    community = "community"
    solo = "solo"
    pro = "pro"
    team = "team"


@dataclass(frozen=True)
class Entitlements:
    monthly_screenings: int
    automated_sources: int
    profiles: int
    team_members: int
    outreach: bool
    advanced_observability: bool
    remote_mcp: bool
    daily_mcp_calls: int


PLANS = {
    Plan.community: Entitlements(100, 0, 1, 1, False, False, False, 0),
    Plan.solo: Entitlements(2_000, 3, 3, 1, True, False, False, 0),
    Plan.pro: Entitlements(10_000, 10, 10, 1, True, True, True, 1_000),
    Plan.team: Entitlements(50_000, 25, 50, 25, True, True, True, 10_000),
}


def require_feature(plan: Plan, feature: str):
    value = getattr(PLANS[plan], feature, None)
    if not value:
        raise HTTPException(402, f"Feature '{feature}' requires an upgraded plan")
