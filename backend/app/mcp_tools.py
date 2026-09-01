"""Pure tool implementations shared by the MCP adapter and unit tests."""

from .guardrails import validate_tool_call
from .models import JobPostingIn, SearchProfile
from .retrieval import retrieve
from .scoring import screen


def explain_match(posting: dict, profile: dict | None = None) -> dict:
    validate_tool_call("explain_match", {"posting": posting})
    job = JobPostingIn.model_validate(posting)
    result = screen(job, SearchProfile.model_validate(profile or {}))
    evidence = retrieve(job)
    return {
        "fit_score": result.fit_score,
        "c2c_status": result.c2c_status,
        "reasons": result.reasons,
        "risks": result.risks,
        "evidence": [{"text": item.text, "citation": item.citation} for item in evidence],
    }


def request_outreach(job_id: str, message: str, approved: bool = False) -> dict:
    validate_tool_call("request_outreach", {"job_id": job_id, "message": message})
    if not approved:
        return {"status": "approval_required", "job_id": job_id}
    return {"status": "queued", "job_id": job_id, "message": message}
