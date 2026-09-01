"""Terms-aware direct ATS connectors with fixed hosts and normalized observations."""

import html
import re
from abc import ABC, abstractmethod

import httpx
from pydantic import BaseModel, Field

from .models import JobPostingIn
from .provenance import JobObservation, ProviderDefinition, ProviderType


class ConnectorTarget(BaseModel):
    adapter: str = Field(pattern=r"^(greenhouse|lever|ashby)$")
    slug: str = Field(pattern=r"^[A-Za-z0-9_-]{2,80}$")
    organization_name: str = Field(min_length=2, max_length=180)
    enabled: bool = True
    tags: list[str] = Field(default_factory=list)
    priority: int = Field(default=3, ge=1, le=5)
    geographies: list[str] = Field(default_factory=lambda: ["US remote"])
    c2cdirect: str = Field(default="unknown", pattern=r"^(strong|possible|unknown|unlikely)$")
    rationale: str = Field(
        default="Manually configured direct ATS source.", min_length=12, max_length=500
    )


def _plain_text(value: str | None) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    return " ".join(html.unescape(text).split())


def _rate(compensation: dict | None) -> tuple[int | None, int | None]:
    if not compensation:
        return None, None
    interval = str(compensation.get("interval", "")).lower()
    if interval not in {"hour", "hourly", "per_hour"}:
        return None, None
    minimum = compensation.get("min")
    maximum = compensation.get("max")
    return (round(float(minimum)) if minimum is not None else None, round(float(maximum)) if maximum is not None else None)


class DirectATSConnector(ABC):
    adapter: str
    canonical_domain: str

    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    def provider_for(self, target: ConnectorTarget) -> ProviderDefinition:
        """Attribute a posting to the employer, while retaining the ATS as intake metadata."""
        safe_slug = re.sub(r"[^a-z0-9]+", "-", target.slug.lower()).strip("-")
        return ProviderDefinition(
            slug=f"employer-{self.adapter}-{safe_slug}"[:63].rstrip("-"),
            name=target.organization_name,
            provider_type=ProviderType.employer_ats,
            intake_method=f"public_api:{self.adapter}",
            canonical_domain=self.canonical_domain,
            terms_status="approved",
            baseline_authority=90,
            direct_source_capable=True,
        )

    @abstractmethod
    async def fetch(self, target: ConnectorTarget) -> list[JobObservation]: ...


class GreenhouseConnector(DirectATSConnector):
    adapter = "greenhouse"
    canonical_domain = "boards.greenhouse.io"

    async def fetch(self, target: ConnectorTarget) -> list[JobObservation]:
        provider = self.provider_for(target)
        response = await self.client.get(
            f"https://boards-api.greenhouse.io/v1/boards/{target.slug}/jobs",
            params={"content": "true"},
        )
        response.raise_for_status()
        observations = []
        for item in response.json().get("jobs", []):
            description = _plain_text(item.get("content"))
            if len(description) < 40:
                continue
            url = item.get("absolute_url")
            posting = JobPostingIn(
                source=f"greenhouse:{target.slug}",
                source_url=url,
                title=item["title"],
                company=target.organization_name,
                description=description,
                location=(item.get("location") or {}).get("name") or "Unknown",
                posted_at=item.get("updated_at"),
            )
            observations.append(
                JobObservation(
                    provider_slug=provider.slug,
                    provider_job_id=str(item["id"]),
                    requisition_id=item.get("requisition_id"),
                    posting=posting,
                    canonical_url_candidate=url,
                    end_client_name=target.organization_name,
                    parser_version="greenhouse-v1",
                    confidence=0.95,
                    evidence=[{"type": "official_posting", "url": url}],
                )
            )
        return observations


class LeverConnector(DirectATSConnector):
    adapter = "lever"
    canonical_domain = "jobs.lever.co"

    async def fetch(self, target: ConnectorTarget) -> list[JobObservation]:
        provider = self.provider_for(target)
        response = await self.client.get(
            f"https://api.lever.co/v0/postings/{target.slug}", params={"mode": "json"}
        )
        response.raise_for_status()
        observations = []
        for item in response.json():
            description = item.get("descriptionPlain") or _plain_text(item.get("description"))
            if len(description) < 40:
                continue
            rate_min, rate_max = _rate(item.get("salaryRange"))
            url = item.get("hostedUrl")
            posting = JobPostingIn(
                source=f"lever:{target.slug}",
                source_url=url,
                title=item["text"],
                company=target.organization_name,
                description=description,
                location=(item.get("categories") or {}).get("location") or "Unknown",
                rate_min=rate_min,
                rate_max=rate_max,
            )
            observations.append(
                JobObservation(
                    provider_slug=provider.slug,
                    provider_job_id=str(item["id"]),
                    requisition_id=item.get("requisitionId"),
                    posting=posting,
                    canonical_url_candidate=url,
                    end_client_name=target.organization_name,
                    engagement_type=(item.get("categories") or {}).get("commitment"),
                    parser_version="lever-v1",
                    confidence=0.95,
                    evidence=[{"type": "official_posting", "url": url}],
                )
            )
        return observations


class AshbyConnector(DirectATSConnector):
    adapter = "ashby"
    canonical_domain = "jobs.ashbyhq.com"

    async def fetch(self, target: ConnectorTarget) -> list[JobObservation]:
        provider = self.provider_for(target)
        response = await self.client.get(
            f"https://api.ashbyhq.com/posting-api/job-board/{target.slug}",
            params={"includeCompensation": "true"},
        )
        response.raise_for_status()
        observations = []
        for item in response.json().get("jobs", []):
            if not item.get("isListed", True):
                continue
            description = item.get("descriptionPlain") or _plain_text(item.get("descriptionHtml"))
            if len(description) < 40:
                continue
            compensation = item.get("compensation") or {}
            rate_min, rate_max = _rate(compensation)
            url = item.get("jobUrl") or item.get("applyUrl")
            posting = JobPostingIn(
                source=f"ashby:{target.slug}",
                source_url=url,
                title=item["title"],
                company=target.organization_name,
                description=description,
                location=item.get("location") or "Unknown",
                rate_min=rate_min,
                rate_max=rate_max,
                posted_at=item.get("publishedAt"),
            )
            observations.append(
                JobObservation(
                    provider_slug=provider.slug,
                    provider_job_id=str(item.get("id") or item.get("jobUrl")),
                    requisition_id=item.get("requisitionId"),
                    posting=posting,
                    canonical_url_candidate=url,
                    end_client_name=target.organization_name,
                    engagement_type=item.get("employmentType"),
                    parser_version="ashby-v1",
                    confidence=0.95,
                    evidence=[{"type": "official_posting", "url": url}],
                )
            )
        return observations


CONNECTORS = {
    "greenhouse": GreenhouseConnector,
    "lever": LeverConnector,
    "ashby": AshbyConnector,
}


def connector_for(target: ConnectorTarget, client: httpx.AsyncClient) -> DirectATSConnector:
    return CONNECTORS[target.adapter](client)
