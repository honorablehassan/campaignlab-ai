import json

import streamlit as st

from engines.battle_engine import generate_strategy_battle
from engines.context_engine import check_context
from engines.red_team_engine import generate_red_team
from engines.scenario_engine import evaluate_scenario, generate_scenario_setup
from engines.strategy_engine import generate_strategy
from state import (
    prepare_experiment_handoff,
    reset_scenario_state,
    reset_strategy_downstream,
)
from utils.display import rating_icon, render_callout
from ui.copy_engine import followup_placeholder, strategy_placeholder
from ui.brand import lab_mark


def _collect_strategy_inputs():
    decision_type = st.selectbox(
        "What kind of problem are we solving?",
        [
            "Build a Strategy",
            "Improve Performance",
            "Launch Something New",
            "Grow Market Share",
            "Enter a New Market",
        ],
    )

    product = st.text_input(
        "What are we making a decision about?",
        placeholder=strategy_placeholder("product"),
    )

    objective = st.selectbox(
        "What does success look like?",
        [
            "Acquire Customers",
            "Grow Revenue",
            "Increase Adoption / Usage",
            "Improve Retention / Loyalty",
            "Improve Profitability / Efficiency",
            "Build Awareness / Preference",
            "Launch Something New",
            "Increase Market Share",
            "Enter a New Market",
            "Reduce Risk / Uncertainty",
            "Other",
        ],
    )

    custom_objective = objective
    if objective == "Other":
        custom_objective = st.text_input(
            "Describe your objective",
            placeholder=strategy_placeholder("custom_objective", {"product": product}),
        )

    audience = st.text_input(
        "Who matters most to this decision?",
        placeholder=strategy_placeholder("audience", {"product": product, "objective": custom_objective}),
    )

    st.markdown("<div class=\"cl-form-kicker\">THE COMMERCIAL REALITY</div>", unsafe_allow_html=True)
    budget_col, period_col, currency_col = st.columns([2.2, 1.35, 1])
    with budget_col:
        budget_text = st.text_input(
            "What budget are we working with?",
            value="25,000",
            help="Use commas if you like — CampaignLab stores this as a number.",
        )
        cleaned_budget = budget_text.replace(",", "").replace(" ", "").strip()
        try:
            budget = max(0, int(float(cleaned_budget))) if cleaned_budget else 0
        except ValueError:
            budget = 0
            st.caption("Enter the budget as a number, for example 25,000.")
    with period_col:
        budget_period = st.selectbox(
            "For what period?",
            ["Project / launch", "Month", "Quarter", "Year", "Other"],
            help="A $25K launch budget and a $25K annual budget imply very different strategic options.",
        )
    with currency_col:
        currency = st.selectbox(
            "Currency",
            ["USD", "GBP", "EUR", "CAD", "AUD", "PKR", "Other"],
        )

    business_model = st.selectbox(
        "How does this business reach or serve people?",
        [
            "Auto-detect",
            "Direct to consumers",
            "To businesses",
            "Through businesses to consumers",
            "Marketplace / platform",
            "Other",
        ],
        help="Choose the route to customer, not the pricing model. CampaignLab can infer subscription or transaction economics from context when relevant.",
    )

    geography = st.text_input(
        "Where does this decision apply?",
        placeholder=strategy_placeholder("geography", {"product": product, "audience": audience}),
    )

    with st.expander("＋ Give CampaignLab more context (optional)"):
        context = st.text_area(
            "What else could change the decision?",
            placeholder=strategy_placeholder(
                "context",
                {"product": product, "objective": custom_objective, "audience": audience, "geography": geography},
            ),
            height=150,
        )

    return {
        "decision_type": decision_type,
        "product": product,
        "business_model": business_model,
        "audience": audience,
        "objective": custom_objective,
        "budget": budget,
        "_budget_valid": bool(cleaned_budget) and budget >= 0 and cleaned_budget.replace(".", "", 1).isdigit(),
        "budget_period": budget_period,
        "currency": currency,
        "geography": geography,
        "context": context,
        "clarification": "",
        "_objective_selector": objective,
    }


