"""Outbound endpoint validation for hosted multi-tenant deployments."""

from ipaddress import ip_address
from urllib.parse import urlparse

BLOCKED_HOSTS = {
    "localhost",
    "host.docker.internal",
    "metadata.google.internal",
    "searxng",
}


def validate_outbound_url(url: str, *, allow_private: bool) -> None:
    if not url:
        return
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not host:
        raise ValueError("Endpoint must be an HTTP or HTTPS URL")
    if parsed.username or parsed.password:
        raise ValueError("Endpoint URLs cannot contain credentials")
    if allow_private:
        return
    if host in BLOCKED_HOSTS or host.endswith((".local", ".internal", ".localhost")):
        raise ValueError("Private network endpoints are disabled in hosted mode")
    try:
        address = ip_address(host)
    except ValueError:
        return
    if not address.is_global:
        raise ValueError("Private network endpoints are disabled in hosted mode")
