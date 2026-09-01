from app.mcp_tools import explain_match, request_outreach
from tests.factories import make_posting


def test_explain_match_returns_structured_cited_result():
    result = explain_match(make_posting().model_dump(mode="json"))
    assert result["fit_score"] >= 75
    assert result["evidence"]
    assert all(item["citation"] for item in result["evidence"])


def test_outreach_requires_explicit_human_approval():
    blocked = request_outreach("job-1", "Interested in discussing this role")
    approved = request_outreach("job-1", "Interested in discussing this role", approved=True)
    assert blocked["status"] == "approval_required"
    assert approved["status"] == "queued"
