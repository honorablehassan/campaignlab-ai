from copy import deepcopy

import pytest

from core.decision_memory import export_memory, remember_decision, update_memory_outcome
from engines.decision_kernel import decision_from_mmm, decision_from_strategy
from schemas.decision import DECISION_OBJECT_SCHEMA


def _strategy_inputs():
    return {"product": "a new retention offer", "objective": "Improve Retention"}


def _strategy():
    return {
        "strategy_name": "Earn the second month",
        "recommendation": "Target the first renewal moment with a value reminder.",
        "why_it_wins": "It intervenes at the decision point closest to preventable churn.",
        "key_assumptions": ["Early churn is addressable."],
        "risks": ["The offer may subsidize customers who would stay anyway."],
        "devils_advocate": "Product dissatisfaction may be the true cause.",
        "suggested_experiment": "Randomize the reminder among eligible customers.",
    }


def _context(status="sufficient"):
    return {
        "context_status": status,
        "confirmed_context": ["Renewal happens monthly."],
        "reasonable_inferences": ["The first renewal is a leverage point."],
        "missing_context": ["Reason-specific churn data is unavailable."],
    }


def test_decision_schema_is_closed_and_complete():
    assert DECISION_OBJECT_SCHEMA["additionalProperties"] is False
    assert set(DECISION_OBJECT_SCHEMA["required"]) == set(DECISION_OBJECT_SCHEMA["properties"])


def test_strategy_decision_converges_on_one_call():
    decision = decision_from_strategy(_strategy(), _context(), _strategy_inputs())
    assert decision["source"] == "Strategy Lab"
    assert decision["call"] == _strategy()["recommendation"]
    assert decision["confidence"]["label"] == "Moderate"
    assert decision["value_of_information"]["worth_resolving"] is True
    assert decision["flip_conditions"] == []
    assert decision["provenance"]["deterministic"] is False


def test_strategy_confidence_falls_when_red_team_breaks_it():
    base = decision_from_strategy(_strategy(), _context(), _strategy_inputs())
    attacked = decision_from_strategy(
        _strategy(),
        _context(),
        _strategy_inputs(),
        red_team={
            "verdict": "Rethink",
            "most_dangerous_assumption": "The churn mechanism is unverified.",
            "contrary_evidence_needed": ["No effect in a randomized holdout."],
        },
    )
    assert attacked["confidence"]["score"] < base["confidence"]["score"]
    assert attacked["contradicting_evidence"][-1]["source"] == "Devil's Advocate"
    assert attacked["flip_conditions"] == ["No effect in a randomized holdout."]


@pytest.mark.parametrize(
    "strength,expected_disposition",
    [("Limited", "hold"), ("Limited-to-moderate", "act_with_guardrails"), ("Moderate", "act_with_guardrails")],
)
def test_mmm_decision_never_turns_observational_fit_into_high_confidence(strength, expected_disposition):
    result = {
        "model": {"evidence_strength": strength, "media_holdout_improvement": 0.12},
        "warning": "Observational evidence does not establish causality.",
    }
    decision = decision_from_mmm(
        move="Shift a small amount from TV to paid search.",
        outcome="revenue",
        model_result=result,
        readiness_status="ready",
        gain_pct=0.05,
        next_check="Run a geo holdout.",
        caveat="Omitted demand drivers could change the result.",
    )
    assert decision["confidence"]["label"] != "High"
    assert decision["disposition"] == expected_disposition
    assert decision["provenance"]["deterministic"] is True


def test_memory_is_bounded_deduplicated_and_exportable():
    state = {}
    decision = decision_from_strategy(_strategy(), _context(), _strategy_inputs())
    remember_decision(state, decision, limit=2)
    changed = deepcopy(decision)
    changed["confidence"]["score"] = 40
    remember_decision(state, changed, limit=2)
    assert len(state["decision_memory"]) == 1
    assert state["decision_memory"][0]["confidence"]["score"] == 40
    updated = update_memory_outcome(state, decision["decision_id"], status="observed", actual_outcome="Retention rose by two points.")
    assert updated["outcome_status"] == "observed"
    assert b"Retention rose by two points" in export_memory(state)
    assert b'"version": "2.0"' in export_memory(state)


def test_memory_rejects_unknown_status_and_missing_decision():
    state = {}
    with pytest.raises(ValueError):
        update_memory_outcome(state, "missing", status="invented")
    with pytest.raises(KeyError):
        update_memory_outcome(state, "missing", status="observed")
