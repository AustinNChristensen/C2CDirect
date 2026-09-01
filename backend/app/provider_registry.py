"""Reviewed provider targets; membership is evidence, not a claimed client relationship."""

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl

from .provenance import ProviderDefinition, ProviderType


class ProviderTarget(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,62}$")
    name: str = Field(min_length=2, max_length=120)
    provider_type: ProviderType
    channel: str
    access_status: str = Field(pattern=r"^(public|registration|required_invite|relationship_target)$")
    c2cdirect: str = Field(pattern=r"^(explicit|strong|possible|unknown)$")
    typical_layer_min: int = Field(ge=0, le=10)
    typical_layer_max: int = Field(ge=0, le=10)
    evidence_urls: list[HttpUrl] = Field(min_length=1)
    rationale: str = Field(min_length=20, max_length=500)
    enabled: bool = True

    def provider_definition(self) -> ProviderDefinition:
        authority = 78 if self.provider_type == ProviderType.prime_vendor else 68
        if self.provider_type in {ProviderType.msp_vms, ProviderType.marketplace}:
            authority = 82
        return ProviderDefinition(
            slug=self.slug,
            name=self.name,
            provider_type=self.provider_type,
            intake_method=self.channel,
            canonical_domain=None,
            terms_status="needs_review",
            baseline_authority=authority,
            typical_layer_min=self.typical_layer_min,
            typical_layer_max=self.typical_layer_max,
            direct_source_capable=self.provider_type in {ProviderType.prime_vendor, ProviderType.msp_vms},
        )


@lru_cache(maxsize=1)
def load_provider_targets() -> tuple[ProviderTarget, ...]:
    path = Path(__file__).with_name("provider_targets.json")
    return tuple(ProviderTarget.model_validate(item) for item in json.loads(path.read_text()))


def provider_target(slug: str) -> ProviderTarget:
    target = next((item for item in load_provider_targets() if item.slug == slug and item.enabled), None)
    if target is None:
        raise KeyError(slug)
    return target


def provider_target_summary() -> dict:
    targets = load_provider_targets()
    return {
        "total": len(targets),
        "enabled": sum(item.enabled for item in targets),
        "explicit_c2c": sum(item.c2cdirect == "explicit" for item in targets),
        "invitation_required": sum(item.access_status == "required_invite" for item in targets),
    }
