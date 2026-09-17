"""Shared progressive-disclosure UI for CampaignLab's canonical decision object."""

from __future__ import annotations

from html import escape
import json
from typing import Any

import streamlit as st

from core.decision_memory import export_memory, forget_all, forget_decision, remember_decision, update_memory_outcome
from core.auth import current_identity
from core.decision_repository import SQLiteDecisionRepository
from core.outcome_learning import calibration_summary, observe_outcome


def _restore_persistent_memory() -> None:
    identity = current_identity()
    if not identity.authenticated:
        return
    marker = f"decision_memory_loaded:{identity.user_id}"
    if st.session_state.get("decision_memory_owner") == marker:
        return
    try:
        repository = SQLiteDecisionRepository()
        st.session_state["decision_memory"] = repository.list(identity.user_id)
        st.session_state["outcome_observations"] = repository.list_observations(identity.user_id)
        st.session_state["decision_memory_owner"] = marker
    except Exception as exc:
        st.warning(f"Persistent Decision Memory is temporarily unavailable. Session memory still works. ({exc})")


def _bullets(items: list[str], empty: str = "None recorded.") -> None:
    if not items:
        st.caption(empty)
        return
    for item in items:
        st.markdown(f"- {item}")


def render_decision_record(decision: dict[str, Any], *, key: str) -> None:
    """Show the call first, with evidence and machinery behind disclosure."""
    confidence = decision["confidence"]
    disposition = decision["disposition"].replace("_", " ").title()
    source = str(decision.get("source") or "CampaignLab")
    if source == "Marketing Mix Model":
        tone, eyebrow, title = "mmm", "ALLOCATION VERDICT", "Where the budget should move"
    elif source == "Evidence Lab":
        tone, eyebrow, title = "evidence", "EVIDENCE VERDICT", "What the evidence supports"
    else:
        tone, eyebrow, title = "default", "DECISION BRIEF", "CampaignLab's call"
    evidence_move = (
        "Worth testing"
        if decision["value_of_information"]["worth_resolving"]
        else "Act on current evidence"
    )
    st.markdown(
        f'''<section class="cl-decision-brief {tone}">
          <div class="cl-decision-eyebrow"><span>{escape(eyebrow)}</span><small>{escape(source)}</small></div>
          <h2>{escape(title)}</h2>
          <p class="cl-decision-call">{escape(str(decision["call"]))}</p>
          <div class="cl-decision-scorecard">
            <div><small>CONFIDENCE</small><b>{escape(str(confidence["label"]))}</b></div>
            <div><small>POSTURE</small><b>{escape(disposition)}</b></div>
            <div><small>EVIDENCE MOVE</small><b>{escape(evidence_move)}</b></div>
          </div>
          <div class="cl-decision-next"><small>DO THIS NEXT</small><p>{escape(str(decision["next_action"]))}</p></div>
        </section>''',
        unsafe_allow_html=True,
    )
    st.caption(f"Why confidence is {confidence['label'].lower()}: {confidence['basis']}")

    with st.expander("Why CampaignLab believes this"):
        st.markdown("**Supporting evidence**")
        if decision["supporting_evidence"]:
            for item in decision["supporting_evidence"]:
                st.markdown(f"- {item['statement']}")
                st.caption(f"{item['source']} · {item['kind'].replace('_', ' ')} · {item['strength']} support")
        else:
            st.caption("No direct supporting evidence was recorded.")
        st.markdown("**Contradicting evidence or challenge**")
        if decision["contradicting_evidence"]:
            for item in decision["contradicting_evidence"]:
                st.markdown(f"- {item['statement']}")
                st.caption(f"{item['source']} · {item['kind'].replace('_', ' ')} · {item['strength']} challenge")
        else:
            st.caption("No material contradiction was recorded.")
        st.markdown("**Confidence basis**")
        st.write(confidence["basis"])

    with st.expander("What could change the decision"):
        st.markdown("**Critical uncertainty**")
        _bullets(decision["critical_uncertainties"])
        st.markdown("**Flip conditions**")
        _bullets(decision["flip_conditions"], "No explicit flip condition has been established yet.")
        st.markdown("**Is more evidence worth waiting for?**")
        st.write(decision["value_of_information"]["reason"])
        st.markdown("**Smallest useful check**")
        st.write(decision["value_of_information"]["smallest_next_check"])

    with st.expander("Assumptions, alternatives, and provenance"):
        st.markdown("**Assumptions**")
        _bullets(decision["assumptions"])
        st.markdown("**Alternatives considered**")
        _bullets(decision["alternatives_considered"])
        st.markdown("**How this was produced**")
        st.write("Deterministic computation was used." if decision["provenance"]["deterministic"] else "AI reasoning was used under a structured decision contract.")
        _bullets(decision["provenance"]["methods"])
        if decision["provenance"]["warnings"]:
            st.markdown("**Guardrails**")
            _bullets(decision["provenance"]["warnings"])

    save_col, export_col = st.columns(2)
    if save_col.button("Remember this decision", key=f"remember_{key}", width="stretch"):
        remember_decision(st.session_state, decision)
        identity = current_identity()
        if identity.authenticated:
            try:
                SQLiteDecisionRepository().save(identity.user_id, decision)
                st.success("Saved to your Decision Memory.")
            except Exception as exc:
                st.warning(f"Saved for this session, but persistent memory is unavailable. ({exc})")
        else:
            st.success("Saved to this CampaignLab session. Sign in to keep decisions across sessions.")
    export_col.download_button(
        "Download decision · JSON",
        data=json.dumps(decision, indent=2, ensure_ascii=False).encode("utf-8"),
        file_name=f"{decision['decision_id']}.json",
        mime="application/json",
        key=f"download_{key}",
        width="stretch",
    )


