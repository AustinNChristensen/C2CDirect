from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class C2CStatus(StrEnum):
    confirmed = "confirmed"
    likely = "likely"
    rejected = "rejected"
    unknown = "unknown"


class JobPostingIn(BaseModel):
    source: str = Field(min_length=2, max_length=80)
    source_url: HttpUrl | None = None
    title: str = Field(min_length=3, max_length=180)
    company: str = Field(min_length=2, max_length=180)
    description: str = Field(min_length=40)
    location: str = "Unknown"
    rate_min: int | None = Field(default=None, ge=20, le=500)
    rate_max: int | None = Field(default=None, ge=20, le=500)
    contract_duration: str | None = Field(default=None, max_length=80)
    engagement_type: str | None = Field(default=None, max_length=80)
    recruiter_email: str | None = None
    posted_at: datetime | None = None

    @model_validator(mode="after")
    def rate_order(self):
        if self.rate_min and self.rate_max and self.rate_min > self.rate_max:
            raise ValueError("rate_min cannot exceed rate_max")
        return self


class SearchProfile(BaseModel):
    min_rate: int = 130
    target_rate: int = 145
    locations: list[str] = ["Remote", "Salt Lake City"]
    core_skills: list[str] = ["typescript", "node", "react", "next.js", "aws"]
    ai_skills: list[str] = ["python", "fastapi", "langgraph", "rag", "mcp", "evals"]
    require_c2c: bool = True
    target_roles: list[str] = []
    seniority_levels: list[str] = []
    work_modes: list[str] = ["remote", "hybrid"]
    feedback_penalties: dict[str, int] = {}


class CandidateProfile(BaseModel):
    display_name: str = Field(default="Independent Engineer", min_length=2, max_length=120)
    headline: str = Field(default="Independent consultant", max_length=180)
    bio: str = Field(default="", max_length=2000)
    target_roles: list[str] = Field(default_factory=list, max_length=20)
    seniority_levels: list[str] = Field(default_factory=list, max_length=8)
    min_rate: int = Field(default=75, ge=20, le=500)
    target_rate: int = Field(default=100, ge=20, le=500)
    locations: list[str] = Field(default_factory=list, max_length=20)
    work_modes: list[str] = Field(default_factory=lambda: ["remote"], max_length=3)
    core_skills: list[str] = Field(default_factory=list, max_length=50)
    ai_skills: list[str] = Field(default_factory=list, max_length=50)
    require_c2c: bool = True
    onboarding_completed: bool = False

    @model_validator(mode="after")
    def valid_profile(self):
        if self.target_rate < self.min_rate:
            raise ValueError("target_rate cannot be below min_rate")
        allowed_modes = {"remote", "hybrid", "onsite"}
        if not set(self.work_modes).issubset(allowed_modes):
            raise ValueError("work_modes contains an unsupported value")
        if self.onboarding_completed:
            if not self.target_roles:
                raise ValueError("add at least one target role")
            if not self.locations:
                raise ValueError("add at least one preferred location")
            if not self.core_skills and not self.ai_skills:
                raise ValueError("add at least one skill")
        return self


class JobDecisionIn(BaseModel):
    outcome: str = Field(pattern=r"^(not_interested|denied)$")
    reason_code: str = Field(
        pattern=(
            r"^(c2c_not_accepted|rate_below_floor|skill_mismatch|location_mismatch|"
            r"seniority_mismatch|vendor_chain_concern|role_not_compelling|expired_or_filled|"
            r"denied_by_client|no_response|timing|other)$"
        )
    )
    notes: str | None = Field(default=None, max_length=2000)


class JobCorrectionIn(BaseModel):
    rate_min: int | None = Field(default=None, ge=20, le=500)
    rate_max: int | None = Field(default=None, ge=20, le=500)
    location: str | None = Field(default=None, min_length=2, max_length=180)
    contract_duration: str | None = Field(default=None, max_length=80)
    engagement_type: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def valid_correction(self):
        if self.rate_min and self.rate_max and self.rate_min > self.rate_max:
            raise ValueError("rate_min cannot exceed rate_max")
        if not self.model_fields_set:
            raise ValueError("provide at least one correction")
        return self


