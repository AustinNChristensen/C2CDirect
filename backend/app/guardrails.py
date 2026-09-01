import re
from dataclasses import dataclass, field

from .models import JobPostingIn

PROMPT_INJECTION_PATTERNS = (
    re.compile(r"ignore (all |any )?(previous|prior|system) instructions", re.IGNORECASE),
    re.compile(r"reveal (the )?(system prompt|hidden instructions|secrets?)", re.IGNORECASE),
    re.compile(r"(developer|system) message\s*:", re.IGNORECASE),
    re.compile(r"do not follow (the )?(rules|policy|instructions)", re.IGNORECASE),
)
PII_PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
}


@dataclass(frozen=True)
class GuardrailDecision:
    allowed: bool
    reasons: list[str] = field(default_factory=list)
    redacted_description: str = ""


def inspect_posting(posting: JobPostingIn) -> GuardrailDecision:
    reasons: list[str] = []
    text = posting.description
    if any(pattern.search(text) for pattern in PROMPT_INJECTION_PATTERNS):
        reasons.append("prompt_injection_detected")
    redacted = text
    for label, pattern in PII_PATTERNS.items():
        if pattern.search(redacted):
            reasons.append(f"{label}_redacted")
            redacted = pattern.sub(f"[REDACTED_{label.upper()}]", redacted)
    return GuardrailDecision(
        allowed="prompt_injection_detected" not in reasons,
        reasons=reasons,
        redacted_description=redacted,
    )


ALLOWED_TOOLS = frozenset({"search_jobs", "explain_match", "save_job", "request_outreach"})


def validate_tool_call(tool_name: str, arguments: dict) -> None:
    if tool_name not in ALLOWED_TOOLS:
        raise ValueError("tool_not_allowed")
    if any(key.lower() in {"password", "token", "secret", "api_key"} for key in arguments):
        raise ValueError("sensitive_tool_argument")