def render_decision_memory() -> None:
    _restore_persistent_memory()
    records = st.session_state.get("decision_memory") or []
    if not records:
        return
    st.divider()
    st.markdown("### Decision memory")
    st.caption("A lightweight session record for the current Beta. Download it before ending the session if you want to keep it.")
    st.download_button(
        "Download all remembered decisions",
        data=export_memory(st.session_state),
        file_name="CampaignLab_Decision_Memory.json",
        mime="application/json",
        key="download_decision_memory",
    )
    for index, record in enumerate(records):
        with st.expander(f"{record['source']} · {record['call'][:90]}"):
            st.caption(f"{record['created_at']} · {record['confidence']['label']} confidence")
            prediction = record.get("prediction") or {}
            if prediction.get("point") is not None:
                st.caption(
                    f"Prediction: {float(prediction['point']):+.4g} {prediction.get('unit', '')} "
                    f"for {prediction.get('metric') or 'the tracked outcome'}"
                )
            status = st.selectbox(
                "What happened next?",
                ["planned", "acted", "observed", "not_tracked"],
                index=["planned", "acted", "observed", "not_tracked"].index(record.get("outcome_status", "not_tracked")),
                key=f"memory_status_{record['decision_id']}_{index}",
            )
            actual = st.text_area(
                "Actual outcome or learning",
                value=record.get("actual_outcome", ""),
                key=f"memory_actual_{record['decision_id']}_{index}",
            )
            measured = st.text_input(
                "Actual measured change · optional",
                placeholder="Example: 0.04 for a 4% proportional change",
                key=f"memory_measured_{record['decision_id']}_{index}",
                help="Use the same units shown in the prediction. CampaignLab will compare prediction with reality without changing the historical decision.",
            )
            if st.button("Update learning", key=f"memory_update_{record['decision_id']}_{index}"):
                update_memory_outcome(st.session_state, record["decision_id"], status=status, actual_outcome=actual)
                identity = current_identity()
                observation = None
                if measured.strip():
                    try:
                        observation = observe_outcome(record, actual_value=float(measured), notes=actual)
                        prior = [x for x in (st.session_state.get("outcome_observations") or []) if not (
                            x.get("decision_id") == observation["decision_id"] and x.get("observed_at") == observation["observed_at"]
                        )]
                        st.session_state["outcome_observations"] = [observation] + prior
                    except ValueError:
                        st.error("Actual measured change must be a number, such as 0.04 for a 4% proportional change.")
                        observation = None
                if identity.authenticated:
                    try:
                        repository = SQLiteDecisionRepository()
                        repository.update_outcome(
                            identity.user_id,
                            record["decision_id"],
                            status=status,
                            actual_outcome=actual,
                        )
                        if observation:
                            repository.save_observation(identity.user_id, observation)
                        st.success("Decision Memory updated.")
                    except Exception as exc:
                        st.warning(f"Session memory updated, but persistent memory is unavailable. ({exc})")
                else:
                    st.success("Session Decision Memory updated.")
                if observation:
                    st.info(observation["score"]["label"])
            if st.button("Delete this decision", key=f"memory_delete_{record['decision_id']}_{index}"):
                forget_decision(st.session_state, record["decision_id"])
                identity = current_identity()
                if identity.authenticated:
                    try:
                        SQLiteDecisionRepository().delete(identity.user_id, record["decision_id"])
                    except Exception as exc:
                        st.warning(f"Removed from this session, but persistent deletion could not be confirmed. ({exc})")
                        return
                st.success("Decision and its recorded outcomes deleted.")
                st.rerun()

    observations = st.session_state.get("outcome_observations") or []
    if observations:
        summary = calibration_summary(observations)
        st.markdown("### Reality check")
        st.caption(summary["warning"])
        c1, c2, c3 = st.columns(3)
        c1.metric("Observed decisions", str(summary["observations"]))
        c2.metric(
            "Direction accuracy",
            "Not scorable" if summary["direction_accuracy"] is None else f"{summary['direction_accuracy']:.0%}",
        )
        c3.metric(
            "Mean absolute error",
            "Not scorable" if summary["mean_absolute_error"] is None else f"{summary['mean_absolute_error']:.4g}",
        )

    with st.expander("Privacy and deletion"):
        st.caption("Download your memory before deleting it if you want a copy. Deletion removes decisions and their recorded outcomes for the current account or session.")
        confirm = st.checkbox("I understand this deletes all Decision Memory", key="confirm_delete_all_memory")
        if st.button("Delete all Decision Memory", disabled=not confirm, key="delete_all_memory"):
            identity = current_identity()
            if identity.authenticated:
                try:
                    SQLiteDecisionRepository().delete_all(identity.user_id)
                except Exception as exc:
                    st.error(f"CampaignLab could not confirm persistent deletion. Nothing was removed from the visible session. ({exc})")
                    return
            forget_all(st.session_state)
            st.success("All Decision Memory and recorded outcomes were deleted.")
            st.rerun()