def _run_strategy_analysis(client, current_inputs):
    saved_inputs = {k: v for k, v in current_inputs.items() if not k.startswith("_")}
    reset_strategy_downstream()
    st.session_state.saved_strategy_inputs = saved_inputs

    with st.spinner("CampaignLab is separating facts, inferences, and unknowns..."):
        context_result = check_context(client, saved_inputs)
        st.session_state.context_result = context_result

    if context_result["context_status"] != "critical_missing":
        with st.spinner("CampaignLab is building and challenging the strategy..."):
            st.session_state.strategy_result = generate_strategy(
                client,
                saved_inputs,
                context_result,
            )


def _render_context_result(client):
    context_result = st.session_state.context_result
    if not context_result:
        return

    st.divider()
    status = context_result["context_status"]
    if status == "sufficient":
        st.success("🟢 Context check: strong enough to proceed")
    elif status == "partial":
        st.info("🟡 Context check: enough to proceed, but uncertainty remains")
    else:
        st.warning("🔴 One missing detail could materially change the recommendation.")

    with st.expander("See how CampaignLab read the situation"):
        st.write(context_result["reason"])

        if context_result["confirmed_context"]:
            st.markdown("#### ✓ Confirmed")
            for item in context_result["confirmed_context"]:
                st.markdown(f"- {item}")

        if context_result["reasonable_inferences"]:
            st.markdown("#### 🧠 Reasonable inferences")
            st.caption("Useful deductions, not confirmed facts.")
            for item in context_result["reasonable_inferences"]:
                st.markdown(f"- {item}")

        if context_result["missing_context"]:
            st.markdown("#### ? Still unknown")
            for item in context_result["missing_context"]:
                st.markdown(f"- {item}")

    if status == "critical_missing":
        st.subheader("One thing before I make the call")
        st.markdown(f"**{context_result['clarifying_question']}**")
        clarification = st.text_area("Your answer", key="clarification_input")

        if st.button("Continue Analysis", type="primary"):
            if not clarification.strip():
                st.warning("Give CampaignLab the missing context first.")
                return

            updated_inputs = dict(st.session_state.saved_strategy_inputs)
            updated_inputs["clarification"] = clarification
            st.session_state.saved_strategy_inputs = updated_inputs

            with st.spinner("CampaignLab is reassessing..."):
                new_context_result = check_context(client, updated_inputs)
                st.session_state.context_result = new_context_result

            if new_context_result["context_status"] != "critical_missing":
                with st.spinner("Building the strategy..."):
                    st.session_state.strategy_result = generate_strategy(
                        client,
                        updated_inputs,
                        new_context_result,
                    )
                st.rerun()