class SearchProfileUpdate(SearchProfile):
    """The active, user-owned profile used for founder sourcing."""

    name: str = Field(default="My active search", min_length=2, max_length=120)


class CandidateEvidenceIn(BaseModel):
    """One resume fact, experience bullet, project outcome, or capability claim.

    Evidence stays atomic so a match can cite exactly what it relied on rather
    than treating an entire resume as proof of every claim.
    """

    source_ref: str = Field(min_length=2, max_length=160)
    kind: str = Field(pattern=r"^(experience|project|skill|summary)$")
    heading: str = Field(min_length=2, max_length=200)
    text: str = Field(min_length=8, max_length=4000)
    metadata: dict[str, str] = Field(default_factory=dict)


class CandidateProfileUpdate(BaseModel):
    name: str = Field(default="My candidate profile", min_length=2, max_length=120)
    headline: str = Field(min_length=3, max_length=240)
    location_preferences: list[str] = Field(default_factory=lambda: ["Remote U.S."])
    work_authorization: str = Field(default="U.S. authorized", max_length=240)
    c2c_preference: bool = True
    rate_floor: int | None = Field(default=None, ge=20, le=500)
    skills: list[str] = Field(default_factory=list)
    evidence: list[CandidateEvidenceIn] = Field(default_factory=list, max_length=100)


class ScreenedJob(BaseModel):
    posting: JobPostingIn
    c2c_status: C2CStatus
    fit_score: int = Field(ge=0, le=100)
    skill_matches: list[str]
    skill_gaps: list[str]
    reasons: list[str]
    risks: list[str]
    vendor_layers: int | None = None
    recommended_action: str


class N8NBatch(BaseModel):
    run_id: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    jobs: list[JobPostingIn] = Field(min_length=1, max_length=250)
    refresh_existing: bool = False
    retain_all_in_pipeline: bool = False


class JobImportRequest(BaseModel):
    jobs: list[JobPostingIn] = Field(min_length=1, max_length=250)
    refresh_existing: bool = False
    retain_all_in_pipeline: bool = True


class ModelConnectionIn(BaseModel):
    provider: str = Field(pattern=r"^(deterministic|openai_compatible)$")
    base_url: str = Field(default="", max_length=500)
    model_name: str = Field(default="local-rules", min_length=1, max_length=180)
    api_key: str | None = Field(default=None, max_length=4096)
    clear_api_key: bool = False
    input_cost_per_million: float = Field(default=0, ge=0, le=1000)
    output_cost_per_million: float = Field(default=0, ge=0, le=1000)

    @field_validator("base_url")
    @classmethod
    def valid_base_url(cls, value: str) -> str:
        clean = value.strip().rstrip("/")
        if clean and not clean.startswith(("http://", "https://")):
            raise ValueError("base_url must begin with http:// or https://")
        if "@" in clean.split("://", 1)[-1].split("/", 1)[0]:
            raise ValueError("base_url cannot contain credentials")
        return clean

    @model_validator(mode="after")
    def valid_connection(self):
        if self.provider == "openai_compatible" and not self.base_url:
            raise ValueError("base_url is required for an OpenAI-compatible model")
        if self.provider == "deterministic":
            self.base_url = ""
            self.model_name = "local-rules"
            self.api_key = None
            self.clear_api_key = True
            self.input_cost_per_million = 0
            self.output_cost_per_million = 0
        return self


class SourceSyncRequest(BaseModel):
    priorities: list[int] = Field(default_factory=lambda: [1, 2, 3], min_length=1, max_length=5)
    source_slugs: list[str] = Field(default_factory=list, max_length=100)
    total_limit: int = Field(default=200, ge=1, le=200)
    per_target_limit: int = Field(default=20, ge=1, le=50)
    query: str | None = Field(default=None, min_length=2, max_length=160)

    @model_validator(mode="after")
    def valid_priorities(self):
        if any(priority < 1 or priority > 5 for priority in self.priorities):
            raise ValueError("priorities must be between 1 and 5")
        self.priorities = sorted(set(self.priorities))
        self.source_slugs = list(dict.fromkeys(self.source_slugs))
        if self.query is not None:
            self.query = " ".join(self.query.split()) or None
        return self


