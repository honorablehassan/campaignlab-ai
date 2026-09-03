STRATEGY_SCHEMA = {
    "type": "object",
    "properties": {
        "strategy_name": {"type": "string"},
        "recommendation": {"type": "string"},
        "why_it_wins": {"type": "string"},
        "key_assumptions": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
        "devils_advocate": {"type": "string"},
        "suggested_experiment": {"type": "string"},
    },
    "required": [
        "strategy_name",
        "recommendation",
        "why_it_wins",
        "key_assumptions",
        "risks",
        "devils_advocate",
        "suggested_experiment",
    ],
    "additionalProperties": False,
}
