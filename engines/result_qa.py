from __future__ import annotations
from typing import Any
from config import MODEL

RESULT_QA_INSTRUCTIONS = """
You are CampaignLab's result explainer. Answer only from the supplied CampaignLab analysis context.
Use clear marketing/business language. If the context does not support a claim, say so.
Do not invent calculations, p-values, causal claims, or dataset facts. Keep the answer concise and decision-oriented.
When a technical term matters, translate it in one sentence before using it.
""".strip()


def ask_about_result(client: Any, *, question: str, analysis_text: str, method_name: str, user_question: str) -> str:
    context = (
        f"BUSINESS QUESTION:\n{question or 'No explicit question supplied.'}\n\n"
        f"PRIMARY METHOD:\n{method_name or 'Not specified'}\n\n"
        f"CAMPAIGNLAB ANALYSIS:\n{analysis_text[:12000]}\n\n"
        f"USER FOLLOW-UP:\n{user_question}"
    )
    response = client.responses.create(model=MODEL, instructions=RESULT_QA_INSTRUCTIONS, input=context)
    return getattr(response, "output_text", "") or "CampaignLab could not produce an explanation from the available result context."
