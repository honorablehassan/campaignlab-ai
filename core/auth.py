"""Optional Streamlit OIDC identity boundary."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping

import streamlit as st


@dataclass(frozen=True)
class UserIdentity:
    user_id: str
    display_name: str
    email: str
    authenticated: bool


ANONYMOUS = UserIdentity("session", "Local session", "", False)


def identity_from_claims(claims: Mapping[str, Any] | None) -> UserIdentity:
    claims = claims or {}
    logged_in = bool(claims.get("is_logged_in"))
    if not logged_in:
        return ANONYMOUS
    subject = str(claims.get("sub") or "").strip()
    email = str(claims.get("email") or "").strip().lower()
    if not subject and not email:
        return ANONYMOUS
    stable = subject or hashlib.sha256(email.encode("utf-8")).hexdigest()
    name = str(claims.get("name") or email or "CampaignLab user").strip()
    return UserIdentity(f"oidc:{stable}", name, email, True)


def auth_configured() -> bool:
    try:
        auth = st.secrets.get("auth")
    except (FileNotFoundError, KeyError):
        return False
    return bool(auth)


def current_identity() -> UserIdentity:
    if not auth_configured():
        return ANONYMOUS
    try:
        return identity_from_claims(dict(st.user))
    except (AttributeError, TypeError, KeyError):
        return ANONYMOUS
