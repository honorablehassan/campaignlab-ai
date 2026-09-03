CONTEXT_SCHEMA = {
    "type": "object",
    "properties": {
        "context_status": {
            "type": "string",
            "enum": ["sufficient", "partial", "critical_missing"],
        },
        "reason": {"type": "string"},
        "confirmed_context": {"type": "array", "items": {"type": "string"}},
        "reasonable_inferences": {"type": "array", "items": {"type": "string"}},
        "missing_context": {"type": "array", "items": {"type": "string"}},
        "clarifying_question": {"type": "string"},
    },
    "required": [
        "context_status",
        "reason",
        "confirmed_context",
        "reasonable_inferences",
        "missing_context",
        "clarifying_question",
    ],
    "additionalProperties": False,
}
