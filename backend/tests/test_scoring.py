from app.models import C2CStatus, JobPostingIn, SearchProfile
from app.scoring import screen


def test_high_rate_c2c_ai_role_scores_high():
    job = JobPostingIn(
        source="test",
        title="Senior AI Application Engineer",
        company="Acme",
        description="12 month C2C contract using TypeScript Node Python FastAPI LangGraph RAG MCP and AWS.",
        rate_min=150,
        rate_max=175,
        location="Remote",
    )
    result = screen(job, SearchProfile())
    assert result.c2c_status == C2CStatus.confirmed
    assert result.fit_score >= 85


def test_w2_only_is_rejected():
    job = JobPostingIn(
        source="test",
        title="React Engineer",
        company="Acme",
        description="This is a contract role. W2 only. No C2C or third parties. React and Node required.",
        rate_min=80,
        rate_max=95,
    )
    result = screen(job, SearchProfile())
    assert result.c2c_status == C2CStatus.rejected
    assert result.fit_score < 55


def test_decision_feedback_changes_future_ranking_with_an_explanation():
    job = JobPostingIn(
        source="test",
        title="Junior Generalist",
        company="Acme",
        description="Contract opportunity with enough detail to be screened but no listed skills.",
        location="Onsite in another state",
    )
    baseline = screen(job, SearchProfile())
    learned = screen(
        job,
        SearchProfile(
            seniority_levels=["senior"],
            feedback_penalties={
                "location_mismatch": 3,
                "skill_mismatch": 3,
                "c2c_not_accepted": 3,
                "seniority_mismatch": 3,
            },
        ),
    )
    assert learned.fit_score < baseline.fit_score
    assert any("recent decisions" in risk.lower() for risk in learned.risks)
