import jsonschema

from core.outcome_learning import calibration_summary, observe_outcome
from engines.decision_kernel import decision_from_mmm
from schemas.outcome import OUTCOME_OBSERVATION_SCHEMA


def _mmm_decision(gain=.06):
    return decision_from_mmm(
        move="Shift budget toward Search.",
        outcome="revenue",
        model_result={"model": {"evidence_strength": "Moderate", "media_holdout_improvement": .12}},
        readiness_status="ready",
        gain_pct=gain,
        next_check="Run a geo test.",
        caveat="Unmeasured demand could change the result.",
    )


def test_observation_scores_direction_and_error_without_rewriting_history():
    decision = _mmm_decision(.06)
    observation = observe_outcome(decision, actual_value=.04, notes="Four-week result")
    jsonschema.validate(observation, OUTCOME_OBSERVATION_SCHEMA)
    assert observation["score"]["direction_correct"] is True
    assert abs(observation["score"]["error"] + .02) < 1e-12
    assert decision["prediction"]["point"] == .06


def test_wrong_direction_is_visible():
    observation = observe_outcome(_mmm_decision(.06), actual_value=-.01)
    assert observation["score"]["direction_correct"] is False
    assert "against" in observation["score"]["label"]


def test_calibration_refuses_to_overinterpret_tiny_history():
    observations = [
        observe_outcome(_mmm_decision(.06), actual_value=.04),
        observe_outcome(_mmm_decision(.03), actual_value=-.01),
    ]
    summary = calibration_summary(observations)
    assert summary["direction_accuracy"] == .5
    assert summary["enough_for_pattern"] is False
    assert "Fewer than 10" in summary["warning"]
