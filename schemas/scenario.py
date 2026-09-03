SCENARIO_SETUP_SCHEMA = {
    "type": "object",
    "properties": {
        "setup_summary": {"type": "string"},
        "levers": {
            "type": "array",
            "minItems": 2,
            "maxItems": 4,
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "why_it_matters": {"type": "string"},
                    "control_type": {"type": "string", "enum": ["numeric", "categorical"]},
                    "current_label": {"type": "string"},
                    "numeric_current": {"type": "number"},
                    "numeric_min": {"type": "number"},
                    "numeric_max": {"type": "number"},
                    "numeric_step": {"type": "number"},
                    "unit": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                    "default_option": {"type": "string"}
                },
                "required": [
                    "name", "why_it_matters", "control_type", "current_label",
                    "numeric_current", "numeric_min", "numeric_max", "numeric_step",
                    "unit", "options", "default_option"
                ],
                "additionalProperties": False
            }
        }
    },
    "required": ["setup_summary", "levers"],
    "additionalProperties": False
}

SCENARIO_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["strategy_holds", "decision_changed"]},
        "headline": {"type": "string"},
        "resulting_call": {"type": "string"},
        "what_changed": {"type": "string"},
        "why_it_matters": {"type": "string"},
        "dominant_variable": {"type": "string"},
        "confidence": {"type": "string", "enum": ["Low", "Moderate", "High"]},
        "confidence_explanation": {"type": "string"},
        "reversal_condition": {"type": "string"}
    },
    "required": [
        "status", "headline", "resulting_call", "what_changed", "why_it_matters",
        "dominant_variable", "confidence", "confidence_explanation", "reversal_condition"
    ],
    "additionalProperties": False
}
