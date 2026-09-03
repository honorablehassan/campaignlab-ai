import streamlit as st

DEFAULT_STATE = {
    "strategy_result": None,
    "strategy_followup": None,
    "context_result": None,
    "saved_strategy_inputs": None,
    "strategy_battle_result": None,
    "strategy_battle_signature": None,
    "battle_mode": "Find challengers for me",
    "battle_user_challenger": "",
    "red_team_result": None,
    "red_team_signature": None,
    "red_team_focus": "",
    "scenario_setup_result": None,
    "scenario_result": None,
    "scenario_input_signature": None,
    "scenario_custom_change": "",
    "experiment_handoff": None,
    "experiment_decision_input": "",
    "experiment_outcome_input": "",
    "experiment_known_input": "",
    "experiment_constraints_input": "",
    "directory_method_interest": None,
}


def initialize_state():
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _clear_prefixed_state(prefixes):
    for key in list(st.session_state.keys()):
        if any(key.startswith(prefix) for prefix in prefixes):
            del st.session_state[key]


def reset_scenario_state():
    st.session_state.scenario_setup_result = None
    st.session_state.scenario_result = None
    st.session_state.scenario_input_signature = None
    st.session_state.scenario_custom_change = ""
    _clear_prefixed_state(("scenario_active_", "scenario_numeric_", "scenario_category_"))


def reset_strategy_downstream():
    """Clear outputs that depend on a newly submitted Strategy Lab input set."""
    st.session_state.strategy_result = None
    st.session_state.context_result = None
    st.session_state.strategy_followup = None
    st.session_state.strategy_battle_result = None
    st.session_state.strategy_battle_signature = None
    st.session_state.battle_mode = "Find challengers for me"
    st.session_state.battle_user_challenger = ""
    st.session_state.red_team_result = None
    st.session_state.red_team_signature = None
    st.session_state.red_team_focus = ""
    reset_scenario_state()
    st.session_state.experiment_handoff = None


def prepare_experiment_handoff(strategy, inputs, context_result):
    assumptions = strategy.get("key_assumptions", [])
    risks = strategy.get("risks", [])
    unknowns = context_result.get("missing_context", [])

    decision = (
        f"Should '{strategy['strategy_name']}' remain the working strategy, "
        "or does its key uncertainty materially weaken the case?"
    )

    known_parts = [
        f"Current strategy: {strategy['strategy_name']}",
        f"Why CampaignLab prefers it: {strategy['why_it_wins']}",
    ]
    if assumptions:
        known_parts.append("Key assumptions: " + "; ".join(assumptions[:4]))
    if risks:
        known_parts.append("Key risks: " + "; ".join(risks[:4]))
    if unknowns:
        known_parts.append("Important unknowns: " + "; ".join(unknowns[:4]))

    constraints = (
        f"Budget: {inputs['budget']} {inputs['currency']} · {inputs.get('budget_period', 'Period not specified')}. "
        f"Geography: {inputs['geography'] or 'Not specified'}. "
        f"Audience: {inputs['audience'] or 'Not specified'}."
    )

    handoff = {
        "source": "Strategy Lab",
        "strategy_name": strategy["strategy_name"],
        "objective": inputs["objective"],
        "audience": inputs["audience"],
        "budget": inputs["budget"],
        "budget_period": inputs.get("budget_period", "Period not specified"),
        "currency": inputs["currency"],
        "assumptions": assumptions,
        "risks": risks,
        "unknowns": unknowns,
        "suggested_experiment": strategy["suggested_experiment"],
        "decision": decision,
        "primary_outcome": "",
        "known_context": "\n\n".join(known_parts),
        "constraints": constraints,
    }

    st.session_state.experiment_handoff = handoff
    st.session_state.experiment_decision_input = handoff["decision"]
    st.session_state.experiment_outcome_input = handoff["primary_outcome"]
    st.session_state.experiment_known_input = handoff["known_context"]
    st.session_state.experiment_constraints_input = handoff["constraints"]
    # Set the actual widget keys so a returning Evidence Lab user never sees stale form values.
    st.session_state.evidence_design_question = handoff["decision"]
    st.session_state.evidence_design_outcome = handoff["primary_outcome"]
    st.session_state.evidence_design_constraints = handoff["constraints"]
    st.session_state.pop("evidence_plan", None)
    st.session_state.pop("evidence_design_result", None)
    st.session_state.evidence_route = "🧪 I need to create evidence"
    return handoff


def prepare_mmm_handoff(*, move: str, outcome: str, confidence: str, caveat: str, best_next_evidence: str, budget_period: str = "Per-period allocation scenario"):
    """Carry an MMM uncertainty into Evidence Lab without pretending the model settled causality."""
    question = (
        f"Would the proposed MMM budget decision actually improve {outcome or 'the business outcome'} enough to justify acting on it?"
    )
    handoff = {
        "source": "Marketing Mix Model",
        "strategy_name": "MMM budget decision",
        "objective": outcome or "Validate the budget decision",
        "audience": "",
        "budget": "Not carried from MMM",
        "budget_period": budget_period,
        "currency": "",
        "assumptions": ["The MMM is observational and cannot eliminate every alternative explanation."],
        "risks": [caveat] if caveat else [],
        "unknowns": [],
        "suggested_experiment": best_next_evidence,
        "decision": question,
        "primary_outcome": outcome or "",
        "known_context": f"MMM working decision: {move}\n\nConfidence: {confidence}",
        "constraints": caveat or "Validate the recommendation without overstating causality.",
    }
    st.session_state.experiment_handoff = handoff
    st.session_state.experiment_decision_input = question
    st.session_state.experiment_outcome_input = outcome or ""
    st.session_state.experiment_known_input = handoff["known_context"]
    st.session_state.experiment_constraints_input = handoff["constraints"]
    st.session_state.evidence_design_question = question
    st.session_state.evidence_design_outcome = outcome or ""
    st.session_state.evidence_design_constraints = handoff["constraints"]
    st.session_state.pop("evidence_plan", None)
    st.session_state.pop("evidence_design_result", None)
    st.session_state.evidence_route = "🧪 I need to create evidence"
    return handoff
