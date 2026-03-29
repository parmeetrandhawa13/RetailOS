from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass
from typing import Any


VALID_ROLES = {"admin", "analyst", "viewer"}


@dataclass(frozen=True)
class AuthUser:
    username: str
    name: str
    role: str
    password_hash: str | None
    password_plain: str | None
    auth_source: str = "local"
    email: str | None = None


@dataclass(frozen=True)
class AccessConfig:
    users: dict[str, AuthUser]
    google_roles: dict[str, str]


def _pbkdf2_sha256(password: str, salt: str, iterations: int) -> str:
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return base64.b64encode(derived).decode("utf-8")


def _normalize_role(role: object) -> str:
    normalized = str(role or "viewer").strip().lower()
    return normalized if normalized in VALID_ROLES else "viewer"


def _safe_get(mapping: Any, key: str, default: Any = None) -> Any:
    try:
        if hasattr(mapping, "get"):
            return mapping.get(key, default)
    except Exception:
        return default
    return default


def _extract_auth_block(secrets: Any | None) -> dict[str, Any]:
    if secrets is None:
        return {}
    return _safe_get(secrets, "auth", {}) or {}


def _extract_access_block(secrets: Any | None) -> dict[str, Any]:
    if secrets is None:
        return {}
    return _safe_get(secrets, "access", {}) or {}


def _build_user(record: dict[str, Any]) -> AuthUser | None:
    username = str(record.get("username", "")).strip()
    if not username:
        return None

    password_hash = record.get("password_hash")
    password_plain = record.get("password")
    if not password_hash and not password_plain:
        return None

    name = str(record.get("name") or username).strip()
    email = record.get("email")
    return AuthUser(
        username=username,
        name=name,
        role=_normalize_role(record.get("role", "viewer")),
        password_hash=str(password_hash) if password_hash else None,
        password_plain=str(password_plain) if password_plain else None,
        auth_source="local",
        email=str(email).strip() if email else None,
    )


def _load_users_from_block(block: dict[str, Any]) -> dict[str, AuthUser]:
    users: dict[str, AuthUser] = {}
    raw_users = block.get("users", [])
    if isinstance(raw_users, list):
        for candidate in raw_users:
            if isinstance(candidate, dict):
                user = _build_user(candidate)
                if user:
                    users[user.username] = user
    return users


def _load_legacy_user(auth_block: dict[str, Any]) -> AuthUser | None:
    return _build_user(
        {
            "username": auth_block.get("username"),
            "name": auth_block.get("name") or auth_block.get("username"),
            "role": auth_block.get("role", "admin"),
            "password": auth_block.get("password"),
            "password_hash": auth_block.get("password_hash"),
            "email": auth_block.get("email"),
        }
    )


def _load_user_from_environment() -> AuthUser | None:
    username = os.getenv("RETAILOS_AUTH_USERNAME", "").strip()
    if not username:
        return None

    password_hash = os.getenv("RETAILOS_AUTH_PASSWORD_HASH")
    password_plain = os.getenv("RETAILOS_AUTH_PASSWORD")
    if not password_hash and not password_plain:
        return None

    return AuthUser(
        username=username,
        name=os.getenv("RETAILOS_AUTH_NAME", username).strip(),
        role=_normalize_role(os.getenv("RETAILOS_AUTH_ROLE", "admin")),
        password_hash=password_hash,
        password_plain=password_plain,
        auth_source="local",
        email=os.getenv("RETAILOS_AUTH_EMAIL"),
    )


def _normalize_email_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    if value:
        return [str(value).strip().lower()]
    return []


def _load_google_roles(access_block: dict[str, Any], auth_block: dict[str, Any]) -> dict[str, str]:
    google_roles: dict[str, str] = {}

    google_access = access_block.get("google_roles", {})
    if isinstance(google_access, dict):
        for role_key, emails in google_access.items():
            normalized_role = _normalize_role(role_key)
            for email in _normalize_email_list(emails):
                google_roles[email] = normalized_role

    google_auth = auth_block.get("google_roles", {})
    if isinstance(google_auth, dict):
        for role_key, emails in google_auth.items():
            normalized_role = _normalize_role(role_key)
            for email in _normalize_email_list(emails):
                google_roles[email] = normalized_role

    for role_name in VALID_ROLES:
        env_value = os.getenv(f"RETAILOS_GOOGLE_{role_name.upper()}_EMAILS", "")
        if env_value:
            for email in [item.strip().lower() for item in env_value.split(",") if item.strip()]:
                google_roles[email] = role_name

    return google_roles


def load_access_config(secrets: Any | None) -> AccessConfig | None:
    auth_block = _extract_auth_block(secrets)
    access_block = _extract_access_block(secrets)

    users = _load_users_from_block(access_block)
    if not users:
        users = _load_users_from_block(auth_block)

    if not users:
        legacy_user = _load_legacy_user(auth_block)
        if legacy_user:
            users[legacy_user.username] = legacy_user

    env_user = _load_user_from_environment()
    if env_user:
        users[env_user.username] = env_user

    google_roles = _load_google_roles(access_block, auth_block)

    if not users and not google_roles:
        return None
    return AccessConfig(users=users, google_roles=google_roles)


def verify_password(password: str, user: AuthUser) -> bool:
    if user.password_hash:
        try:
            algorithm, iteration_text, salt, encoded_hash = user.password_hash.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            calculated = _pbkdf2_sha256(password, salt, int(iteration_text))
            return hmac.compare_digest(calculated, encoded_hash)
        except (TypeError, ValueError):
            return False

    if user.password_plain is None:
        return False

    return hmac.compare_digest(password, user.password_plain)


def authenticate_local_user(username: str, password: str, config: AccessConfig | None) -> AuthUser | None:
    if config is None:
        return None
    candidate = config.users.get(username)
    if candidate is None:
        return None
    if not verify_password(password, candidate):
        return None
    return candidate


def google_auth_available(secrets: Any | None) -> bool:
    auth_block = _extract_auth_block(secrets)
    google_block = auth_block.get("google")
    return isinstance(google_block, dict) and bool(google_block.get("client_id"))


def build_google_user(user_info: Any, config: AccessConfig | None) -> AuthUser | None:
    if user_info is None:
        return None

    email = str(getattr(user_info, "email", "") or user_info.get("email", "")).strip().lower()
    if not email:
        return None

    name = str(
        getattr(user_info, "name", "")
        or user_info.get("name", "")
        or getattr(user_info, "preferred_name", "")
        or user_info.get("preferred_name", "")
        or email.split("@")[0]
    ).strip()
    role = "viewer"
    if config and email in config.google_roles:
        role = config.google_roles[email]

    return AuthUser(
        username=email,
        name=name,
        role=role,
        password_hash=None,
        password_plain=None,
        auth_source="google",
        email=email,
    )
