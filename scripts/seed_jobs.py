#!/usr/bin/env python3
"""Load a reviewed job batch through the supported n8n ingestion contract."""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path, help="Path to an n8n-compatible job batch JSON file")
    args = parser.parse_args()
    secret = os.environ.get("C2C_WEBHOOK_SECRET") or os.environ.get("C2C_DEMO_WEBHOOK_SECRET")
    if not secret:
        print("Set C2C_WEBHOOK_SECRET to the local n8n webhook secret.", file=sys.stderr)
        return 2
    api_url = os.environ.get("C2C_API_URL", "http://127.0.0.1:8000").rstrip("/")
    try:
        payload = args.batch.expanduser().resolve(strict=True).read_bytes()
        decoded = json.loads(payload)
        if not decoded.get("run_id") or not decoded.get("jobs"):
            raise ValueError("batch must contain run_id and a non-empty jobs array")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Invalid job batch: {exc}", file=sys.stderr)
        return 2
    request = Request(
        f"{api_url}/v1/ingest/n8n",
        data=payload,
        headers={"content-type": "application/json", "x-webhook-secret": secret},
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            result = json.load(response)
    except HTTPError as exc:
        print(f"Job ingestion failed with HTTP {exc.code}.", file=sys.stderr)
        return 1
    except URLError:
        print("Job ingestion failed because the local API is unavailable.", file=sys.stderr)
        return 1
    print(
        f"Seed complete: {result.get('persisted', 0)} persisted, "
        f"{result.get('qualified', 0)} qualified, {result.get('duplicates', 0)} duplicates."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
