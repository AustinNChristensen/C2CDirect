from pydantic import BaseModel, Field


class EvaluationResult(BaseModel):
    groundedness: float = Field(ge=0, le=1)
    schema_valid: bool
    c2c_classification_correct: bool | None = None
    rank_relevance: float = Field(ge=0, le=1)
    passed: bool
    citation_coverage: float = Field(default=0, ge=0, le=1)
    safety_passed: bool = True


def evaluate_screening(
    reasons: list[str],
    evidence: list[str],
    schema_valid: bool = True,
    citations: list[str] | None = None,
    safety_passed: bool = True,
) -> EvaluationResult:
    supported = sum(
        any(token in e.lower() for e in evidence for token in r.lower().split() if len(token) > 5)
        for r in reasons
    )
    grounded = min(1.0, supported / max(1, len(reasons)))
    relevance = min(1.0, (len(reasons) + len(evidence)) / 8)
    citation_coverage = min(1.0, len(set(citations or [])) / max(1, len(evidence)))
    return EvaluationResult(
        groundedness=grounded,
        schema_valid=schema_valid,
        rank_relevance=relevance,
        citation_coverage=citation_coverage,
        safety_passed=safety_passed,
        passed=schema_valid and grounded >= 0.5 and safety_passed,
    )
