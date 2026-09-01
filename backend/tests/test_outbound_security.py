import pytest

from app.outbound_security import validate_outbound_url


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:11434/v1",
        "http://10.0.0.8:8080",
        "http://host.docker.internal:11434/v1",
        "http://model.internal/v1",
    ],
)
def test_hosted_mode_blocks_private_model_and_search_endpoints(url):
    with pytest.raises(ValueError, match="Private network"):
        validate_outbound_url(url, allow_private=False)


def test_local_core_allows_private_endpoints_but_never_url_credentials():
    validate_outbound_url("http://host.docker.internal:11434/v1", allow_private=True)
    with pytest.raises(ValueError, match="credentials"):
        validate_outbound_url("https://user:secret@example.com/v1", allow_private=True)
