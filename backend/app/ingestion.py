import re
from hashlib import sha256

from .models import JobPostingIn

_HOURLY_RANGE = re.compile(
    r"\$(?P<minimum>\d{2,3})(?:\.\d{1,2})?\s*(?:-|–|—|to)\s*(?:USD\s*)?\$?(?P<maximum>\d{2,3})(?:\.\d{1,2})?\s*(?:/\s*|per\s+)?(?:hr|hour)s?\b",
    re.IGNORECASE,
)
_HOURLY_SINGLE = re.compile(
    r"(?:rate(?:\s+range)?\s*:?\s*|up\s+to\s+)?\$(?P<rate>\d{2,3})(?:\.\d{1,2})?\s*(?:/\s*|per\s+)(?:hr|hour)s?\b",
    re.IGNORECASE,
)
_DURATION = re.compile(
    r"\b(?P<duration>\d{1,2}(?:\s*(?:-|–|to)\s*\d{1,2})?\s*(?:\+\s*)?(?:month|months|year|years)(?:\s*(?:\+|renewable|with\s+extension))?)\b",
    re.IGNORECASE,
)


def enrich_posting(posting: JobPostingIn) -> JobPostingIn:
    """Fill deterministic commercial fields without overwriting authoritative structured data."""
    text = posting.description
    updates: dict = {}
    if posting.rate_min is None or posting.rate_max is None:
        rate_range = _HOURLY_RANGE.search(text)
        single_rate = _HOURLY_SINGLE.search(text) if not rate_range else None
        if rate_range:
            updates.setdefault("rate_min", int(rate_range.group("minimum")))
            updates.setdefault("rate_max", int(rate_range.group("maximum")))
        elif single_rate:
            rate = int(single_rate.group("rate"))
            updates.setdefault("rate_min", rate)
            updates.setdefault("rate_max", rate)
        if posting.rate_min is not None:
            updates.pop("rate_min", None)
        if posting.rate_max is not None:
            updates.pop("rate_max", None)
    if not posting.contract_duration:
        duration = _DURATION.search(text)
        if duration:
            updates["contract_duration"] = " ".join(duration.group("duration").split())
    if not posting.engagement_type:
        lowered = text.lower()
        types = []
        if "c2c" in lowered or "corp-to-corp" in lowered or "corp to corp" in lowered:
            types.append("C2C")
        if "1099" in lowered or "independent contract" in lowered:
            types.append("1099")
        if re.search(r"\bw-?2\b", lowered):
            types.append("W2")
        if types:
            updates["engagement_type"] = " / ".join(types)
    return posting.model_copy(update=updates) if updates else posting


def normalize_email_alert(subject: str, body: str, source: str = "email") -> JobPostingIn:
    lines = [x.strip() for x in body.splitlines() if x.strip()]
    title = subject.removeprefix("Job alert:").strip() or lines[0]
    company = next(
        (x.split(":", 1)[1].strip() for x in lines if x.lower().startswith("company:")),
        "Unknown company",
    )
    location = next(
        (x.split(":", 1)[1].strip() for x in lines if x.lower().startswith("location:")), "Unknown"
    )
    return enrich_posting(JobPostingIn(
        source=source, title=title, company=company, location=location, description=body
    ))


def content_fingerprint(job: JobPostingIn) -> str:
    value = f"{job.company}|{job.title}|{job.source_url or ''}".lower()
    return sha256(value.encode()).hexdigest()
