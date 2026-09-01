from app.provenance import ProviderType
from app.provider_registry import load_provider_targets, provider_target, provider_target_summary


def test_provider_registry_has_reviewed_c2c_and_prime_targets():
    targets = load_provider_targets()
    summary = provider_target_summary()
    assert summary["total"] >= 20
    assert summary["explicit_c2c"] >= 2
    assert any(item.provider_type == ProviderType.prime_vendor for item in targets)
    assert any(item.provider_type == ProviderType.msp_vms for item in targets)


def test_registry_relationship_target_is_not_claimed_as_verified():
    target = provider_target("dexian")
    provider = target.provider_definition()
    assert target.access_status == "relationship_target"
    assert provider.terms_status == "needs_review"
    assert provider.typical_layer_max == 1
