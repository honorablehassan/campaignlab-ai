from __future__ import annotations

import traceback
from typing import Callable, Any

import streamlit as st

from core.errors import CampaignLabError
from core.observability import record_event


def render_with_error_boundary(feature: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    try:
        fn(*args, **kwargs)
    except CampaignLabError as exc:
        st.error(str(exc))
        st.caption("Your current inputs are preserved. Retry when ready.")
    except Exception as exc:
        event_id = record_event(
            kind="ui_error",
            feature=feature,
            status="error",
            detail=f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=6)}",
        )
        st.error(f"CampaignLab hit an unexpected error. Your inputs are preserved. Reference: {event_id}")
        st.caption("The failure was recorded for debugging instead of exposing a raw stack trace in the product UI.")
