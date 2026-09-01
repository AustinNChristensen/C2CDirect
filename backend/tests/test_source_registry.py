from app.source_registry import load_source_registry, source_registry_summary


def test_registry_is_unique_curated_and_sorted():
    targets = load_source_registry(enabled_only=False)
    identities = [(target.adapter, target.slug.lower()) for target in targets]

    assert len(targets) >= 20
    assert len(identities) == len(set(identities))
    assert [target.priority for target in targets] == sorted(target.priority for target in targets)
    assert all(target.rationale for target in targets)
    assert all(target.tags for target in targets)


def test_registry_summary_counts_disabled_targets():
    summary = source_registry_summary()

    assert summary["targets"] == 26
    assert summary["enabled"] == 25
    assert summary["by_adapter"] == {"greenhouse": 8, "lever": 0, "ashby": 18}
