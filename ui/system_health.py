from __future__ import annotations

import pandas as pd
import streamlit as st

from core.observability import recent_events, telemetry_summary
from analytics.method_registry import live_methods


def render_system_health() -> None:
    st.header("⚙️ System Health")
    st.write("Local runtime observability for this CampaignLab session. No raw uploaded dataset rows are written to telemetry.")
    summary = telemetry_summary()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("LLM calls", f"{summary["llm_calls"]:,}")
    c2.metric("Tool calls", f"{summary["tool_calls"]:,}")
    c3.metric("Errors", f"{summary["errors"]:,}")
    c4.metric("Est. API cost", f"${summary['estimated_cost_usd']:.5f}")
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Input tokens", f"{summary['input_tokens']:,}")
    c6.metric("Output tokens", f"{summary['output_tokens']:,}")
    c7.metric("Avg LLM latency", f"{summary['avg_llm_latency_ms']:.0f} ms")
    c8.metric("Live analytic engines", f"{len(live_methods()):,}")
    st.caption("Health telemetry records runtime metadata and compact errors only; raw uploaded dataset rows are not logged here.")

    events = recent_events(100)
    if not events:
        st.info("No runtime events yet. Use Strategy or Evidence Lab and telemetry will appear here.")
        return
    st.subheader("Recent runtime events")
    cols = ["timestamp_utc", "kind", "feature", "status", "duration_ms", "total_tokens", "estimated_cost_usd", "event_id"]
    frame = pd.DataFrame(events)
    keep = [c for c in cols if c in frame.columns]
    st.dataframe(frame[keep].iloc[::-1], use_container_width=True, hide_index=True)
    with st.expander("Error details"):
        errors = [e for e in events if e.get("status") != "ok"]
        if not errors:
            st.write("No errors recorded in this session.")
        for event in reversed(errors[-20:]):
            st.markdown(f"**{event['event_id']} · {event['feature']}**")
            st.code(event.get("detail") or "No detail captured.", language="text")
