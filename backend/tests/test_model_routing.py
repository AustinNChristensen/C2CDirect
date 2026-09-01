from app.model_routing import select_model


def test_model_router_selects_tier_by_complexity():
    assert select_model(10).tier == "economy"
    assert select_model(50).tier == "standard"
    assert select_model(90).tier == "premium"


def test_model_router_falls_back_without_provider():
    result = select_model(50, available_providers=("unknown",))
    assert result.provider == "deterministic"
    assert result.reason == "no_provider_configured"


def test_sensitive_data_never_leaves_local_boundary():
    result = select_model(90, available_providers=("anthropic",), sensitive_data=True)
    assert result.model == "local-rules"
    assert result.reason == "sensitive_data_local_only"
