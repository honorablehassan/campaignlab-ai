"""Contract for deterministic arbitration across multiple evidence results."""

EVIDENCE_ARBITRATION_VERSION = "1.0"

EVIDENCE_ARBITRATION_SCHEMA = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "status": {
            "type": "string",
            "enum": ["insufficient", "agreement", "directional_agreement", "conflict", "not_comparable"],
        },
        "dominant_method": {"type": ["string", "null"]},
        "resolved_verdict": {"type": "string"},
        "confidence_adjustment": {"type": "integer", "minimum": -40, "maximum": 15},
        "reason": {"type": "string"},
        "ranked_evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "method_id": {"type": "string"},
                    "identification": {"type": "string"},
                    "score": {"type": "integer"},
                    "verdict": {"type": "string"},
                    "direction": {"type": "string"},
                    "estimand": {"type": "string"},
                    "warnings": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["method_id", "identification", "score", "verdict", "direction", "estimand", "warnings"],
                "additionalProperties": False,
            },
        },
        "conflicts": {"type": "array", "items": {"type": "string"}},
        "comparability_warnings": {"type": "array", "items": {"type": "string"}},
        "next_evidence": {"type": "string"},
    },
    "required": [
        "version", "status", "dominant_method", "resolved_verdict",
        "confidence_adjustment", "reason", "ranked_evidence", "conflicts",
        "comparability_warnings", "next_evidence",
    ],
    "additionalProperties": False,
}
