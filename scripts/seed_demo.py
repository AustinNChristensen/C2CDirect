#!/usr/bin/env python3
"""Load the fictional public demo batch through the supported n8n ingestion contract."""

import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main() -> int:
    secret = os.environ.get("C2C_DEMO_WEBHOOK_SECRET")
    if not secret:
        print("Set C2C_DEMO_WEBHOOK_SECRET to the local N8N webhook secret.", file=sys.stderr)
        return 2
    api_url = os.environ.get("C2C_DEMO_API_URL", "http://127.0.0.1:8000").rstrip("/")
    payload = Path(__file__).resolve().parents[1].joinpath("examples/demo-jobs.json").read_bytes()
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
        print(f"Demo ingestion failed with HTTP {exc.code}.", file=sys.stderr)
        return 1
    except URLError:
        print("Demo ingestion failed because the local API is unavailable.", file=sys.stderr)
        return 1
    print(
        f"Demo ready: {result.get('persisted', 0)} persisted, "
        f"{result.get('qualified', 0)} qualified, {result.get('duplicates', 0)} duplicates."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
