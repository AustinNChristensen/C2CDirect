"""Small encrypted-secret boundary for self-hosted tenant configuration."""

from cryptography.fernet import Fernet, InvalidToken
from pydantic_settings import BaseSettings, SettingsConfigDict


class SecretStoreSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    c2cdirect_config_encryption_key: str = ""


settings = SecretStoreSettings()


def _fernet() -> Fernet:
    if not settings.c2cdirect_config_encryption_key:
        raise RuntimeError("Core configuration encryption is not configured")
    return Fernet(settings.c2cdirect_config_encryption_key.encode())


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError("Stored Core credential could not be decrypted") from exc
