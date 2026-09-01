from app.models import CandidateEvidenceIn, CandidateProfileUpdate, JobPostingIn


def make_candidate() -> CandidateProfileUpdate:
    return CandidateProfileUpdate(
        headline="Senior AI application engineer",
        location_preferences=["Remote U.S."],
        work_authorization="C2C eligible",
        c2c_preference=True,
        rate_floor=120,
        skills=["TypeScript", "Python", "FastAPI", "LangGraph"],
        evidence=[
            CandidateEvidenceIn(
                source_ref="example:agent-platform",
                kind="project",
                heading="Agent platform",
                text=(
                    "Built a production agent platform using Python, FastAPI, LangGraph, "
                    "TypeScript, evaluations, observability, and secure tool calling."
                ),
            )
        ],
    )


def make_posting(**overrides) -> JobPostingIn:
    values = {
        "source": "test",
        "title": "Senior AI Application Engineer",
        "company": "Example Consulting",
        "description": (
            "Twelve month C2C contract building Python FastAPI LangGraph RAG services "
            "with TypeScript, evaluation, observability, and secure tool calling."
        ),
        "location": "Remote",
        "rate_min": 140,
        "rate_max": 165,
    }
    values.update(overrides)
    return JobPostingIn(**values)
