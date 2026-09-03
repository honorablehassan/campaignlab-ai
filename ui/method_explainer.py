from __future__ import annotations

import streamlit as st
from analytics.method_registry import get_method

PLAIN = {
    "binary_ab": ("Did the variant change conversion?", "Compare two groups on a yes/no outcome such as purchase, signup, click or churn."),
    "continuous_ab": ("Did the variant change customer value?", "Compare two groups on a numeric outcome such as revenue, AOV, time spent or score."),
    "abn": ("Which of several variants actually wins?", "Compare three or more variants while controlling the extra false-positive risk from many comparisons."),
    "bootstrap_difference": ("How shaky is this group difference?", "Repeatedly resample the observed data to estimate how uncertain a mean or median difference is."),
    "marketing_efficiency": ("Where is spend working hardest?", "Compare observed ROAS, CPA/CAC and related efficiency metrics across channels or campaigns."),
    "funnel": ("Where are people dropping out?", "Turn ordered funnel stages into conversion and drop-off rates so the biggest leak becomes obvious."),
    "cohort_retention": ("Which cohorts keep coming back?", "Track repeated customer activity over time to reveal retention and lifecycle patterns."),
    "linear_regression": ("What moves a numeric outcome?", "Estimate how a continuous outcome changes with several predictors while showing uncertainty and diagnostics."),
    "logistic_regression": ("What predicts a yes/no outcome?", "Model the probability of conversion, churn, response or purchase from a set of predictors."),
    "tree_model": ("Can nonlinear patterns predict better?", "Use a tree ensemble to capture nonlinear relationships and interactions, then rank predictive signal."),
    "did": ("Did the rollout change the outcome?", "Compare the before/after change in a treated group with the change in an untreated comparison group."),
    "event_study": ("When did the effect show up?", "Trace estimated effects before and after an intervention and inspect whether pre-trends look suspicious."),
    "interrupted_time_series": ("Did the trend break at launch?", "Estimate whether the level or slope of a time series changed around a known intervention date."),
    "kmeans_segmentation": ("Are useful audience clusters hiding here?", "Group similar rows or customers across numeric features to surface descriptive segments."),
    "anomaly_detection": ("What looks weird enough to investigate?", "Flag unusually different observations so you can inspect possible data or performance anomalies."),
    "synthetic_control": ("What might have happened without the intervention?", "Build a weighted comparison from untreated units to approximate the treated unit's counterfactual path."),
    "dml": ("Can we estimate impact with lots of confounders?", "Use flexible nuisance models plus orthogonalization to estimate a treatment effect in high-dimensional observational data."),
    "causal_forest": ("Who responds differently to treatment?", "Estimate how treatment effects may vary across people or segments."),
}


def plain(method_id: str, fallback_name: str = "") -> tuple[str, str]:
    method = get_method(method_id) or {}
    return PLAIN.get(method_id, (method.get("answers", fallback_name), method.get("answers", "")))


def render_method_explainer(ranked_method: dict, *, expanded: bool = False) -> None:
    method = get_method(ranked_method["method_id"]) or {}
    question, definition = plain(ranked_method["method_id"], ranked_method.get("name", ""))
    reasons = ranked_method.get("reasons") or []
    blockers = ranked_method.get("blockers") or []
    why = reasons[0] if reasons else ("The available columns and your question are compatible with this analytical family." if ranked_method.get("eligible") else "CampaignLab considered this method because it is relevant to the business question.")
    with st.expander(f"What is {ranked_method['name']}?", expanded=expanded):
        st.markdown("**What it is**")
        st.write(definition)
        st.markdown("**What business question it answers**")
        st.write(question)
        st.markdown("**Why CampaignLab picked it here**")
        st.write(why)
        st.markdown("**What it needs**")
        st.write(method.get("requires") or ranked_method.get("requires") or "A dataset that satisfies the method's evidence contract.")
        assumptions = method.get("assumptions") or []
        if assumptions:
            st.markdown("**What needs to be reasonably true**")
            for item in assumptions[:4]:
                st.write(f"• {item}")
        caution = method.get("caution")
        if caution:
            st.markdown("**What can fool it**")
            st.write(caution)
        if blockers:
            st.markdown("**What would unlock it**")
            for item in blockers[:3]:
                st.write(f"• {item}")