def _render_strategy_battle(client, strategy):
    st.divider()
    st.header("⚔️ Strategy Arena")
    st.write(
        "Put the current recommendation against two genuinely different "
        "strategic approaches."
    )

    battle_mode = st.radio(
        "Who should challenge it?",
        ["Find challengers for me", "I have something in mind"],
        key="battle_mode",
    )

    if battle_mode == "I have something in mind":
        user_challenger = st.text_area(
            "What's your challenger?",
            placeholder=followup_placeholder("challenger", strategy),
            key="battle_user_challenger",
        )
    else:
        user_challenger = ""

    st.caption(
        "CampaignLab will compare the original strategy with exactly two "
        "challengers. No fake numeric scoring."
    )

    if st.button("⚔️ Run Strategy Battle", type="primary", use_container_width=True):
        if battle_mode == "I have something in mind" and not user_challenger.strip():
            st.warning("Tell CampaignLab what strategy you want to challenge it with.")
        else:
            with st.spinner("CampaignLab is trying to beat its own recommendation..."):
                st.session_state.strategy_battle_result = generate_strategy_battle(
                    client,
                    st.session_state.saved_strategy_inputs,
                    st.session_state.context_result,
                    strategy,
                    battle_mode,
                    user_challenger,
                )
                st.session_state.strategy_battle_signature = (battle_mode, user_challenger.strip())

    battle = st.session_state.strategy_battle_result
    if not battle:
        return
    if st.session_state.get("strategy_battle_signature") != (battle_mode, user_challenger.strip()):
        st.info("The challenger setup changed after the last battle. Run Strategy Battle again before using the old comparison.")
        return

    st.divider()
    st.caption("THE CONTENDERS")
    original_col, challenger1_col, challenger2_col = st.columns(3)

    with original_col:
        st.markdown("### 🛡️ Original")
        st.markdown(f"**{battle['original']['name']}**")
        st.write(battle["original"]["thesis"])

    with challenger1_col:
        st.markdown("### ⚔️ Challenger 1")
        st.markdown(f"**{battle['challenger_1']['name']}**")
        st.write(battle["challenger_1"]["thesis"])

    with challenger2_col:
        st.markdown("### 🥊 Challenger 2")
        st.markdown(f"**{battle['challenger_2']['name']}**")
        st.write(battle["challenger_2"]["thesis"])

    st.subheader("📋 Decision Scorecard")
    st.caption(
        "Ratings are qualitative CampaignLab judgments based on the available "
        "context. They are not calculated scores."
    )

    table_rows = []
    for criterion in battle["criteria"]:
        table_rows.append(
            {
                "Decision criterion": criterion["criterion"],
                battle["original"]["name"]: rating_icon(criterion["original_rating"]),
                battle["challenger_1"]["name"]: rating_icon(criterion["challenger_1_rating"]),
                battle["challenger_2"]["name"]: rating_icon(criterion["challenger_2_rating"]),
            }
        )

    st.dataframe(table_rows, use_container_width=True, hide_index=True)

    with st.expander("Why CampaignLab scored it this way"):
        for criterion in battle["criteria"]:
            st.markdown(f"**{criterion['criterion']}**")
            st.write(criterion["basis"])

    st.divider()
    st.caption("CAMPAIGNLAB'S CALL")
    st.header(f"🏆 {battle['campaignlab_call']}")
    st.write(battle["why_winner"])

    confidence = battle["confidence"]
    confidence_text = (
        f"Confidence: {confidence}\n\n"
        + battle["confidence_explanation"]
    )
    confidence_tone = {
        "High": "success",
        "Moderate": "info",
        "Low": "warning",
    }.get(confidence, "info")
    render_callout(confidence_text, tone=confidence_tone)

    st.caption(
        "Confidence describes how strongly the available information separates "
        "the strategies. It is not a probability."
    )

    st.subheader("🔄 What Would Flip the Decision?")
    for flip in battle["flip_conditions"]:
        st.markdown(f"- {flip}")

    if battle["decision_caution"]:
        render_callout(battle["decision_caution"], tone="warning")



