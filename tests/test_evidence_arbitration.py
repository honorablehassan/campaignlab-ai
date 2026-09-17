import jsonschema

from engines.decision_kernel import decision_from_evidence
from engines.evidence_arbitration import arbitrate_evidence
from schemas.evidence_arbitration import EVIDENCE_ARBITRATION_SCHEMA


def _result(method, direction, verdict, estimand="Treatment effect", *, check="pass"):
    return {
        "method_id": method,
        "estimand": estimand,
        "estimate": {"direction": direction},
        "uncertainty": {"low": .01, "high": .04},
        "decision": {"verdict": verdict},
        "integrity_checks": [{"name": "integrity", "status": check, "detail": check}],
        "warnings": [],
    }


def test_randomized_evidence_outranks_observational_when_they_conflict():
    arbitration = arbitrate_evidence([
        _result("fit_linear_regression", "positive", "SHIP"),
        _result("analyze_binary_ab", "negative", "DON'T SHIP"),
    ])
    jsonschema.validate(arbitration, EVIDENCE_ARBITRATION_SCHEMA)
    assert arbitration["status"] == "conflict"
    assert arbitration["dominant_method"] == "analyze_binary_ab"
    assert arbitration["resolved_verdict"] == "DON'T SHIP"
    assert arbitration["confidence_adjustment"] < 0


def test_failed_integrity_can_demote_nominally_stronger_evidence():
    arbitration = arbitrate_evidence([
        _result("analyze_binary_ab", "positive", "SHIP", check="fail"),
        _result("run_difference_in_differences", "positive", "SHIP"),
    ])
    assert arbitration["dominant_method"] == "run_difference_in_differences"


def test_different_estimands_are_directional_not_numerical_confirmation():
    arbitration = arbitrate_evidence([
        _result("analyze_binary_ab", "positive", "SHIP", estimand="Conversion-rate effect"),
        _result("run_difference_in_differences", "positive", "SHIP", estimand="Revenue effect"),
    ])
    assert arbitration["status"] == "directional_agreement"
    assert arbitration["comparability_warnings"]


def test_empty_arbitration_refuses_to_invent_evidence():
    arbitration = arbitrate_evidence([])
    jsonschema.validate(arbitration, EVIDENCE_ARBITRATION_SCHEMA)
    assert arbitration["status"] == "insufficient"
    assert arbitration["dominant_method"] is None


def test_conflict_is_visible_in_canonical_decision_and_lowers_confidence():
    dominant = _result("analyze_binary_ab", "negative", "DON'T SHIP")
    arbitration = arbitrate_evidence([
        _result("fit_linear_regression", "positive", "SHIP"),
        dominant,
    ])
    decision = decision_from_evidence(
        question="Should we launch?",
        analytical_result=dominant,
        arbitration=arbitration,
    )
    assert decision["disposition"] == "hold"
    assert any(item["source"] == "Evidence Arbitration" for item in decision["contradicting_evidence"])
    assert "evidence arbitration" in decision["provenance"]["methods"]
