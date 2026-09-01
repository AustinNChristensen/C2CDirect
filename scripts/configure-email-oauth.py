#!/usr/bin/env python3
"""Safely write a public mailbox OAuth client ID to the private local environment."""

import argparse
import getpass
import os
import re
import tempfile
from pathlib import Path


PROVIDERS = {
    "gmail": ("GMAIL_OAUTH_CLIENT_ID", "gmail"),
    "microsoft": ("MICROSOFT_OAUTH_CLIENT_ID", "microsoft"),
}


def valid_client_id(value: str) -> bool:
    return 10 <= len(value) <= 512 and not re.search(r"\s", value)


def replace_setting(contents: str, name: str, value: str) -> str:
    replacement = f"{name}={value}"
    pattern = re.compile(rf"^{re.escape(name)}=.*$", re.MULTILINE)
    if pattern.search(contents):
        return pattern.sub(replacement, contents)
    return contents.rstrip() + f"\n{replacement}\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Configure a local read-only Gmail or Microsoft OAuth client without echoing it."
    )
    parser.add_argument("provider", choices=sorted(PROVIDERS))
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "deploy" / "core" / ".env",
        help="Path to the private Core environment file",
    )
    args = parser.parse_args()
    if not args.env_file.is_file():
        raise SystemExit("Private deployment environment does not exist")

    client_id = getpass.getpass(f"Paste the {args.provider} OAuth client ID (input hidden): ").strip()
    if not valid_client_id(client_id):
        raise SystemExit("Client ID was empty or malformed; no file was changed")

    name, callback_name = PROVIDERS[args.provider]
    original = args.env_file.read_text()
    updated = replace_setting(original, name, client_id)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{args.env_file.name}.", dir=args.env_file.parent
    )
    try:
        with os.fdopen(descriptor, "w") as temporary:
            temporary.write(updated)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, args.env_file)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)

    print("OAuth client configured without displaying or committing it.")
    print(
        "Registered callback must be: "
        f"http://127.0.0.1:8080/api/v1/email/oauth/{callback_name}/callback"
    )
    print("Restart the API service, then use Workspace → Connect mailbox.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