def _render_red_team(client, strategy):
    st.divider()
    st.header("👿 Devil's Advocate")
    st.write(
        "Try to break the recommendation once, then make a call. "
        "No endless critique loop."
    )

    attack_focus = st.text_area(
        "Anything CampaignLab should attack specifically?",
        placeholder=followup_placeholder("red_team", strategy),
        key="red_team_focus",
    )

    if st.button(
        "😈 Stress-Test Strategy",
        type="primary",
        use_container_width=True,
    ):
        with st.spinner("CampaignLab is trying to break its own recommendation..."):
            st.session_state.red_team_result = generate_red_team(
                client,
                st.session_state.saved_strategy_inputs,
                st.session_state.context_result,
                strategy,
                attack_focus,
            )
            st.session_state.red_team_signature = attack_focus.strip()

    red_team = st.session_state.red_team_result
    if not red_team:
        return
    if st.session_state.get("red_team_signature") != attack_focus.strip():
        st.info("The attack focus changed after the last stress test. Run it again before using the old verdict.")
        return

    st.divider()
    st.caption("ADVERSARIAL CHECK")

    danger_col, underestimate_col = st.columns(2)

    with danger_col:
        st.subheader("👁️ BLIND SPOT DETECTED")
        render_callout(
            red_team["most_dangerous_assumption"],
            tone="warning",
        )

    with underestimate_col:
        st.subheader("🫥 What We May Be Underestimating")
        render_callout(
            red_team["what_we_are_underestimating"],
            tone="info",
        )

    st.subheader("🧨 Likely Failure Modes")
    for failure_mode in red_team["failure_modes"]:
        st.markdown(f"- {failure_mode}")

    st.subheader("🔎 What Evidence Would Prove Us Wrong?")
    for evidence in red_team["contrary_evidence_needed"]:
        st.markdown(f"- {evidence}")

    st.subheader("🧪 Cheapest Next Check")
    render_callout(
        red_team["cheapest_next_check"],
        tone="success",
    )

    st.divider()
    st.caption("DEVIL'S ADVOCATE VERDICT")

    verdict = red_team["verdict"]
    verdict_icon = {
        "Survives": "🟢",
        "Survives with caution": "🟡",
        "Rethink": "🔴",
    }.get(verdict, "⚪")

    st.header(f"{verdict_icon} {verdict}")
    render_callout(
        red_team["verdict_reason"],
        tone={
            "Survives": "success",
            "Survives with caution": "warning",
            "Rethink": "warning",
        }.get(verdict, "info"),
    )

    st.caption(
        "This is a bounded stress test. CampaignLab is not automatically "
        "rewriting the strategy or starting another critique cycle."
    )


def _sanitize_numeric_lever(lever):
    minimum = float(lever.get("numeric_min", 0))
    maximum = float(lever.get("numeric_max", 0))
    current = float(lever.get("numeric_current", 0))
    step = float(lever.get("numeric_step", 0))

    if maximum <= minimum:
        maximum = minimum + 1.0
    current = max(minimum, min(maximum, current))
    if step <= 0:
        step = max((maximum - minimum) / 10.0, 0.01)
    step = min(step, maximum - minimum)
    return minimum, maximum, current, step


