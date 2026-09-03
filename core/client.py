from __future__ import annotations

import time
from typing import Any

import streamlit as st
from openai import OpenAI

from config import API_MAX_RETRIES, API_TIMEOUT_SECONDS
from core.errors import CampaignLabAPIError
from core.observability import record_event


def _feature_from_kwargs(kwargs: dict[str, Any]) -> str:
    text = kwargs.get("text") or {}
    fmt = text.get("format") if isinstance(text, dict) else None
    if isinstance(fmt, dict) and fmt.get("name"):
        return str(fmt["name"])
    instructions = str(kwargs.get("instructions") or "").lower()
    if "evidence orchestrator" in instructions:
        return "evidence_orchestrator"
    if kwargs.get("tools"):
        return "tool_orchestration"
    return "llm_call"


def _usage(response: Any) -> tuple[int, int, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return 0, 0, 0
    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    cached = 0
    details = getattr(usage, "input_tokens_details", None)
    if details is not None:
        cached = int(getattr(details, "cached_tokens", 0) or 0)
    return input_tokens, output_tokens, cached


class _ResponsesProxy:
    def __init__(self, raw_responses: Any):
        self._raw = raw_responses

    def create(self, **kwargs: Any):
        feature = _feature_from_kwargs(kwargs)
        started = time.perf_counter()
        try:
            response = self._raw.create(**kwargs)
            elapsed = (time.perf_counter() - started) * 1000
            inp, out, cached = _usage(response)
            record_event(
                kind="llm_call", feature=feature, status="ok", duration_ms=elapsed,
                model=str(kwargs.get("model") or ""), input_tokens=inp,
                cached_input_tokens=cached, output_tokens=out,
            )
            return response
        except Exception as exc:
            elapsed = (time.perf_counter() - started) * 1000
            event_id = record_event(
                kind="llm_call", feature=feature, status="error", duration_ms=elapsed,
                model=str(kwargs.get("model") or ""), detail=f"{type(exc).__name__}: {exc}",
            )
            raise CampaignLabAPIError(
                f"CampaignLab could not complete the AI request. Please retry. Reference: {event_id}"
            ) from exc


class InstrumentedOpenAI:
    """Narrow proxy used by CampaignLab so every Responses API call is observable."""
    def __init__(self, raw: OpenAI):
        self._raw = raw
        self.responses = _ResponsesProxy(raw.responses)


def get_openai_client() -> InstrumentedOpenAI:
    key = st.secrets.get("OPENAI_API_KEY")
    if not key:
        raise CampaignLabAPIError("OPENAI_API_KEY is missing from .streamlit/secrets.toml.")
    raw = OpenAI(api_key=key, timeout=API_TIMEOUT_SECONDS, max_retries=API_MAX_RETRIES)
    return InstrumentedOpenAI(raw)
