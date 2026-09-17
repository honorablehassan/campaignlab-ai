"""Minimal account controls; visual wrapping belongs to the final UX pass."""

import streamlit as st

from core.auth import auth_configured, current_identity


def render_account_control() -> None:
    if not auth_configured():
        return
    identity = current_identity()
    left, right = st.columns([5, 1])
    if identity.authenticated:
        left.caption(f"Signed in as {identity.display_name}")
        right.button("Sign out", on_click=st.logout, key="account_logout", width="stretch")
    else:
        left.caption("Sign in to keep Decision Memory across sessions.")
        right.button("Sign in", on_click=st.login, key="account_login", width="stretch")
