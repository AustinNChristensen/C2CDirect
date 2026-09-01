import pytest
from fastapi import HTTPException

from app.entitlements import PLANS, Plan, require_feature


def test_pro_has_advanced_observability():
    assert PLANS[Plan.pro].advanced_observability
    assert PLANS[Plan.pro].remote_mcp
    assert PLANS[Plan.pro].daily_mcp_calls == 1_000


def test_community_cannot_generate_outreach():
    with pytest.raises(HTTPException):
        require_feature(Plan.community, "outreach")
    assert not PLANS[Plan.community].remote_mcp
