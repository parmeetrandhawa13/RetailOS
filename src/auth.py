from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AuthConfig:
    username: str
    password_hash: str | None
    password_plain: str | None


def _extract_auth_block(secrets: Any | None) -> dict[str, Any]:
    auth_block = {}
    if secrets is None:
        return auth_block

    try:
        if hasattr(secrets, "get"):
            auth_block = secrets.get("auth", {}) or {}
    except Exception:
        return {}
    return auth_block


def load_auth_config(secrets: Any | None) -> AuthConfig | None:
    auth_block = _extract_auth_block(secrets)

    username = (
        auth_block.get("username")
        or os.getenv("RETAILOS_AUTH_USERNAME")
    )
    password_hash = (
        auth_block.get("password_hash")
        or os.getenv("RETAILOS_AUTH_PASSWORD_HASH")
    )
    password_plain = (
        auth_block.get("password")
        or os.getenv("RETAILOS_AUTH_PASSWORD")
    )

    if not username or not (password_hash or password_plain):
        return None

    return AuthConfig(
        username=str(username),
        password_hash=str(password_hash) if password_hash else None,
        password_plain=str(password_plain) if password_plain else None,
    )


def _pbkdf2_sha256(password: str, salt: str, iterations: int) -> str:
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return base64.b64encode(derived).decode("utf-8")


def verify_password(password: str, config: AuthConfig) -> bool:
    if config.password_hash:
        try:
            algorithm, iteration_text, salt, encoded_hash = config.password_hash.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            calculated = _pbkdf2_sha256(password, salt, int(iteration_text))
            return hmac.compare_digest(calculated, encoded_hash)
        except (TypeError, ValueError):
            return False

    if config.password_plain is None:
        return False

    return hmac.compare_digest(password, config.password_plain)


def verify_credentials(username: str, password: str, config: AuthConfig | None) -> bool:
    if config is None:
        return False
    return hmac.compare_digest(username, config.username) and verify_password(password, config)
