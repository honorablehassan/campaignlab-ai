STRATEGY_CARD_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "thesis": {"type": "string"},
    },
    "required": ["name", "thesis"],
    "additionalProperties": False,
}

BATTLE_SCHEMA = {
    "type": "object",
    "properties": {
        "original": STRATEGY_CARD_SCHEMA,
        "challenger_1": STRATEGY_CARD_SCHEMA,
        "challenger_2": STRATEGY_CARD_SCHEMA,
        "criteria": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "criterion": {"type": "string"},
                    "original_rating": {
                        "type": "string",
                        "enum": ["Strong", "Moderate", "Weak"],
                    },
                    "challenger_1_rating": {
                        "type": "string",
                        "enum": ["Strong", "Moderate", "Weak"],
                    },
                    "challenger_2_rating": {
                        "type": "string",
                        "enum": ["Strong", "Moderate", "Weak"],
                    },
                    "basis": {"type": "string"},
                },
                "required": [
                    "criterion",
                    "original_rating",
                    "challenger_1_rating",
                    "challenger_2_rating",
                    "basis",
                ],
                "additionalProperties": False,
            },
        },
        "winner": {
            "type": "string",
            "enum": ["original", "challenger_1", "challenger_2", "no_clear_winner"],
        },
        "campaignlab_call": {"type": "string"},
        "why_winner": {"type": "string"},
        "confidence": {
            "type": "string",
            "enum": ["Low", "Moderate", "High"],
        },
        "confidence_explanation": {"type": "string"},
        "flip_conditions": {"type": "array", "items": {"type": "string"}},
        "decision_caution": {"type": "string"},
    },
    "required": [
        "original",
        "challenger_1",
        "challenger_2",
        "criteria",
        "winner",
        "campaignlab_call",
        "why_winner",
        "confidence",
        "confidence_explanation",
        "flip_conditions",
        "decision_caution",
    ],
    "additionalProperties": False,
}
