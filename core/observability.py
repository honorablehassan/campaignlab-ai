from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import logging
import time
import uuid
from typing import Any

from config import MODEL_INPUT_COST_PER_MILLION, MODEL_OUTPUT_COST_PER_MILLION, MODEL_CACHED_INPUT_COST_PER_MILLION

logger = logging.getLogger("campaignlab")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

_FALLBACK_EVENTS: list[dict[str, Any]] = []
_MAX_EVENTS = 250


@dataclass
class TelemetryEvent:
    event_id: str
    timestamp_utc: str
    kind: str
    feature: str
    status: str
    duration_ms: float | None = None
    model: str | None = None
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    detail: str = ""


def _store() -> list[dict[str, Any]]:
    try:
        import streamlit as st
        if "telemetry_events" not in st.session_state:
            st.session_state["telemetry_events"] = []
        return st.session_state["telemetry_events"]
    except Exception:
        return _FALLBACK_EVENTS


def estimate_cost(input_tokens: int, output_tokens: int, cached_input_tokens: int = 0) -> float:
    regular_input = max(0, input_tokens - cached_input_tokens)
    return (
        regular_input / 1_000_000 * MODEL_INPUT_COST_PER_MILLION
        + cached_input_tokens / 1_000_000 * MODEL_CACHED_INPUT_COST_PER_MILLION
        + output_tokens / 1_000_000 * MODEL_OUTPUT_COST_PER_MILLION
    )


def record_event(*, kind: str, feature: str, status: str, duration_ms: float | None = None,
                 model: str | None = None, input_tokens: int = 0, cached_input_tokens: int = 0,
                 output_tokens: int = 0, detail: str = "") -> str:
    event = TelemetryEvent(
        event_id=uuid.uuid4().hex[:12],
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        kind=kind,
        feature=feature,
        status=status,
        duration_ms=duration_ms,
        model=model,
        input_tokens=int(input_tokens or 0),
        cached_input_tokens=int(cached_input_tokens or 0),
        output_tokens=int(output_tokens or 0),
        total_tokens=int(input_tokens or 0) + int(output_tokens or 0),
        estimated_cost_usd=estimate_cost(int(input_tokens or 0), int(output_tokens or 0), int(cached_input_tokens or 0)),
        detail=(detail or "")[:800],
    )
    payload = asdict(event)
    store = _store()
    store.append(payload)
    del store[:-_MAX_EVENTS]
    log = logger.info if status == "ok" else logger.error
    log("event=%s kind=%s feature=%s status=%s duration_ms=%s tokens=%s cost=%.8f detail=%s",
        event.event_id, kind, feature, status, duration_ms, event.total_tokens, event.estimated_cost_usd, event.detail)
    return event.event_id


def recent_events(limit: int = 100) -> list[dict[str, Any]]:
    return list(_store())[-max(1, limit):]


def telemetry_summary() -> dict[str, Any]:
    events = recent_events(250)
    api = [e for e in events if e.get("kind") == "llm_call"]
    tools = [e for e in events if e.get("kind") == "tool_call"]
    errors = [e for e in events if e.get("status") != "ok"]
    return {
        "llm_calls": len(api),
        "tool_calls": len(tools),
        "errors": len(errors),
        "input_tokens": sum(e.get("input_tokens", 0) for e in api),
        "cached_input_tokens": sum(e.get("cached_input_tokens", 0) for e in api),
        "output_tokens": sum(e.get("output_tokens", 0) for e in api),
        "estimated_cost_usd": sum(e.get("estimated_cost_usd", 0.0) for e in api),
        "avg_llm_latency_ms": (sum(e.get("duration_ms") or 0 for e in api) / len(api)) if api else 0.0,
    }
