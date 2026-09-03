from __future__ import annotations

from analytics.directory_catalog import DECISION_FAMILIES, METHOD_PRESENTATION, LAB_SPECIALS

import io
import json
import hashlib
from pathlib import Path

import pandas as pd
import streamlit as st

from analytics.ab_binary import analyze_binary_ab, required_sample_size_per_group
from analytics.data_profile import profile_dataframe
from analytics.data_builder import understand_source
from analytics.dataset_intelligence import analyze_dataset_intelligence
from analytics.method_ranker import rank_methods
from analytics.method_registry import methods_by_family, get_method, METHODS
from analytics.tool_runtime import EvidenceToolRuntime
from engines.evidence_orchestrator import run_evidence_orchestrator
from engines.result_qa import ask_about_result
from visualization.decision_visualization import build_visualization, recommend_visualizations
from ui.copy_engine import dataset_question_placeholder, evidence_design_placeholder, evidence_outcome_placeholder
from ui.theme import kicker
from ui.brand import intelligence_label, lab_mark, utility_mark
from ui.method_explainer import plain as method_plain, render_method_explainer
from ui.reporting import build_decision_report
from visualization.interactive_charts import (group_outcome_rate as interactive_group_rate, efficiency_rank as interactive_efficiency_rank, spend_vs_revenue as interactive_spend_vs_revenue, performance_over_time as interactive_time, group_trends as interactive_group_trends, retention_heatmap as interactive_retention, media_funnel as interactive_funnel, missingness as interactive_missingness, numeric_distribution as interactive_distribution, ab_conversion_result, ab_effect_interval)
from visualization.evidence_charts import (
    conversion_rate_chart,
    effect_interval_chart,
    missingness_chart,
    sample_size_curve,
)




def _dataset_fingerprint(df: pd.DataFrame, source_name: str) -> str:
    """Stable-enough UI signature so old analyses never appear under changed evidence."""
    row_hash = pd.util.hash_pandas_object(df, index=True).values.tobytes()
    schema = "|".join(f"{c}:{df[c].dtype}" for c in df.columns).encode("utf-8")
    return hashlib.sha256(source_name.encode("utf-8") + schema + row_hash).hexdigest()


def _go_to(page: str) -> None:
    st.query_params["page"] = page
    st.rerun()

def _pct(value: float, digits: int = 2) -> str:
    return f"{value * 100:.{digits}f}%"


def _pp(value: float, digits: int = 2) -> str:
    return f"{value * 100:+.{digits}f} pp"


def _comma_int_input(label: str, value: int, key: str) -> int:
    """Integer input that keeps human-friendly thousands separators visible."""
    raw = st.text_input(label, value=f"{value:,}", key=key)
    cleaned = raw.replace(",", "").replace(" ", "").strip()
    try:
        return int(cleaned)
    except ValueError:
        st.caption(f"Enter {label.lower()} as a whole number, for example {value:,}.")
        return -1


ROLE_LABELS = {
    "id": ("Identity", "ID"), "customer": ("Customer", "Customer"), "date": ("Time", "Date"),
    "treatment": ("Experiment", "Treatment"), "binary_outcome": ("Outcome", "Yes / no"),
    "continuous_outcome": ("Outcome", "Numeric"), "spend": ("Economics", "Spend"),
    "revenue": ("Economics", "Revenue"), "channel": ("Marketing", "Channel"),
    "campaign": ("Marketing", "Campaign"), "impressions": ("Funnel", "Impressions"),
    "clicks": ("Funnel", "Clicks"), "conversions": ("Funnel", "Conversions"),
}


def _method_plain(method):
    return method_plain(method["method_id"], method.get("name", ""))


def _render_data_builder_understanding(df: pd.DataFrame, source_name: str, dataset_key: str):
    understanding = understand_source(df, source_name)
    st.markdown(
        f'<div class="cl-data-understand"><span>CAMPAIGNLAB FOUND YOUR EVIDENCE</span><b>{understanding["source_label"]}</b><p>{understanding["rows"]:,} rows · {understanding["columns"]:,} columns · {understanding["confidence"].title()} confidence</p></div>',
        unsafe_allow_html=True,
    )
    mapped = understanding.get("evidence") or []
    if mapped:
        chips = []
        for item in mapped[:10]:
            chips.append(f'<div class="cl-map-chip"><small>{item["role"].replace("_"," ").upper()}</small><b>{item["column"]}</b></div>')
        st.markdown('<div class="cl-map-grid">' + ''.join(chips) + '</div>', unsafe_allow_html=True)

    # Resolve only consequential ambiguity, and make the user's resolution a
    # first-class analytical contract rather than a decorative dropdown.
    consequential = {
        role: candidates for role, candidates in (understanding.get("ambiguous") or {}).items()
        if role in {"revenue", "spend", "date", "event", "user", "session", "conversions"}
    }
    role_overrides: dict[str, str] = {}
    unresolved: list[str] = []
    if consequential:
        st.markdown("### One thing CampaignLab won't guess")
        st.caption("I found more than one plausible field for an important analytical role. Confirm the meaning once; CampaignLab will use that same choice for readiness, method selection, charts and analysis.")
        for role, candidates in consequential.items():
            options = ["I'm not sure yet"] + list(candidates)
            choice = st.selectbox(
                f"Which field should CampaignLab use for {role.replace('_', ' ')}?",
                options,
                key=f"resolved_role_{dataset_key}_{role}",
                help="This is not just a display setting. Your choice becomes the resolved analytical mapping for this dataset.",
            )
            if choice == "I'm not sure yet":
                unresolved.append(role)
            else:
                role_overrides[role] = choice
                st.caption(f"✓ Resolved: {role.replace('_', ' ')} → {choice}")
        if unresolved:
            st.info("That's okay. CampaignLab will keep " + ", ".join(r.replace('_',' ') for r in unresolved) + " unresolved rather than silently choosing for you. Resolve it above when your question depends on it.")
        else:
            st.success("Mapping confirmed. CampaignLab will carry these choices through the analytical pipeline.")
    elif understanding.get("questions"):
        label = 'ONE THING I NEED FROM YOU' if len(understanding['questions']) == 1 else 'A FEW THINGS I NEED FROM YOU'
        st.markdown(f'<div class="cl-data-question"><span>{label}</span><b>These choices could change the analysis, so CampaignLab will not guess.</b></div>', unsafe_allow_html=True)
        for q in understanding["questions"][:3]:
            st.warning(q)

    if understanding.get("safe_actions"):
        with st.expander("What CampaignLab can safely do with this evidence", expanded=False):
            for action in understanding["safe_actions"]:
                st.write(f"✓ {action}")
            for caution in understanding.get("cautions") or []:
                st.write(f"⚠ {caution}")
            st.caption(understanding["philosophy"])
    analytical_mapping = dict(role_overrides)
    for role in unresolved:
        analytical_mapping[role] = None
    return understanding, analytical_mapping, unresolved


