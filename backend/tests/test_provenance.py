from app.models import C2CStatus
from app.provenance import (
    JobObservation,
    ProviderDefinition,
    ProviderType,
    QualityLane,
    assess_provenance,
    canonical_key,
    normalized_url,
)
from tests.factories import make_posting


def provider(kind=ProviderType.employer_ats, layers=(0, 0), authority=90):
    return ProviderDefinition(
        slug="greenhouse",
        name="Greenhouse",
        provider_type=kind,
        intake_method="public_api",
        canonical_domain="boards.greenhouse.io",
        terms_status="approved",
        baseline_authority=authority,
        typical_layer_min=layers[0],
        typical_layer_max=layers[1],
        direct_source_capable=True,
    )


def observation(**changes):
    values = {
        "provider_slug": "greenhouse",
        "provider_job_id": "123",
        "requisition_id": "REQ-42",
        "posting": make_posting(source_url="https://boards.greenhouse.io/acme/jobs/123?gh_src=x"),
        "canonical_url_candidate": "https://boards.greenhouse.io/acme/jobs/123?gh_src=x",
        "end_client_name": "Acme",
        "engagement_type": "c2c_contract",
        "parser_version": "greenhouse-v1",
        "confidence": 0.95,
    }
    values.update(changes)
    return JobObservation(**values)


def test_canonical_key_uses_end_client_and_requisition_across_sources():
    first = observation(provider_slug="greenhouse")
    second = observation(provider_slug="email", canonical_url_candidate=None)
    assert canonical_key(first) == canonical_key(second)


def test_url_normalization_removes_tracking_and_fragments():
    assert normalized_url("http://boards.greenhouse.io/acme/jobs/123?gh_src=x#apply") == (
        "https://boards.greenhouse.io/acme/jobs/123"
    )


def test_direct_confirmed_high_rate_job_reaches_direct_prime_lane():
    result = assess_provenance(provider(), observation(), C2CStatus.confirmed, 90, 130)
    assert result.quality_lane == QualityLane.direct_prime
    assert result.source_authority == 95
    assert result.completeness == 1


def test_multilayer_provider_is_low_quality_even_with_good_role_fit():
    result = assess_provenance(
        provider(ProviderType.staffing_vendor, layers=(2, 4), authority=35),
        observation(end_client_name=None),
        C2CStatus.confirmed,
        95,
        130,
    )
    assert result.quality_lane == QualityLane.low_quality
    assert "multiple_vendor_layers" in result.reasons


def test_employer_posting_does_not_imply_c2c_confirmation():
    result = assess_provenance(
        provider(),
        observation(posting=make_posting(rate_min=None, rate_max=None)),
        C2CStatus.unknown,
        90,
        130,
    )
    assert result.quality_lane == QualityLane.needs_verification
    assert "rate_unknown" in result.reasons
