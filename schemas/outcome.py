"""Contract for an observed outcome linked to a CampaignLab decision."""

OUTCOME_OBSERVATION_VERSION = "1.0"

OUTCOME_OBSERVATION_SCHEMA = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "decision_id": {"type": "string"},
        "source": {"type": "string"},
        "observed_at": {"type": "string"},
        "metric": {"type": "string"},
        "predicted_direction": {"type": "string", "enum": ["increase", "decrease", "no_change", "unknown"]},
        "predicted_value": {"type": ["number", "null"]},
        "predicted_low": {"type": ["number", "null"]},
        "predicted_high": {"type": ["number", "null"]},
        "actual_value": {"type": "number"},
        "unit": {"type": "string"},
        "notes": {"type": "string"},
        "score": {
            "type": "object",
            "properties": {
                "direction_correct": {"type": ["boolean", "null"]},
                "error": {"type": ["number", "null"]},
                "inside_interval": {"type": ["boolean", "null"]},
                "label": {"type": "string"},
            },
            "required": ["direction_correct", "error", "inside_interval", "label"],
            "additionalProperties": False,
        },
    },
    "required": [
        "version", "decision_id", "source", "observed_at", "metric",
        "predicted_direction", "predicted_value", "predicted_low", "predicted_high",
        "actual_value", "unit", "notes", "score",
    ],
    "additionalProperties": False,
}
