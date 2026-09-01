"""Curated, reviewable first-party job-source registry."""

import json
from importlib.resources import files

from .connectors import ConnectorTarget


def load_source_registry(*, enabled_only: bool = True) -> list[ConnectorTarget]:
    raw = json.loads(files("app").joinpath("source_targets.json").read_text())
    targets = [ConnectorTarget.model_validate(item) for item in raw]
    if enabled_only:
        targets = [target for target in targets if target.enabled]
    return sorted(targets, key=lambda target: (target.priority, target.organization_name.lower()))


def source_registry_summary() -> dict:
    targets = load_source_registry(enabled_only=False)
    return {
        "targets": len(targets),
        "enabled": sum(target.enabled for target in targets),
        "by_adapter": {
            adapter: sum(target.adapter == adapter for target in targets)
            for adapter in ("greenhouse", "lever", "ashby")
        },
        "by_priority": {
            str(priority): sum(target.priority == priority for target in targets)
            for priority in range(1, 6)
        },
    }