def _render_role_chips(role_map):
    chips=[]
    for role,(eyebrow,label) in ROLE_LABELS.items():
        cols=role_map.get(role) or []
        if cols:
            chips.append(f'<div class="cl-role-chip"><div class="cl-role-name">{eyebrow}</div><div class="cl-role-value">{label} · {cols[0]}</div></div>')
    if chips:
        st.markdown('<div class="cl-role-grid">'+''.join(chips[:10])+'</div>',unsafe_allow_html=True)


def _render_method_cards(ranked):
    plausible=[m for m in ranked if m["eligible"]]
    ready=[m for m in plausible if m["executable_now"]]
    best_any=max(plausible,key=lambda x:x["score"],default=None)
    best_ready=max(ready,key=lambda x:x["score"],default=None)
    selected=[]
    if best_any: selected.append(best_any)
    if best_ready and best_ready["method_id"] not in {x["method_id"] for x in selected}: selected.append(best_ready)
    for m in ready:
        if len(selected)>=3: break
        if m["method_id"] not in {x["method_id"] for x in selected}: selected.append(m)
    cards=[]
    for i,m in enumerate(selected[:3]):
        q,desc=_method_plain(m); ready_now=m["executable_now"]
        label="Ready to run" if ready_now else f"{m['implementation_status']} · not runnable here"
        status="ready" if ready_now else "blocked"; why=(m.get("reasons") or [""])[0]
        badge="BEST MATCH" if i==0 else "GOOD OPTION"
        cards.append(f'<div class="cl-method-card {"best" if i==0 else ""}"><span class="cl-method-status {status}">{badge} · {label}</span><div class="cl-method-title">{q}</div><div class="cl-method-copy"><b>{m["name"]}</b><br>{desc}</div><div class="cl-fit">{m["score"]}/100 fit</div><div class="cl-explain">{why}</div></div>')
    if cards: st.markdown('<div class="cl-method-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
    if selected:
        st.markdown('<div class="cl-explainer-note"><b>New to the stats?</b> You do not need to know the jargon. Open any method below and CampaignLab will translate what it is, why it fits, what it needs, and what can fool it.</div>',unsafe_allow_html=True)
        for i,m in enumerate(selected[:3]): render_method_explainer(m, expanded=(i==0))
    if best_any and not best_any["executable_now"]:
        alt=best_ready["name"] if best_ready else "no runnable alternative yet"
        st.warning(f"The strongest methodological fit is {best_any['name']}, but CampaignLab cannot execute it here yet. Best runnable alternative: {alt}.")
    return best_any,best_ready

def _render_interactive_chart(df,intel,plan):
    roles=intel.role_map; cid=plan["id"]
    try:
        if cid=="group_outcome_rate" and roles.get("treatment") and roles.get("binary_outcome"): return interactive_group_rate(df,roles["treatment"][0],roles["binary_outcome"][0])
        if cid=="efficiency_rank" and roles.get("spend") and roles.get("revenue") and (roles.get("channel") or roles.get("campaign")): return interactive_efficiency_rank(df,(roles.get("channel") or roles.get("campaign"))[0],roles["spend"][0],roles["revenue"][0])
        if cid=="spend_vs_revenue" and roles.get("spend") and roles.get("revenue") and (roles.get("channel") or roles.get("campaign")): return interactive_spend_vs_revenue(df,(roles.get("channel") or roles.get("campaign"))[0],roles["spend"][0],roles["revenue"][0])
        if cid=="performance_over_time" and roles.get("date") and (roles.get("revenue") or roles.get("conversions") or roles.get("spend")): return interactive_time(df,roles["date"][0],(roles.get("revenue") or roles.get("conversions") or roles.get("spend"))[0])
        if cid=="group_trends" and roles.get("date") and roles.get("treatment") and (roles.get("continuous_outcome") or roles.get("revenue") or roles.get("conversions")): return interactive_group_trends(df,roles["date"][0],roles["treatment"][0],(roles.get("continuous_outcome") or roles.get("revenue") or roles.get("conversions"))[0])
        if cid=="retention_heatmap" and (roles.get("customer") or roles.get("id")) and roles.get("date"): return interactive_retention(df,(roles.get("customer") or roles.get("id"))[0],roles["date"][0])
        if cid=="media_funnel" and roles.get("impressions") and roles.get("clicks") and roles.get("conversions"): return interactive_funnel(df,roles["impressions"][0],roles["clicks"][0],roles["conversions"][0])
        if cid=="missingness": return interactive_missingness(df)
        if cid=="numeric_distributions": return interactive_distribution(df)
    except Exception:
        return None
    return None

def _load_dataset(uploaded_file) -> pd.DataFrame:
    raw = uploaded_file.getvalue()
    max_bytes = 50 * 1024 * 1024
    if len(raw) > max_bytes:
        raise ValueError("File is larger than the current 50 MB safety limit. Reduce the extract before analysis.")
    if uploaded_file.name.lower().endswith(".csv"):
        return pd.read_csv(io.BytesIO(raw), low_memory=False)
    return pd.read_excel(io.BytesIO(raw))


def _render_handoff():
    handoff = st.session_state.get("experiment_handoff")
    if not handoff:
        return
    source = handoff.get("source", "Another CampaignLab workflow")
    st.success(f"Context carried from {source}: {handoff['strategy_name']}")
    with st.expander(f"See context from {source}"):
        st.markdown(f"**Decision / uncertainty:** {handoff['decision']}")
        st.markdown(f"**Objective:** {handoff['objective']}")
        if handoff.get("audience"):
            st.markdown(f"**Audience:** {handoff['audience']}")
        if handoff.get("budget") not in (None, "", "Not carried from MMM"):
            st.markdown(f"**Budget:** {handoff['budget']} {handoff.get('currency','')} · {handoff.get('budget_period', 'Period not specified')}")
        if handoff.get("assumptions"):
            st.markdown("**Assumptions to challenge:**")
            for item in handoff["assumptions"][:4]: st.write(f"• {item}")
        if handoff.get("risks"):
            st.markdown("**Risks / caveats:**")
            for item in handoff["risks"][:4]: st.write(f"• {item}")
        if handoff.get("unknowns"):
            st.markdown("**Important unknowns:**")
            for item in handoff["unknowns"][:4]: st.write(f"• {item}")
        st.markdown("**Suggested next evidence:**")
        st.write(handoff["suggested_experiment"])
    if st.button("Clear carried context", key="clear_evidence_handoff"):
        st.session_state.experiment_handoff = None
        for key in (
            "experiment_decision_input", "experiment_outcome_input", "experiment_known_input", "experiment_constraints_input",
            "evidence_design_question", "evidence_design_outcome", "evidence_design_constraints", "evidence_plan", "evidence_design_result",
        ):
            st.session_state.pop(key, None)
        st.rerun()


def _render_design_test():
    st.subheader("🧪 Design Evidence")
    st.caption(
        "Bring the uncertainty. CampaignLab maps it to the strongest supported way to learn, asks only for real-world constraints that matter, "
        "and only shows design calculators where CampaignLab has validated them."
    )

    default_question = st.session_state.get("experiment_decision_input", "")
    handoff = st.session_state.get("experiment_handoff")
    if "evidence_design_question" not in st.session_state:
        st.session_state.evidence_design_question = default_question
    if "evidence_design_outcome" not in st.session_state:
        st.session_state.evidence_design_outcome = st.session_state.get("experiment_outcome_input", "")
    if "evidence_design_constraints" not in st.session_state:
        st.session_state.evidence_design_constraints = st.session_state.get("experiment_constraints_input", "")
    question = st.text_area(
        "What are you trying to find out?",
        placeholder=evidence_design_placeholder(handoff),
        key="evidence_design_question",
        help=(
            "Say it in business language. Examples: Did the new checkout increase purchases? "
            "Did the pricing change hurt retention? Which offer should we launch?"
        ),
    )
    outcome = st.text_input(
        "What would you look at to know it worked?",
        placeholder=evidence_outcome_placeholder(question, handoff),
        key="evidence_design_outcome",
        help=(
            "Use the name you use in the business — purchases, revenue per visitor, retention, "
            "qualified leads, average order value, usage, or something else."
        ),
    )

    st.markdown('<div class="cl-form-kicker">WHAT CAN ACTUALLY CHANGE IN THE REAL WORLD?</div>', unsafe_allow_html=True)
    change_scope = st.selectbox(
        "Which situation is closest?",
        [
            "I'm not sure yet",
            "Different people can receive different experiences",
            "Different stores, markets, teams, or accounts can receive the change",
            "The change would happen everywhere at once",
            "The change already happened",
        ],
        key="evidence_change_scope",
        help=(
            "Pick the closest description, not a statistical design. CampaignLab uses this to work out "
            "whether individual randomization, group-level testing, time-based evidence, or analysis of existing data makes sense."
        ),
    )

    constraints = st.text_area(
        "Anything that could make testing hard? · optional",
        placeholder="e.g. We only have 8 stores, the launch must happen nationwide, customers can see the experience more than once, or we need an answer within 3 weeks.",
        key="evidence_design_constraints",
        height=95,
        help="Operational reality matters. CampaignLab should adapt the design to the world, not the other way around.",
    )

    if change_scope == "I'm not sure yet":
        st.info(
            "That's fine. You do not need to know the design. CampaignLab can still give you a useful first plan: "
            "it will show what needs to be established before choosing a method, without asking you to invent statistical details."
        )

    if st.button("Find My Evidence Path", type="primary", use_container_width=True, key="build_evidence_plan"):
        if not question.strip():
            st.warning("Give CampaignLab the uncertainty you want to resolve first.")
        else:
            st.session_state["evidence_plan"] = {
                "question": question.strip(),
                "outcome": outcome.strip(),
                "scope": change_scope,
                "constraints": constraints.strip(),
            }
            # A new plan invalidates any old design-sizing result.
            st.session_state.pop("evidence_design_result", None)

    plan = st.session_state.get("evidence_plan")
    if not plan:
        return

    current_plan_inputs = {
        "question": question.strip(),
        "outcome": outcome.strip(),
        "scope": change_scope,
        "constraints": constraints.strip(),
    }
    if plan != current_plan_inputs:
        st.info("You changed the situation. Build the evidence plan again so CampaignLab does not show a stale recommendation.")
        return

    st.divider()
    st.caption("CAMPAIGNLAB'S PLAN")
    scope = plan["scope"]
    outcome_name = plan["outcome"] or "the business outcome that would settle the decision"

    if scope == "Different people can receive different experiences":
        st.header("A controlled test looks feasible")
        st.write(
            "Because comparable people can receive different experiences, individual-level randomization may give you a clean answer. "
            "CampaignLab would normally start with the current experience versus the proposed change, then add more conditions only if your decision genuinely requires them."
        )
        st.markdown(f"**Outcome to track:** {outcome_name}")
        st.markdown("**Likely assignment unit:** the stable person / customer / account that receives the experience")
        st.markdown("**Default comparison:** current experience vs proposed change")
        st.caption("The exact design still depends on how the outcome is recorded and whether the same unit can cross between experiences.")
        design_path = "individual"
    elif scope == "Different stores, markets, teams, or accounts can receive the change":
        st.header("A group-level controlled test may fit")
        st.write(
            "The change can vary across groups rather than individual people. That points toward a cluster or geo-style design when the groups are comparable enough. "
            "CampaignLab should check group count, balance, contamination, timing, and pre-period behavior before calling the design credible."
        )
        st.markdown(f"**Outcome to track:** {outcome_name}")
        st.markdown("**Likely assignment unit:** store, market, team, account, or another stable group")
        st.warning("Dedicated design-time sizing for cluster / geo experiments is not yet promoted as a Live CampaignLab calculator, so CampaignLab will not invent a sample-size number here.")
        design_path = "group"
    elif scope == "The change would happen everywhere at once":
        st.header("Don't force an A/B test")
        st.write(
            "If everyone receives the change at the same time, there may be no simultaneous control group. The strongest path may be time-based evidence — "
            "for example interrupted time series — or another causal design if a credible comparison group exists elsewhere."
        )
        st.markdown(f"**Outcome to track:** {outcome_name}")
        st.markdown("**What CampaignLab would challenge:** trend, seasonality, concurrent events, measurement changes, and whether enough pre/post history exists")
        design_path = "time"
    elif scope == "The change already happened":
        st.header("You already have evidence to inspect")
        st.write(
            "This is no longer mainly a design problem. CampaignLab should inspect what actually happened, what comparison is available, and what claim the data can support."
        )
        st.markdown(f"**Outcome to investigate:** {outcome_name}")
        st.caption("Use Analyze Results if you ran a structured experiment. Use Analyze Data if you have event, panel, campaign, customer, or time-series data.")
        design_path = "existing"
    else:
        st.header("First, establish what can vary")
        st.write(
            "CampaignLab does not need you to know the statistical method. The first useful question is operational: can the change vary across people, groups, or time — or has it already happened?"
        )
        st.markdown("**CampaignLab's next check:**")
        st.write("• Can comparable people receive different experiences without crossing over?")
        st.write("• If not, can comparable stores, markets, teams, or accounts receive different versions of the change?")
        st.write("• If not, will the change happen everywhere at once, leaving time as the main source of comparison?")
        st.write("• If it already happened, bring the resulting data instead of trying to reconstruct a hypothetical experiment.")
        st.success("You can leave this page with a next step even if you do not know the design yet: answer the operational question above, or bring the data you already have and let CampaignLab inspect it.")
        design_path = "triage"

    if plan.get("constraints"):
        with st.expander("Reality check · constraints you gave CampaignLab"):
            st.write(plan["constraints"])

    if design_path == "existing":
        c1, c2 = st.columns(2)
        with c1:
            st.button(
                "Analyze a structured test →",
                use_container_width=True,
                key="route_existing_results",
                on_click=lambda: st.session_state.update(evidence_route="📈 I already ran a test"),
            )
        with c2:
            st.button(
                "Bring the data →",
                use_container_width=True,
                key="route_existing_data",
                on_click=lambda: st.session_state.update(evidence_route="📂 I have data"),
            )
        return

    if design_path in {"time", "group"}:
        if st.button(
            "Bring data for CampaignLab to inspect →",
            use_container_width=True,
            key=f"route_design_data_{design_path}",
            on_click=lambda: st.session_state.update(evidence_route="📂 I have data"),
        ):
            pass
        return

    if design_path == "triage":
        st.caption("CampaignLab has reduced the uncertainty to one operational distinction. Change the situation above when you know it, or bring whatever evidence already exists and let CampaignLab inspect it.")
        if st.button("Bring whatever data I have →", use_container_width=True, key="triage_to_data"):
            st.session_state.evidence_route = "📂 I have data"
            st.rerun()
        return

    # Individual-level controlled path: only now ask for the measurement shape,
    # because it changes the deterministic calculator CampaignLab is allowed to use.
    st.markdown("### One detail to finish the recommendation")
    measurement = st.selectbox(
        "How does that outcome show up in the data?",
        ["I'm not sure", "A yes / no action", "A number or amount"],
        key="evidence_measurement_shape",
        help=(
            "Examples: purchased/didn't purchase is a yes/no action. Revenue, order value, time, or usage are numbers. "
            "If you're not sure, CampaignLab will explain the distinction instead of blocking you."
        ),
    )

    if measurement == "I'm not sure":
        st.info(
            "No problem. If each eligible unit either does or does not do the thing, treat it as a yes/no outcome. "
            "If every unit has a numeric value — dollars, minutes, units, balance, usage — treat it as a numeric outcome. "
            "Your evidence plan above is still valid either way."
        )
        st.caption("Choose one only if you want CampaignLab to continue into a supported design-time calculator. Your evidence plan above is still usable.")
        st.button(
            "Bring example data for CampaignLab to inspect →",
            use_container_width=True,
            key="route_unknown_measurement_data",
            on_click=lambda: st.session_state.update(evidence_route="📂 I have data"),
        )
        return

    if measurement == "A number or amount":
        st.success("CampaignLab recommends a two-condition controlled comparison with a numeric outcome.")
        st.write(
            "CampaignLab can analyze continuous-outcome A/B results once the data exists. Dedicated design-time sample sizing for this path is not yet promoted, "
            "so it will not fabricate a required sample without the variance assumptions that calculation needs."
        )
        return

    st.success("CampaignLab recommends a two-condition randomized test with a yes/no outcome.")
    st.caption("Now the deterministic sizing calculator can take over. You only need to supply business quantities it cannot responsibly invent.")

    st.markdown("### Size the test")
    col1, col2, col3 = st.columns(3)
    with col1:
        baseline_pct = st.number_input(
            "What happens today? · baseline rate (%)",
            min_value=0.01,
            max_value=99.0,
            value=5.0,
            step=0.1,
            help="If about 5 in 100 eligible people do the thing today, enter 5.",
        )
    with col2:
        mde_pp = st.number_input(
            "How much improvement would be worth acting on? · points",
            min_value=0.01,
            max_value=50.0,
            value=0.5,
            step=0.1,
            help="This is the smallest absolute improvement worth detecting. Example: 5.0% to 5.5% is +0.5 percentage points.",
        )
    with col3:
        power_label = st.selectbox(
            "How cautious should the test be about missing a real effect?",
            ["Standard · 80%", "Strong · 90%", "Very strong · 95%"],
            index=0,
            help="Higher power reduces the chance of missing a real effect, but requires more observations.",
        )
        power_pct = {"Standard · 80%": 80, "Strong · 90%": 90, "Very strong · 95%": 95}[power_label]

    with st.expander("Under the hood · statistical settings"):
        st.write(f"Power: {power_pct}%")
        st.write("Alpha: 5%, two-sided")
        st.write(f"Minimum detectable effect: +{mde_pp:.2f} percentage points")

    if st.button("Size This Test", type="primary", use_container_width=True, key="design_binary_ab"):
        baseline = baseline_pct / 100
        target = baseline + mde_pp / 100
        if target >= 1:
            st.error("Baseline plus target lift must remain below 100%.")
            return
        n = required_sample_size_per_group(baseline, target, alpha=0.05, power=power_pct / 100)
        st.session_state["evidence_design_result"] = {
            "question": plan["question"],
            "outcome": plan["outcome"],
            "baseline": baseline,
            "target": target,
            "mde": mde_pp / 100,
            "power": power_pct / 100,
            "n": n,
        }

    result = st.session_state.get("evidence_design_result")
    if result:
        sizing_signature = (baseline_pct / 100, mde_pp / 100, power_pct / 100)
        saved_signature = (result["baseline"], result["mde"], result["power"])
        if sizing_signature != saved_signature:
            st.info("You changed the sizing assumptions. Run Size This Test again before CampaignLab shows a recommendation based on the old settings.")
            return
        st.divider()
        st.caption("CAMPAIGNLAB RECOMMENDS")
        st.header("Randomized A/B test · yes/no outcome")
        m1, m2, m3 = st.columns(3)
        m1.metric("People / units per group", f"{result['n']:,}")
        m2.metric("Total needed", f"{result['n'] * 2:,}")
        m3.metric("Smallest lift targeted", _pp(result["mde"]))
        st.write(
            f"At a {result['baseline']:.1%} baseline, this design is sized to reliably detect about "
            f"{result['mde'] * 100:.2f} percentage points of lift under the settings below."
        )
        st.pyplot(sample_size_curve(result["baseline"], power=result["power"]), clear_figure=True)
        with st.expander("📋 Give this to my analyst / data scientist"):
            st.code(
                f"""Experiment specification
Question: {result['question'] or 'Not specified'}
Primary outcome: {result['outcome'] or 'Binary conversion outcome'}
Design: 50/50 randomized A/B test
Unit of randomization: choose the stable unit that receives treatment
Baseline conversion: {result['baseline']:.4f}
Minimum detectable absolute lift: {result['mde']:.4f}
Alpha: 0.05 (two-sided)
Target power: {result['power']:.2f}
Required sample: {result['n']} per arm
""",
                language="text",
            )

def _render_analysis_call(result):
    tone = {"SHIP": "success", "HOLD": "warning", "DON'T SHIP": "error"}[result.verdict]
    getattr(st, tone)(f"CAMPAIGNLAB'S CALL: {result.verdict}")
    st.write(result.verdict_reason)

    if result.srm_status == "fail":
        st.error(
            "Analysis risk: sample-ratio mismatch detected. The observed traffic split is unlikely under the expected allocation. Check assignment and logging before trusting the treatment comparison."
        )
    elif result.robustness_status == "robust":
        st.success("Cross-check passed: two independent statistical checks agree, and the traffic split does not show a sample-ratio warning.")
    else:
        st.warning("Cross-check warning: two reasonable statistical checks do not fully agree. Treat the conclusion as fragile and inspect the detail below.")


def _render_analyze_results():
    st.subheader("📈 Analyze Results")
    st.caption("Enter what happened. CampaignLab calculates the result first, then explains what the evidence means.")

    experiment_type = st.selectbox(
        "What experiment did you run?",
        ["A/B test — binary outcome", "Other / help me identify it"],
    )
    if experiment_type != "A/B test — binary outcome":
        st.info("CampaignLab cannot safely reconstruct every test from a few summary numbers. Bring the raw experiment data instead and CampaignLab can inspect its structure, identify supported methods, and tell you what the evidence can actually answer.")
        if st.button("Bring the experiment data →", use_container_width=True, key="results_to_data"):
            st.session_state.evidence_route = "📂 I have data"
            st.rerun()
        return

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Control")
        control_n = _comma_int_input("Control participants", 10000, "control_participants")
        control_conv = _comma_int_input("Control conversions", 500, "control_conversions")
    with c2:
        st.markdown("#### Treatment")
        treatment_n = _comma_int_input("Treatment participants", 10000, "treatment_participants")
        treatment_conv = _comma_int_input("Treatment conversions", 560, "treatment_conversions")

    c3, c4 = st.columns(2)
    with c3:
        expected_treatment_pct = st.number_input(
            "How was traffic supposed to split? · treatment share (%)",
            min_value=1.0, max_value=99.0, value=50.0, step=1.0,
            help="50 means an intended 50/50 split between control and treatment.",
        )
    with c4:
        threshold_pp = st.number_input(
            "What's the smallest improvement worth acting on? · percentage points",
            min_value=0.0, max_value=50.0, value=0.25, step=0.05,
            help="CampaignLab uses this business threshold separately from statistical significance.",
        )

    if st.button("Run Evidence Analysis", type="primary", use_container_width=True, key="run_ab_results"):
        try:
            st.session_state["evidence_ab_result"] = analyze_binary_ab(
                int(control_n),
                int(control_conv),
                int(treatment_n),
                int(treatment_conv),
                expected_treatment_share=expected_treatment_pct / 100,
                business_threshold=threshold_pp / 100,
            )
            st.session_state["evidence_ab_signature"] = (
                int(control_n), int(control_conv), int(treatment_n), int(treatment_conv),
                float(expected_treatment_pct), float(threshold_pp),
            )
        except ValueError as exc:
            st.error(str(exc))
            return

    result = st.session_state.get("evidence_ab_result")
    if not result:
        return
    current_signature = (
        int(control_n), int(control_conv), int(treatment_n), int(treatment_conv),
        float(expected_treatment_pct), float(threshold_pp),
    )
    if st.session_state.get("evidence_ab_signature") != current_signature:
        st.info("These inputs changed after the last analysis. Run Evidence Analysis again so CampaignLab does not show a stale result.")
        return

    st.divider()
    _render_analysis_call(result)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Control conversion", _pct(result.control_rate))
    m2.metric("Treatment conversion", _pct(result.treatment_rate))
    m3.metric("Absolute lift", _pp(result.absolute_lift))
    m4.metric("Relative lift", "N/A" if result.relative_lift is None else _pct(result.relative_lift))

    st.markdown("#### What this means")
    crosses_zero = result.ci_low <= 0 <= result.ci_high
    range_read = "The uncertainty range still includes no effect, so the direction is not settled." if crosses_zero else "The uncertainty range stays on one side of zero, so the direction is more stable statistically."
    st.write(
        f"The best estimate is {_pp(result.absolute_lift)}. A 95% uncertainty range runs from "
        f"{_pp(result.ci_low)} to {_pp(result.ci_high)}. {range_read}"
    )
    st.caption("Open statistical detail below for the confidence interval, p-values, exact-test check, sample-ratio check, and post-experiment power diagnostic.")

    chart1, chart2 = st.columns(2)
    with chart1:
        st.plotly_chart(ab_conversion_result(result), use_container_width=True, config={"displaylogo":False,"responsive":True})
        st.caption("What this shows: observed conversion in each arm. Hover for exact rates and sample sizes.")
    with chart2:
        st.plotly_chart(ab_effect_interval(result), use_container_width=True, config={"displaylogo":False,"responsive":True})
        st.caption("What this shows: estimated lift, uncertainty around it, and the business threshold when supplied.")

    with st.expander("See statistical detail"):
        st.write(f"Two-proportion z-test p-value: {result.p_value:.6f}")
        st.write(f"Fisher exact p-value: {result.fisher_p_value:.6f}")
        st.write(f"SRM exact-binomial p-value: {result.srm_p_value:.6f}")
        if result.achieved_power_at_observed_effect is not None:
            st.write(f"Approximate power at the observed effect size: {result.achieved_power_at_observed_effect:.1%}")
        st.caption("Power at the observed effect is descriptive after the experiment; design-time power/MDE is usually more useful for planning.")


def _render_analyze_data(client):
    st.subheader("📂 Understand & Analyze Data")
    st.caption("Start with the data you have. CampaignLab first works out what it is, what it can answer, and what needs your judgment.")

    method_interest = st.session_state.get("directory_method_interest")
    if method_interest:
        method = get_method(method_interest)
        if method:
            q, _ = _method_plain(method)
            st.info(f"You came here from Analytics Directory looking at **{q}**. Bring the evidence first; CampaignLab will verify whether it actually fits instead of forcing the method onto the data.")

    st.markdown("### Bring your data — or try a realistic example")
    demo1, demo2 = st.columns(2)
    with demo1:
        if st.button("🚀 Load Marketing Growth Demo", use_container_width=True, key="load_marketing_demo"):
            st.session_state["evidence_demo_dataset"] = "demo_marketing_evidence.csv"
    with demo2:
        if st.button("🛰️ Load Rollout / Causal Demo", use_container_width=True, key="load_rollout_demo"):
            st.session_state["evidence_demo_dataset"] = "demo_panel_rollout.csv"
    st.caption("Marketing demo: variants, conversion, revenue and channels. Rollout demo: panel/time-series structure for causal methods such as DiD and event study.")

    uploaded = st.file_uploader(
        "Or upload your own CSV / Excel",
        type=["csv", "xlsx"],
        key="evidence_dataset",
        help="CampaignLab inspects the file first and shares only compact analytical summaries with the AI planner.",
    )

    df = None
    preliminary_intel = None
    source_name = ""
    if uploaded:
        st.session_state["evidence_demo_dataset"] = None
        try:
            df = _load_dataset(uploaded)
            source_name = uploaded.name
            preliminary_intel = analyze_dataset_intelligence(df, "")
        except Exception as exc:
            st.error(f"CampaignLab could not read this file: {exc}")
            return
    elif st.session_state.get("evidence_demo_dataset"):
        source_name = st.session_state["evidence_demo_dataset"]
        demo_path = Path(__file__).resolve().parents[1] / "examples" / source_name
        try:
            df = pd.read_csv(demo_path)
            preliminary_intel = analyze_dataset_intelligence(df, "")
            st.success(f"Demo loaded: {source_name}")
        except Exception as exc:
            st.error(f"CampaignLab could not load the demo dataset: {exc}")
            return

    if df is None:
        st.info("Upload a file or load one of the demos. CampaignLab will first show what it recognizes before asking what you want to learn from it.")
        return

    profile = profile_dataframe(df)
    dataset_fingerprint = _dataset_fingerprint(df, source_name)
    st.success(f"Loaded {source_name}: {profile.rows:,} rows × {profile.columns:,} columns")
    understanding, role_overrides, unresolved_roles = _render_data_builder_understanding(df, source_name, dataset_fingerprint[:12])

    st.markdown("### Now, what do you want from this data?")
    question = st.text_area(
        "What do you want to decide or understand?",
        placeholder=dataset_question_placeholder(
            preliminary_intel.role_map if preliminary_intel else None,
            source_name,
        ),
        key="evidence_dataset_question",
        help="You can leave this blank. CampaignLab will show the strongest questions this evidence appears capable of answering.",
    )

    intel = analyze_dataset_intelligence(df, question, role_overrides=role_overrides)
    ranked = rank_methods(intel, question)
    chart_plan = recommend_visualizations(intel, question)
    st.markdown('<div class="cl-modebar">', unsafe_allow_html=True)
    view_mode = st.segmented_control("View", ["Executive", "Analyst"], default="Executive", key=f"evidence_view_mode_{source_name}", help="Executive keeps the decision path tight. Analyst opens the implementation and diagnostic detail.")
    st.markdown('</div>', unsafe_allow_html=True)

    intelligence_label("CampaignLab sees")
    st.markdown("## What CampaignLab understands")
    st.caption(f"Likely level of detail: {intel.grain_guess}. CampaignLab maps what each useful field appears to mean before choosing an analysis.")
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Rows", f"{profile.rows:,}")
    d2.metric("Columns", f"{profile.columns:,}")
    d3.metric("Missing", f"{profile.missing_rate:.1%}")
    d4.metric("Duplicates", f"{profile.duplicate_rate:.1%}")
    _render_role_chips(intel.role_map)

    assessment = intel.question_assessment
    if assessment["status"] == "blocked":
        st.error("Not enough evidence for that exact question yet.")
        for blocker in assessment["blockers"]:
            st.write(f"• {blocker}")
    elif assessment["status"] == "provisionally_answerable":
        st.success("Good news: this file looks capable of investigating your question. CampaignLab will still check the assumptions before making a call.")
    else:
        st.info("No question yet? That's fine. CampaignLab is scanning for the strongest things this dataset can answer.")

    if view_mode == "Analyst":
        with st.expander("See the full column map", expanded=False):
            role_rows=[]
            for role,cols in intel.role_map.items():
                if cols:
                    role_rows.append({"CampaignLab role": role.replace("_"," ").title(), "Detected column(s)": ", ".join(cols[:8])})
            if role_rows: st.dataframe(pd.DataFrame(role_rows),use_container_width=True,hide_index=True)
            else: st.write("CampaignLab did not infer high-confidence analytical roles yet.")

    warnings=[f for f in intel.quality_findings if f["level"]=="warning"]
    if warnings:
        intelligence_label("Watch-outs")
        st.markdown("### What could make the answer unreliable")
        for finding in warnings[:6]:
            st.warning(finding["finding"])
    else:
        st.success("Data health looks clean enough to keep moving. No critical quality warnings detected.")

    intelligence_label("CampaignLab recommends")
    st.markdown("## What this data is best equipped to answer")
    st.caption("Start with the question. The statistical method sits underneath it, with the technical detail available when you want it.")
    best_any,best_ready=_render_method_cards(ranked)

    blocked=[m for m in ranked if not m["eligible"]]
    if blocked:
        with st.expander("What else did CampaignLab consider?"):
            for method in blocked[:6]:
                q,desc=_method_plain(method)
                st.markdown(f"**{q} — {method['name']}**")
                st.caption(desc)
                for blocker in method["blockers"]:
                    st.write(f"• Missing: {blocker}")

    intelligence_label("Decision chartbook")
    st.markdown("## Start with the views that explain the story")
    st.caption("CampaignLab starts with a small set of useful views. Add or remove charts only when they help you understand the decision.")

    available_ids=[p["id"] for p in chart_plan]
    selected_default=available_ids[:3]
    selected_ids=st.multiselect(
        "Choose views",
        options=available_ids,
        default=selected_default,
        format_func=lambda cid: next((p["title"] for p in chart_plan if p["id"]==cid),cid),
        key=f"chartbook_{source_name}",
        help="CampaignLab preselects the strongest views. Add or remove any chart you want.",
    )
    plans=[p for p in chart_plan if p["id"] in selected_ids]
    rendered=0
    for idx,plan in enumerate(plans,start=1):
        st.markdown(f"### {idx:02d} · {plan['title']}")
        st.caption(plan["why"])
        interactive=_render_interactive_chart(df,intel,plan)
        if interactive is not None:
            st.plotly_chart(interactive,use_container_width=True,config={"displaylogo":False,"responsive":True})
            rendered += 1
            continue
        fig=build_visualization(df,intel,plan["id"])
        if fig is not None:
            st.pyplot(fig,clear_figure=True,use_container_width=True)
            rendered += 1
    if rendered==0:
        st.info("No chart is earning its place yet. CampaignLab would rather show nothing than fill the page with dashboard wallpaper.")

    if view_mode == "Analyst":
        with st.expander("Preview data"):
            st.dataframe(df.head(100), use_container_width=True, hide_index=True)

    st.divider()
    intelligence_label("CampaignLab plan")
    st.markdown("## Turn the evidence into a decision")
    st.write("CampaignLab will use the strongest supported analytical path, run only validated calculations, and separate what the evidence supports from what remains uncertain.")

    if assessment["status"] == "blocked" and question.strip():
        blockers_text = "; ".join(assessment.get("blockers") or [])
        orchestrator_question = (
            f"The user's exact question is currently blocked: {question.strip()}\n"
            f"Deterministic blockers: {blockers_text}. Explain the evidence gap, identify the nearest defensible analysis this data can support, and specify the smallest additional evidence that would unlock the original question. Do not pretend the blocked question was answered."
        )
        button_label = "✦ Show me what would unlock this question"
    else:
        orchestrator_question = question.strip() or (
            "Inspect the uploaded dataset. Determine what this dataset can defensibly answer, rank the highest-value analytical opportunities and methods, "
            "recommend the smallest useful visualization set, distinguish executable methods from planned/research methods, and give the next analytical action."
        )
        button_label = "✦ Build my analysis plan" if not question.strip() else "✦ Analyze this decision"
    if client is None:
        st.info("The deterministic Evidence engine is available. Add the OpenAI API key to enable the tool-using planner.")
        return
    if st.button(button_label, type="primary", use_container_width=True, key="run_evidence_orchestrator"):
        runtime = EvidenceToolRuntime(dataframe=df, role_overrides=role_overrides)
        with st.spinner("CampaignLab is reading the signal, checking the method, and building the analysis..."):
            try:
                result = run_evidence_orchestrator(client, orchestrator_question, runtime)
                st.session_state["evidence_orchestration_result"] = result
                st.session_state["evidence_orchestration_signature"] = (dataset_fingerprint, question.strip(), tuple(sorted(role_overrides.items())))
                st.session_state.pop(f"result_qa_answer_{source_name}", None)
            except Exception as exc:
                st.error(f"Evidence Orchestrator could not complete: {exc}")

    orchestration = st.session_state.get("evidence_orchestration_result")
    current_orchestration_signature = (dataset_fingerprint, question.strip(), tuple(sorted(role_overrides.items())))
    same_analysis = st.session_state.get("evidence_orchestration_signature") == current_orchestration_signature
    if orchestration and not same_analysis:
        st.info("The dataset or question changed after the last CampaignLab analysis. Run the plan again before using the old conclusion.")
    if orchestration and same_analysis:
        intelligence_label("CampaignLab's plan")
        st.markdown('<div class="cl-call"><h2>Here\'s the move.</h2><p>CampaignLab has inspected the evidence and built the next analytical step.</p></div>', unsafe_allow_html=True)
        st.markdown(orchestration.text)
        st.markdown('<div class="cl-report-card"><b>Take the decision with you.</b><br><span style="color:#aeb7bc">Export a clean, executive-ready record of the question, evidence, recommended method, warnings and CampaignLab analysis.</span></div>', unsafe_allow_html=True)
        pdf_bytes = build_decision_report(source_name=source_name, question=question, profile=profile, intel=intel, best_method=best_ready or best_any, orchestration_text=orchestration.text)
        st.download_button("↓ Export Decision Report · PDF", data=pdf_bytes, file_name=f"CampaignLab_Decision_Report_{Path(source_name).stem}.pdf", mime="application/pdf", use_container_width=True)

        with st.expander("Ask CampaignLab about this result"):
            followup = st.text_input("What do you want to understand?", placeholder="e.g. What would make this conclusion weaker?", key=f"result_qa_input_{source_name}")
            if st.button("Ask about this result", key=f"result_qa_button_{source_name}", use_container_width=True, disabled=not bool(followup.strip())):
                with st.spinner("CampaignLab is translating the result..."):
                    try:
                        answer = ask_about_result(client, question=question, analysis_text=orchestration.text, method_name=(best_ready or best_any or {}).get("name", ""), user_question=followup.strip())
                        st.session_state[f"result_qa_answer_{source_name}"] = answer
                    except Exception as exc:
                        st.error(f"CampaignLab could not answer the follow-up: {exc}")
            answer = st.session_state.get(f"result_qa_answer_{source_name}")
            if answer: st.markdown(answer)

        if orchestration.traces and view_mode == "Analyst":
            with st.expander(f"Analysis audit trail · {len(orchestration.traces)} tool calls"):
                for i, trace in enumerate(orchestration.traces, start=1):
                    icon = "✅" if trace.status == "ok" else "⚠️"
                    st.markdown(f"**{i}. {icon} `{trace.name}`**")
                    if trace.arguments:
                        st.code(json.dumps(trace.arguments, indent=2), language="json")
                    st.caption(trace.output_summary)
        if orchestration.usage.get("total_tokens") and view_mode == "Analyst":
            st.caption(
                f"Technical detail: {orchestration.usage['input_tokens']:,} input + "
                f"{orchestration.usage['output_tokens']:,} output tokens. This is visible for cost/performance tuning, not part of the end-user decision."
            )

def render_evidence_lab(client):
    st.markdown(f"""<section class="cl-lab-hero evidence">
      {lab_mark("evidence", "lg")}
      <div class="cl-lab-hero-copy"><div class="cl-lab-kicker">EVIDENCE LAB</div>
      <h1>Bring the claim. We'll bring the receipts.</h1>
      <p>Create evidence, read results, or bring the data you already have. You tell CampaignLab what you need to know; it figures out the strongest defensible path.</p></div>
    </section>""", unsafe_allow_html=True)
    _render_handoff()

    st.markdown("### Where are you starting from?")
    st.caption("You do not need to know the method. Pick the situation that matches reality.")
    route = st.radio(
        "Evidence starting point",
        ["🧪 I need to create evidence", "📈 I already ran a test", "📂 I have data"],
        horizontal=True,
        key="evidence_route",
        label_visibility="collapsed",
    )
    st.divider()
    if route == "🧪 I need to create evidence":
        _render_design_test()
    elif route == "📈 I already ran a test":
        _render_analyze_results()
    else:
        _render_analyze_data(client)


def render_analytics_directory():
    st.markdown(f'<div style="display:flex;align-items:center;gap:.8rem">{utility_mark("directory", "md")}<h1 style="margin:0">Analytics Directory</h1></div>', unsafe_allow_html=True)
    st.write("Start with the decision you need to make. CampaignLab maps that question to an analytical family, then exposes the proper method and the statistical machinery underneath it.")
    st.caption("Start with the question. CampaignLab handles the translation from business problem → analytical family → method → statistical machinery.")

    st.markdown("""<div class="cl-status-legend">
      <div class="ready"><b>✓ READY TO RUN</b><span>CampaignLab can execute this now when your evidence meets the method's requirements.</span></div>
      <div class="special"><b>✦ GUARDED WORKSPACE</b><span>Runnable in a dedicated Lab Special with extra readiness checks and guardrails.</span></div>
      <div class="coming"><b>◷ COMING NEXT</b><span>Defined in the roadmap, but CampaignLab will not pretend it can run it yet.</span></div>
      <div class="research"><b>◇ BEING EXPLORED</b><span>Promising, but still under validation before CampaignLab calls it supported.</span></div>
    </div>""", unsafe_allow_html=True)

    live_count=sum(m["status"]=="Live" for m in METHODS); beta_count=sum(m["status"]=="Beta" for m in METHODS)
    planned_count=sum(m["status"]=="Planned" for m in METHODS); research_count=sum(m["status"]=="Research" for m in METHODS)
    st.caption(f"{live_count} ready to run · {beta_count} guarded workspace · {planned_count} coming next · {research_count} being explored")

    st.markdown("## Browse by decision question")
    st.write("You should not need to know whether your problem requires a z-test, event study or random forest before CampaignLab can help you.")
    family_ids=[f["id"] for f in DECISION_FAMILIES]
    labels={f["id"]:f["title"] for f in DECISION_FAMILIES}
    selected=st.segmented_control("Decision family",family_ids,default=None,format_func=lambda x:labels[x],label_visibility='collapsed',key='directory_family')
    if selected is None:
        st.markdown('<div class="cl-explainer-note"><b>Pick the question, not the technique.</b> Nothing is preselected here because CampaignLab should not quietly steer every user toward experimentation.</div>', unsafe_allow_html=True)
        for f in DECISION_FAMILIES:
            st.markdown(f'<div class="cl-family-card"><div class="campaignlab-kicker">{f["title"]}</div><div class="q">{f["question"]}</div><div class="desc">{f["description"]}</div></div>', unsafe_allow_html=True)
        return
    family=next(f for f in DECISION_FAMILIES if f['id']==selected)
    st.markdown(f'<div class="cl-family-card"><div class="campaignlab-kicker">{family["title"]}</div><div class="q">{family["question"]}</div><div class="desc">{family["description"]}</div><div class="count">{len(family["method_ids"])} methods / capabilities mapped here</div></div>',unsafe_allow_html=True)

    query=st.text_input("Search inside this decision family",placeholder="e.g. conversion lift, revenue per visitor, event study…",key='analytics_directory_search')
    q=query.lower().strip(); status_icon={"Live":"✓","Beta":"✦","Planned":"◷","Research":"◇"}
    for mid in family['method_ids']:
        method=get_method(mid)
        if not method: continue
        presentation=METHOD_PRESENTATION.get(mid,{"human_name":method['name'],"technical":method['name'],"machinery":method.get('diagnostics',[])[:4]})
        blob=' '.join([presentation['human_name'],presentation['technical'],method['answers'],method['requires'],' '.join(method.get('use_cases',[]))]).lower()
        if q and q not in blob: continue
        machinery=''.join(f'<span class="cl-machine-pill">{x}</span>' for x in presentation.get('machinery',[]))
        status_label={"Live":"Ready to run","Beta":"Guarded workspace","Planned":"Coming next","Research":"Being explored"}.get(method["status"],method["status"])
        st.markdown(f'<div class="cl-method-shell"><div class="human">{presentation["human_name"]}</div><div class="technical">{presentation["technical"]} · {status_label}</div><div class="cl-machinery">{machinery}</div></div>',unsafe_allow_html=True)
        with st.expander(f"{status_icon.get(method['status'],'⚪')} See what {presentation['human_name']} does"):
            st.markdown("**Question it answers**"); st.write(method['answers'])
            c1,c2=st.columns(2)
            with c1:
                st.markdown("**Evidence it needs**"); st.write(method['requires'])
                st.markdown("**Good uses**")
                for x in method.get('use_cases',[]): st.write(f"• {x}")
            with c2:
                st.markdown("**Trust checks**")
                for x in method.get('diagnostics',[]): st.write(f"• {x}")
                st.markdown("**What comes back**")
                for x in method.get('outputs',[]): st.write(f"• {x}")
            if presentation.get('machinery'):
                st.markdown("**Under the hood**")
                st.caption(" · ".join(presentation['machinery']))
            st.warning(method['caution'])
            if method['status']=='Live':
                st.success("Ready to run when your evidence satisfies the method requirements.")
                if st.button("Use this with my data →", key=f"use_method_{mid}", use_container_width=True):
                    st.session_state.directory_method_interest = mid
                    st.session_state.evidence_route = "📂 I have data"
                    _go_to("evidence")
            elif method['status']=='Beta':
                st.info("Runnable in its dedicated guarded workspace while validation expands.")
                if mid == "mmm_beta" and st.button("Open the guarded MMM workspace →", key=f"open_method_{mid}", use_container_width=True):
                    _go_to("mmm")
            else: st.info("Visible so you can see where CampaignLab is going. It will not claim execution until the implementation is validated and promoted.")

    st.markdown("## Lab Specials")
    st.write("Heavier end-to-end analytical products get their own workspace instead of making Evidence Lab noisy.")
    for special in LAB_SPECIALS:
        st.markdown(f'<div class="cl-special-card"><div class="cl-special-badge">LAB SPECIAL · {special["status"].upper()}</div><div class="cl-special-title">{special["title"]}</div><div class="q"><b>{special["question"]}</b></div><div class="cl-home-copy">{special["description"]}</div><div class="cl-home-cta">Use the dedicated workspace below.</div></div>',unsafe_allow_html=True)
        st.caption(special['guardrail'])
        if special.get('method_id') == 'mmm_beta' or 'mix' in special.get('title','').lower():
            st.markdown('[Open Marketing Mix Model →](?page=mmm)')

    st.markdown("## What is next")
    st.write("Forecasting is the next major analytical family to promote once its own readiness gate, naïve/seasonal baselines, ARIMA/ETS benchmarking, rolling backtests, prediction intervals and failure behavior are validated. Individualized uplift stays Research until treatment-effect diagnostics are equally defensible.")

