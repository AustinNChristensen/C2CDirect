"""Deterministic provenance, canonicalization, and commercial-quality policy."""

import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, Field

from .models import C2CStatus, JobPostingIn


class ProviderType(StrEnum):
    end_client = "end_client"
    employer_ats = "employer_ats"
    prime_vendor = "prime_vendor"
    msp_vms = "msp_vms"
    staffing_vendor = "staffing_vendor"
    aggregator = "aggregator"
    marketplace = "marketplace"
    email_channel = "email_channel"
    public_agency = "public_agency"
    manual = "manual"


class QualityLane(StrEnum):
    direct_prime = "direct_prime"
    needs_verification = "needs_verification"
    low_quality = "low_quality"


class ProviderDefinition(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,62}$")
    name: str = Field(min_length=2, max_length=120)
    provider_type: ProviderType
    intake_method: str
    canonical_domain: str | None = None
    terms_status: str = "needs_review"
    baseline_authority: int = Field(ge=0, le=100)
    typical_layer_min: int = Field(default=0, ge=0, le=10)
    typical_layer_max: int = Field(default=0, ge=0, le=10)
    direct_source_capable: bool = False


class JobObservation(BaseModel):
    provider_slug: str
    provider_job_id: str | None = None
    requisition_id: str | None = None
    posting: JobPostingIn
    canonical_url_candidate: str | None = None
    end_client_name: str | None = None
    engagement_type: str | None = None
    recruiter_email_domain: str | None = None
    parser_version: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[dict] = []
    warnings: list[str] = []

    def payload_hash(self) -> str:
        return sha256(self.model_dump_json(exclude_none=False).encode()).hexdigest()


@dataclass(frozen=True)
class ProvenanceAssessment:
    canonical_key: str
    canonical_url: str | None
    source_authority: int
    confidence: float
    completeness: float
    quality_lane: QualityLane
    layer_min: int
    layer_max: int
    reasons: tuple[str, ...]


def normalized_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value)
    host = parsed.hostname.lower() if parsed.hostname else ""
    path = re.sub(r"/+$", "", parsed.path)
    return urlunsplit(("https", host, path, "", ""))


def normalized_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def canonical_key(observation: JobObservation) -> str:
    if observation.requisition_id and observation.end_client_name:
        value = f"req|{normalized_text(observation.end_client_name)}|{observation.requisition_id.lower()}"
    else:
        value = "|".join(
            (
                "role",
                normalized_text(observation.end_client_name or observation.posting.company),
                normalized_text(observation.posting.title),
                normalized_text(observation.posting.location),
            )
        )
    return sha256(value.encode()).hexdigest()


def assess_provenance(
    provider: ProviderDefinition,
    observation: JobObservation,
    c2c_status: C2CStatus,
    fit_score: int,
    minimum_rate: int,
) -> ProvenanceAssessment:
    reasons: list[str] = []
    url = normalized_url(
        observation.canonical_url_candidate
        or (str(observation.posting.source_url) if observation.posting.source_url else None)
    )
    completeness_fields = (
        bool(observation.end_client_name),
        bool(observation.requisition_id or observation.provider_job_id),
        bool(url),
        observation.posting.rate_min is not None or observation.posting.rate_max is not None,
        observation.engagement_type is not None,
    )
    completeness = sum(completeness_fields) / len(completeness_fields)
    authority = provider.baseline_authority
    if url and provider.canonical_domain and urlsplit(url).hostname == provider.canonical_domain:
        authority = min(100, authority + 5)
        reasons.append("canonical_provider_domain")
    if observation.end_client_name:
        reasons.append("end_client_identified")
    else:
        authority = max(0, authority - 15)
        reasons.append("end_client_unknown")
    rate_supplied = observation.posting.rate_max is not None or observation.posting.rate_min is not None
    rate_high = observation.posting.rate_max or observation.posting.rate_min or 0
    layer_min = provider.typical_layer_min
    layer_max = provider.typical_layer_max
    direct_or_prime = provider.provider_type in {ProviderType.end_client, ProviderType.employer_ats, ProviderType.prime_vendor}
    if layer_max >= 2:
        reasons.append("multiple_vendor_layers")
    if rate_supplied and rate_high < minimum_rate:
        reasons.append("below_rate_floor")
    elif not rate_supplied:
        reasons.append("rate_unknown")
    if c2c_status == C2CStatus.rejected:
        reasons.append("c2c_rejected")
    if (
        direct_or_prime
        and layer_max <= 1
        and c2c_status == C2CStatus.confirmed
        and rate_high >= minimum_rate
        and observation.confidence >= 0.75
    ):
        lane = QualityLane.direct_prime
    elif (
        layer_max >= 2
        or c2c_status == C2CStatus.rejected
        or (rate_supplied and rate_high < minimum_rate)
        or fit_score < 50
    ):
        lane = QualityLane.low_quality
    else:
        lane = QualityLane.needs_verification
    return ProvenanceAssessment(
        canonical_key=canonical_key(observation),
        canonical_url=url,
        source_authority=authority,
        confidence=observation.confidence,
        completeness=completeness,
        quality_lane=lane,
        layer_min=layer_min,
        layer_max=layer_max,
        reasons=tuple(reasons),
    )