class WebSearchConnectionIn(BaseModel):
    provider: str = Field(pattern=r"^(disabled|searxng|tavily|brave)$")
    base_url: str = Field(default="", max_length=500)
    api_key: str | None = Field(default=None, max_length=4096)
    clear_api_key: bool = False

    @field_validator("base_url")
    @classmethod
    def valid_search_base_url(cls, value: str) -> str:
        clean = value.strip().rstrip("/")
        if clean and not clean.startswith(("http://", "https://")):
            raise ValueError("base_url must begin with http:// or https://")
        if "@" in clean.split("://", 1)[-1].split("/", 1)[0]:
            raise ValueError("base_url cannot contain credentials")
        return clean

    @model_validator(mode="after")
    def valid_search_connection(self):
        if self.provider == "searxng" and not self.base_url:
            raise ValueError("base_url is required for SearXNG")
        if self.provider == "disabled":
            self.base_url = ""
            self.api_key = None
            self.clear_api_key = True
        return self


class WebScoutRequest(BaseModel):
    focus: str = Field(default="", max_length=300)
    max_results: int = Field(default=20, ge=1, le=50)
    domains: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("domains")
    @classmethod
    def valid_domains(cls, values: list[str]) -> list[str]:
        cleaned = []
        for value in values:
            domain = value.strip().lower().removeprefix("https://").removeprefix("http://")
            domain = domain.split("/", 1)[0]
            if not domain or len(domain) > 253 or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789.-" for char in domain):
                raise ValueError("domains must contain host names only")
            cleaned.append(domain)
        return list(dict.fromkeys(cleaned))


class AcquisitionRunIn(BaseModel):
    kind: str = Field(pattern=r"^(public_sources|web_scout|email_sync|import)$")
    request: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_run_request(self):
        if len(str(self.request)) > 2_000_000:
            raise ValueError("acquisition request is too large")
        return self


class JobStatusUpdate(BaseModel):
    status: str = Field(pattern=r"^(new|saved|contacted|submitted|interview|offer|rejected|passed)$")
    hidden_reason: str | None = Field(default=None, max_length=500)
    follow_up_at: datetime | None = None


class ApplicationPackageStatusUpdate(BaseModel):
    status: str = Field(pattern=r"^(draft|approved|submitted|archived)$")


class RecruiterContactIn(BaseModel):
    provider_slug: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]{1,62}$")
    name: str = Field(min_length=2, max_length=160)
    email: str | None = Field(default=None, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    company: str | None = Field(default=None, max_length=160)
    relationship_stage: str = Field(
        default="target", pattern=r"^(target|connected|active|paused|avoid)$"
    )
    source: str = Field(default="manual", max_length=80)
    notes: str | None = Field(default=None, max_length=4000)
    next_follow_up_at: datetime | None = None


class RecruiterContactPatch(BaseModel):
    relationship_stage: str | None = Field(
        default=None, pattern=r"^(target|connected|active|paused|avoid)$"
    )
    notes: str | None = Field(default=None, max_length=4000)
    next_follow_up_at: datetime | None = None
    mark_contacted: bool = False


class BudgetPolicy(BaseModel):
    daily_limit_usd: float = Field(default=10, gt=0)
    per_run_limit_usd: float = Field(default=0.10, gt=0)
    max_total_tokens: int = Field(default=12_000, ge=100)
    max_graph_steps: int = Field(default=12, ge=1, le=100)
    max_retries: int = Field(default=2, ge=0, le=10)
    require_approval_above_usd: float = Field(default=0.05, ge=0)


class CostEstimate(BaseModel):
    model: str
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost_usd: float
    allowed: bool
    gate_reason: str | None = None


class RunSummary(BaseModel):
    trace_id: str
    status: str
    graph_steps: int
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0
    actual_cost_usd: float | None = None
    latency_ms: float
    model: str | None = None
    policy_decisions: list[str] = []