def _render_scenario_lab(client, strategy):
    st.divider()
    st.header("🔮 Scenario Lab")
    st.write("Change the reality. See whether CampaignLab's call survives.")
    st.caption(
        "CampaignLab suggests the pressure points most capable of changing "
        "this decision. You choose which ones to manipulate."
    )

    if not st.session_state.scenario_setup_result:
        if st.button("✨ Find pressure points", type="primary", use_container_width=True):
            with st.spinner("CampaignLab is finding the variables most capable of changing the call..."):
                reset_scenario_state()
                st.session_state.scenario_setup_result = generate_scenario_setup(
                    client,
                    st.session_state.saved_strategy_inputs,
                    st.session_state.context_result,
                    strategy,
                )
            st.rerun()
        return

    setup = st.session_state.scenario_setup_result
    st.subheader("Pressure points")
    st.write(setup["setup_summary"])

    selected_changes = []
    for index, lever in enumerate(setup["levers"]):
        st.markdown(f"#### {lever['name']}")
        st.caption(lever["why_it_matters"])
        active = st.checkbox(f"Change {lever['name']}", key=f"scenario_active_{index}")

        if lever["control_type"] == "numeric":
            minimum, maximum, current, step = _sanitize_numeric_lever(lever)
            value = st.slider(
                f"{lever['name']} scenario",
                min_value=minimum,
                max_value=maximum,
                value=current,
                step=step,
                key=f"scenario_numeric_{index}",
                disabled=not active,
            )
            current_label = lever.get("current_label", "")
            unit = lever.get("unit", "")
            if current_label:
                st.caption(f"Current reality: {current_label}")
            if active:
                selected_changes.append({
                    "variable": lever["name"],
                    "control_type": "numeric",
                    "scenario_value": value,
                    "unit": unit,
                    "original_context": current_label,
                })
        else:
            options = lever.get("options") or ["Unknown", "Limited", "Strong"]
            default_option = lever.get("default_option")
            default_index = options.index(default_option) if default_option in options else 0
            value = st.selectbox(
                f"{lever['name']} scenario",
                options,
                index=default_index,
                key=f"scenario_category_{index}",
                disabled=not active,
            )
            current_label = lever.get("current_label", "")
            if current_label:
                st.caption(f"Current reality: {current_label}")
            if active:
                selected_changes.append({
                    "variable": lever["name"],
                    "control_type": "categorical",
                    "scenario_value": value,
                    "original_context": current_label,
                })
        st.divider()

    custom_change = st.text_area(
        "Add another change",
        placeholder=followup_placeholder("scenario", strategy),
        key="scenario_custom_change",
    )

    run_col, reset_col = st.columns([3, 1])
    with run_col:
        run_scenario = st.button("🔮 Run Scenario", type="primary", use_container_width=True)
    with reset_col:
        if st.button("Reset pressure points", use_container_width=True):
            reset_scenario_state()
            st.rerun()

    scenario_signature = json.dumps({"changes": selected_changes, "custom": custom_change.strip()}, sort_keys=True, default=str)
    if run_scenario:
        if not selected_changes and not custom_change.strip():
            st.warning("Change at least one pressure point or describe another scenario change.")
        else:
            with st.spinner("CampaignLab is checking whether the decision survives..."):
                st.session_state.scenario_result = evaluate_scenario(
                    client,
                    st.session_state.saved_strategy_inputs,
                    st.session_state.context_result,
                    strategy,
                    selected_changes,
                    custom_change,
                )
                st.session_state.scenario_input_signature = scenario_signature

    result = st.session_state.scenario_result
    if not result:
        return
    if st.session_state.get("scenario_input_signature") != scenario_signature:
        st.info("The scenario changed after the last run. Run Scenario again before CampaignLab shows the old call under new assumptions.")
        return

    st.divider()
    st.caption("SCENARIO RESULT")
    if result["status"] == "strategy_holds":
        st.header("🟢 STRATEGY HOLDS")
        st.success("This strategy survives the new reality.")
        result_tone = "success"
    else:
        st.header("⚠️ DECISION CHANGED")
        st.warning("Under these conditions, CampaignLab changes its call.")
        result_tone = "warning"

    st.subheader(result["headline"])
    render_callout(result["resulting_call"], tone=result_tone)

    what_col, why_col = st.columns(2)
    with what_col:
        st.markdown("#### What changed")
        st.write(result["what_changed"])
    with why_col:
        st.markdown("#### Why it matters")
        st.write(result["why_it_matters"])

    st.markdown("#### Dominant variable")
    st.write(result["dominant_variable"])
    st.markdown(f"#### Confidence: {result['confidence']}")
    st.write(result["confidence_explanation"])
    st.caption(
        "Confidence describes how strongly the available information separates "
        "the decisions. It is not a probability."
    )
    st.markdown("#### What could reverse this result?")
    st.write(result["reversal_condition"])
    st.caption(
        "Scenario Lab does not automatically replace the working strategy. "
        "It shows whether CampaignLab would change its call under this reality."
    )

