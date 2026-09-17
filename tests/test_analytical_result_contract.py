import jsonschema
import json
from types import SimpleNamespace

from analytics.ab_binary import analyze_binary_ab
from analytics.result_contract import analytical_result
from analytics.tool_runtime import EvidenceToolRuntime
from engines.decision_kernel import decision_from_evidence
from engines.evidence_orchestrator import run_evidence_orchestrator
from schemas.analytical_result import ANALYTICAL_RESULT_SCHEMA
from schemas.decision import DECISION_OBJECT_SCHEMA


def test_binary_result_normalizes_to_closed_contract():
    raw = analyze_binary_ab(10_000, 500, 10_000, 560, business_threshold=.0025).to_dict()
    envelope = analytical_result("analyze_binary_ab", raw, question="Should treatment replace control?")
    jsonschema.validate(envelope, ANALYTICAL_RESULT_SCHEMA)
    assert envelope["estimand"] == "Treatment-minus-control conversion-rate difference"
    assert envelope["estimate"]["value"] == raw["absolute_lift"]
    assert envelope["provenance"]["raw_result_preserved"] is True


def test_runtime_adds_envelope_without_removing_raw_result():
    runtime = EvidenceToolRuntime()
    output = runtime.execute("analyze_binary_ab", {
        "control_n": 10_000,
        "control_conversions": 500,
        "treatment_n": 10_000,
        "treatment_conversions": 560,
        "expected_treatment_share": .5,
        "business_threshold": .0025,
    })
    assert "absolute_lift" in output
    jsonschema.validate(output["_analytical_result"], ANALYTICAL_RESULT_SCHEMA)


def test_evidence_decision_is_derived_from_envelope_and_validates():
    raw = analyze_binary_ab(10_000, 500, 10_000, 560, business_threshold=.0025).to_dict()
    envelope = analytical_result("analyze_binary_ab", raw)
    decision = decision_from_evidence(
        question="Should treatment replace control?",
        analytical_result=envelope,
    )
    jsonschema.validate(decision, DECISION_OBJECT_SCHEMA)
    assert decision["source"] == "Evidence Lab"
    assert decision["disposition"] == "hold"
    assert decision["provenance"]["deterministic"] is True


def test_plan_without_execution_never_pretends_to_be_a_call():
    decision = decision_from_evidence(
        question="Which channel caused revenue growth?",
        analytical_result=None,
        next_action="Run a credible incrementality design.",
    )
    jsonschema.validate(decision, DECISION_OBJECT_SCHEMA)
    assert decision["disposition"] == "investigate"
    assert decision["confidence"]["label"] == "Low"
    assert "plan" in decision["provenance"]["warnings"][0].lower()


def test_orchestrator_trace_carries_the_analytical_envelope():
    call = SimpleNamespace(
        type="function_call",
        name="analyze_binary_ab",
        call_id="call_1",
        arguments=json.dumps({
            "control_n": 10_000,
            "control_conversions": 500,
            "treatment_n": 10_000,
            "treatment_conversions": 560,
            "expected_treatment_share": .5,
            "business_threshold": .0025,
        }),
    )
    responses = iter([
        SimpleNamespace(output=[call], output_text="", id="response_1", usage=None),
        SimpleNamespace(output=[], output_text="CampaignLab's Call", id="response_2", usage=None),
    ])

    class FakeResponses:
        def create(self, **_kwargs):
            return next(responses)

    client = SimpleNamespace(responses=FakeResponses())
    result = run_evidence_orchestrator(client, "Should treatment replace control?", EvidenceToolRuntime())
    assert result.traces[0].analytical_result is not None
    jsonschema.validate(result.traces[0].analytical_result, ANALYTICAL_RESULT_SCHEMA)
