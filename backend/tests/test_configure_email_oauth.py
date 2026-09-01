import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "scripts" / "configure-email-oauth.py"
SPEC = importlib.util.spec_from_file_location("configure_email_oauth", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_client_id_validation_rejects_empty_or_shell_split_values():
    assert MODULE.valid_client_id("valid-client-id-123")
    assert not MODULE.valid_client_id("")
    assert not MODULE.valid_client_id("client id with spaces")


def test_setting_replacement_does_not_duplicate_key():
    updated = MODULE.replace_setting("GMAIL_OAUTH_CLIENT_ID=old\nOTHER=value\n", "GMAIL_OAUTH_CLIENT_ID", "new")

    assert updated == "GMAIL_OAUTH_CLIENT_ID=new\nOTHER=value\n"