def _render_followups(client, strategy):
    st.divider()
    st.subheader("Go deeper")
    st.caption(
        "Compare the call, attack it, change the reality, or investigate the uncertainty with evidence."
    )
    follow1, follow2, follow3, follow4 = st.columns(4)

    with follow1:
        if st.button("⚔️ Compare Strategies", use_container_width=True):
            st.session_state.strategy_followup = "compare"
    with follow2:
        if st.button("👿 Devil's Advocate", use_container_width=True):
            st.session_state.strategy_followup = "challenge"
    with follow3:
        if st.button("🔬 Investigate with Evidence", use_container_width=True):
            st.session_state.strategy_followup = "experiment"
    with follow4:
        if st.button("🔮 Scenario Lab", use_container_width=True):
            st.session_state.strategy_followup = "scenario"

    followup = st.session_state.strategy_followup
    if followup == "compare":
        _render_strategy_battle(client, strategy)
    elif followup == "challenge":
        _render_red_team(client, strategy)
    elif followup == "experiment":
        st.divider()
        st.header("🔬 Investigate with Evidence")
        st.write(
            "Carry the current strategy, assumptions, risks, and uncertainty "
            "into Evidence Lab without starting over."
        )
        render_callout(strategy["suggested_experiment"], tone="success")
        if st.button("🔬 Send to Evidence Lab", type="primary", use_container_width=True):
            prepare_experiment_handoff(
                strategy,
                st.session_state.saved_strategy_inputs,
                st.session_state.context_result,
            )
            st.query_params["page"] = "evidence"
            st.rerun()
    elif followup == "scenario":
        _render_scenario_lab(client, strategy)

def _render_strategy_result(client):
    strategy = st.session_state.strategy_result
    if not strategy:
        return

    st.divider()
    st.caption("CAMPAIGNLAB'S CALL")
    st.header(strategy["strategy_name"])

    st.subheader("🎯 The Move")
    render_callout(strategy["recommendation"], tone="info")

    st.subheader("🏆 Why It Wins")
    st.write(strategy["why_it_wins"])

    assumption_col, risk_col = st.columns(2)
    with assumption_col:
        st.subheader("⚠️ Key Assumptions")
        for assumption in strategy["key_assumptions"]:
            st.markdown(f"- {assumption}")

    with risk_col:
        st.subheader("🔥 Risks")
        for risk in strategy["risks"]:
            st.markdown(f"- {risk}")

    st.subheader("👿 Devil's Advocate")
    render_callout(strategy["devils_advocate"], tone="warning")

    st.subheader("🔬 What Would Reduce the Uncertainty")
    render_callout(strategy["suggested_experiment"], tone="success")

    _render_followups(client, strategy)


def render_strategy_lab(client):
    st.markdown(
        f"""<section class="cl-lab-hero strategy">
        {lab_mark("strategy", "lg")}
        <div class="cl-lab-hero-copy"><div class="cl-lab-kicker">STRATEGY LAB</div>
        <h1>Turn a messy decision into a strategy you can defend.</h1>
        <p>Bring the situation. CampaignLab finds the strategic options, separates facts from assumptions, challenges the obvious answer, and shows you the strongest path forward.</p></div>
        </section>""",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="cl-brief-title"><h3>Tell me what we are solving</h3><span>Give CampaignLab the useful context. Skip the corporate intake-form nonsense.</span></div>',
        unsafe_allow_html=True,
    )

    current_inputs = _collect_strategy_inputs()
    st.markdown(
        '<div class="cl-action-strip"><b>That is enough to start thinking.</b><span>CampaignLab will read the context, surface what matters, challenge the assumptions, and build the strongest strategy available.</span></div>',
        unsafe_allow_html=True,
    )

    if st.button("✦ Build my strategy", type="primary", use_container_width=True):
        if not current_inputs["product"].strip():
            st.warning("Tell CampaignLab what we are making a decision about.")
        elif (
            current_inputs["_objective_selector"] == "Other"
            and not current_inputs["objective"].strip()
        ):
            st.warning("Describe the objective before running Strategy Lab.")
        elif not current_inputs.get("_budget_valid", True):
            st.warning("Enter the budget as a number before CampaignLab builds the strategy.")
        else:
            _run_strategy_analysis(client, current_inputs)

    submitted_inputs = {k: v for k, v in current_inputs.items() if not k.startswith("_")}
    saved_inputs = st.session_state.get("saved_strategy_inputs")
    if saved_inputs and submitted_inputs != saved_inputs and (st.session_state.get("context_result") or st.session_state.get("strategy_result")):
        st.info("The strategy inputs changed after the last run. Build the strategy again before CampaignLab shows the old recommendation under new context.")
        return

    _render_context_result(client)
    _render_strategy_result(client)