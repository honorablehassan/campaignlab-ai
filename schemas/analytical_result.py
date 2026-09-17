"""Closed contract shared by CampaignLab's deterministic analytical methods."""

ANALYTICAL_RESULT_VERSION = "1.0"

ANALYTICAL_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "method_id": {"type": "string"},
        "question": {"type": "string"},
        "status": {"type": "string", "enum": ["complete", "blocked"]},
        "estimand": {"type": "string"},
        "estimate": {
            "type": "object",
            "properties": {
                "value": {"type": ["number", "null"]},
                "unit": {"type": "string"},
                "direction": {"type": "string", "enum": ["positive", "negative", "neutral", "unknown"]},
            },
            "required": ["value", "unit", "direction"],
            "additionalProperties": False,
        },
        "uncertainty": {
            "type": "object",
            "properties": {
                "kind": {"type": "string"},
                "level": {"type": ["number", "null"]},
                "low": {"type": ["number", "null"]},
                "high": {"type": ["number", "null"]},
            },
            "required": ["kind", "level", "low", "high"],
            "additionalProperties": False,
        },
        "decision": {
            "type": "object",
            "properties": {
                "verdict": {"type": "string"},
                "business_threshold": {"type": ["number", "null"]},
                "reason": {"type": "string"},
            },
            "required": ["verdict", "business_threshold", "reason"],
            "additionalProperties": False,
        },
        "integrity_checks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "status": {"type": "string", "enum": ["pass", "warning", "fail", "not_available"]},
                    "detail": {"type": "string"},
                },
                "required": ["name", "status", "detail"],
                "additionalProperties": False,
            },
        },
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "warnings": {"type": "array", "items": {"type": "string"}},
        "provenance": {
            "type": "object",
            "properties": {
                "deterministic": {"type": "boolean"},
                "engine": {"type": "string"},
                "raw_result_preserved": {"type": "boolean"},
            },
            "required": ["deterministic", "engine", "raw_result_preserved"],
            "additionalProperties": False,
        },
    },
    "required": [
        "version", "method_id", "question", "status", "estimand", "estimate",
        "uncertainty", "decision", "integrity_checks", "assumptions", "warnings", "provenance",
    ],
    "additionalProperties": False,
}
