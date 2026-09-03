RED_TEAM_SCHEMA = {
    "type": "object",
    "properties": {
        "most_dangerous_assumption": {"type": "string"},
        "failure_modes": {
            "type": "array",
            "items": {"type": "string"}
        },
        "contrary_evidence_needed": {
            "type": "array",
            "items": {"type": "string"}
        },
        "what_we_are_underestimating": {"type": "string"},
        "cheapest_next_check": {"type": "string"},
        "verdict": {
            "type": "string",
            "enum": [
                "Survives",
                "Survives with caution",
                "Rethink"
            ]
        },
        "verdict_reason": {"type": "string"}
    },
    "required": [
        "most_dangerous_assumption",
        "failure_modes",
        "contrary_evidence_needed",
        "what_we_are_underestimating",
        "cheapest_next_check",
        "verdict",
        "verdict_reason"
    ],
    "additionalProperties": False
}
