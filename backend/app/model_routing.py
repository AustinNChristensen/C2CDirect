from dataclasses import dataclass


@dataclass(frozen=True)
class ModelTarget:
    provider: str
    model: str
    tier: str
    reason: str


PROVIDER_MODELS = {
    "openai": {"economy": "gpt-4.1-mini", "standard": "gpt-4.1", "premium": "o3"},
    "anthropic": {
        "economy": "claude-3-5-haiku-latest",
        "standard": "claude-sonnet-4-20250514",
        "premium": "claude-opus-4-20250514",
    },
}


def select_model(
    complexity: int,
    available_providers: tuple[str, ...] = ("openai",),
    sensitive_data: bool = False,
) -> ModelTarget:
    tier = "economy" if complexity < 35 else "standard" if complexity < 80 else "premium"
    provider = next((name for name in available_providers if name in PROVIDER_MODELS), None)
    if provider is None:
        return ModelTarget("deterministic", "local-rules", tier, "no_provider_configured")
    if sensitive_data:
        return ModelTarget("deterministic", "local-rules", tier, "sensitive_data_local_only")
    return ModelTarget(provider, PROVIDER_MODELS[provider][tier], tier, "complexity_routed")
