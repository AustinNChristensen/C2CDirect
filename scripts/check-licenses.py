#!/usr/bin/env python3
"""Fail the release gate when locked dependencies introduce an unreviewed license."""

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from importlib.metadata import distributions
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# These expressions were reviewed for the current lockfiles. An unfamiliar expression
# intentionally fails the gate so a maintainer must assess it before extending this set.
APPROVED_NODE_LICENSES = {
    "0BSD",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "BlueOak-1.0.0",
    "CC-BY-4.0",
    "CC0-1.0",
    "ISC",
    "LGPL-3.0-or-later",
    "MIT",
    "MIT OR Apache-2.0",
    "MPL-2.0",
    "Python-2.0",
}

APPROVED_PYTHON_LICENSE_TERMS = {
    "0BSD",
    "Apache",
    "BSD",
    "CC0",
    "CNRI-Python",
    "LGPL-3.0-only",
    "MIT",
    "MPL-2.0",
    "PSF-2.0",
    "Python",
    "Zlib",
}


def node_licenses() -> Counter[str]:
    result = subprocess.run(
        ["pnpm", "licenses", "list", "--json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    inventory = json.loads(result.stdout)
    unknown = sorted(set(inventory) - APPROVED_NODE_LICENSES)
    if unknown:
        raise SystemExit(f"Unreviewed Node license expression(s): {', '.join(unknown)}")
    return Counter({license_name: len(packages) for license_name, packages in inventory.items()})


def normalized_python_license(distribution) -> str:
    metadata = distribution.metadata
    license_value = (metadata.get("License-Expression") or metadata.get("License") or "").strip()
    if license_value.startswith("MIT License\n"):
        return "MIT"
    if not license_value or license_value.upper() in {"UNKNOWN", "NONE"}:
        classifiers = metadata.get_all("Classifier") or []
        values = [
            item.removeprefix("License :: OSI Approved :: ")
            for item in classifiers
            if item.startswith("License ::")
        ]
        license_value = "; ".join(values)
    return license_value or "UNKNOWN"


def python_licenses() -> Counter[str]:
    inventory: Counter[str] = Counter()
    unreviewed: list[str] = []
    for distribution in distributions():
        name = distribution.metadata.get("Name", "unknown")
        if name.lower() == "c2cdirect-api":
            continue
        license_value = normalized_python_license(distribution)
        inventory[license_value] += 1
        terms = set(re.findall(r"[A-Za-z0-9.-]+", license_value))
        if license_value == "UNKNOWN" or not any(
            approved in license_value for approved in APPROVED_PYTHON_LICENSE_TERMS
        ):
            unreviewed.append(f"{name}=={distribution.version} ({license_value})")
        if any(term in {"GPL-2.0", "GPL-3.0", "AGPL-3.0"} for term in terms):
            unreviewed.append(f"{name}=={distribution.version} ({license_value})")
    if unreviewed:
        raise SystemExit("Unreviewed Python license(s):\n" + "\n".join(sorted(set(unreviewed))))
    return inventory


def print_inventory(label: str, inventory: Counter[str]) -> None:
    print(label)
    for license_name, count in sorted(inventory.items()):
        print(f"  {license_name}: {count}")


if __name__ == "__main__":
    print_inventory("Node dependency licenses", node_licenses())
    print_inventory("Python dependency licenses", python_licenses())
    print("License gate passed. See docs/THIRD_PARTY_LICENSES.md for the review record.")
