"""Canonical contract for every CampaignLab decision.

The JSON schema is intentionally dependency-free so the same contract can be
used by deterministic engines, AI engines, exports, and a future database.
"""

DECISION_OBJECT_VERSION = "1.0"

EVIDENCE_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "statement": {"type": "string"},
        "source": {"type": "string"},
        "kind": {
            "type": "string",
            "enum": ["calculated", "observed", "user_context", "inference", "model_diagnostic"],
        },
        "strength": {"type": "string", "enum": ["weak", "moderate", "strong"]},
    },
    "required": ["statement", "source", "kind", "strength"],
    "additionalProperties": False,
}

DECISION_OBJECT_SCHEMA = {
    "type": "object",
    "properties": {
        "decision_id": {"type": "string"},
        "version": {"type": "string"},
        "created_at": {"type": "string"},
        "source": {"type": "string"},
        "question": {"type": "string"},
        "call": {"type": "string"},
        "disposition": {
            "type": "string",
            "enum": ["act", "act_with_guardrails", "hold", "investigate"],
        },
        "confidence": {
            "type": "object",
            "properties": {
                "label": {"type": "string", "enum": ["Low", "Cautious", "Moderate", "High"]},
                "score": {"type": "integer", "minimum": 0, "maximum": 100},
                "basis": {"type": "string"},
            },
            "required": ["label", "score", "basis"],
            "additionalProperties": False,
        },
        "supporting_evidence": {"type": "array", "items": EVIDENCE_ITEM_SCHEMA},
        "contradicting_evidence": {"type": "array", "items": EVIDENCE_ITEM_SCHEMA},
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "alternatives_considered": {"type": "array", "items": {"type": "string"}},
        "critical_uncertainties": {"type": "array", "items": {"type": "string"}},
        "value_of_information": {
            "type": "object",
            "properties": {
                "worth_resolving": {"type": "boolean"},
                "reason": {"type": "string"},
                "smallest_next_check": {"type": "string"},
            },
            "required": ["worth_resolving", "reason", "smallest_next_check"],
            "additionalProperties": False,
        },
        "flip_conditions": {"type": "array", "items": {"type": "string"}},
        "next_action": {"type": "string"},
        "predicted_outcome": {"type": "string"},
        "prediction": {
            "type": "object",
            "properties": {
                "metric": {"type": "string"},
                "direction": {"type": "string", "enum": ["increase", "decrease", "no_change", "unknown"]},
                "point": {"type": ["number", "null"]},
                "low": {"type": ["number", "null"]},
                "high": {"type": ["number", "null"]},
                "unit": {"type": "string"},
            },
            "required": ["metric", "direction", "point", "low", "high", "unit"],
            "additionalProperties": False,
        },
        "outcome_status": {
            "type": "string",
            "enum": ["not_tracked", "planned", "acted", "observed"],
        },
        "actual_outcome": {"type": "string"},
        "provenance": {
            "type": "object",
            "properties": {
                "deterministic": {"type": "boolean"},
                "methods": {"type": "array", "items": {"type": "string"}},
                "warnings": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["deterministic", "methods", "warnings"],
            "additionalProperties": False,
        },
    },
    "required": [
        "decision_id", "version", "created_at", "source", "question", "call",
        "disposition", "confidence", "supporting_evidence", "contradicting_evidence",
        "assumptions", "alternatives_considered", "critical_uncertainties",
        "value_of_information", "flip_conditions", "next_action", "predicted_outcome", "prediction",
        "outcome_status", "actual_outcome", "provenance",
    ],
    "additionalProperties": False,
}
