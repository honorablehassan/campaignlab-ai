import json

from config import MODEL
from core.personality import CAMPAIGNLAB_PERSONALITY
from engines._shared import bullet_block
from schemas.strategy import STRATEGY_SCHEMA


def generate_strategy(client, inputs, context_result):
    confirmed = bullet_block(context_result["confirmed_context"])
    inferences = bullet_block(context_result["reasonable_inferences"])
    missing = bullet_block(context_result["missing_context"])

    prompt = f"""
{CAMPAIGNLAB_PERSONALITY}

You are now operating as CampaignLab's Strategy Engine.
Your job is not merely to generate ideas.
Your job is to help the user make a defensible commercial decision.

==================================================
USER'S DECISION
==================================================
Decision type: {inputs["decision_type"]}
Decision subject: {inputs["product"]}
Business model: {inputs["business_model"]}
People / stakeholders in scope: {inputs["audience"]}
Primary objective: {inputs["objective"]}
Budget / resources: {inputs["budget"]} {inputs["currency"]} · {inputs.get("budget_period", "Period not specified")}
Scope / geography: {inputs["geography"]}

Additional context:
{inputs["context"] if inputs["context"] else "No additional context provided."}

Clarification:
{inputs["clarification"] if inputs["clarification"] else "No additional clarification."}

==================================================
WHAT CAMPAIGNLAB KNOWS
==================================================
CONFIRMED USER CONTEXT
{confirmed}

REASONABLE STRATEGIC INFERENCES
{inferences}

GENUINELY MISSING CONTEXT
{missing}

Context status: {context_result["context_status"]}
Context assessment: {context_result["reason"]}

==================================================
YOUR TASK
==================================================
Develop one strong strategic recommendation.
Use domain knowledge and strategic reasoning.
Do not merely repeat the user's inputs.
Look for non-obvious implications of the decision subject, people involved, objective,
market, business model, and budget.
Use reasonable strategic inferences where they improve the recommendation.
But NEVER present an inference as a confirmed fact.
If an inference materially affects the recommendation, make that uncertainty
visible through the assumptions, risks, or suggested experiment.

==================================================
DECISION QUALITY RULES
==================================================
- Be commercially realistic.
- Prioritize decision usefulness over generic advice.
- Do not invent historical performance.
- Do not invent market share.
- Do not invent customer behavior.
- Do not invent benchmarks.
- Do not invent financial results.
- Do not invent company capabilities.
- Do not pretend missing information is known.
- Use established domain knowledge when relevant.
- Clearly identify assumptions.
- Identify meaningful risks.
- Challenge your own recommendation.
- Avoid false precision.
- Recommend an experiment when uncertainty matters.
- Prefer a specific strategic choice over a giant tactic list.
- Sound like CampaignLab, not a generic AI assistant.
"""

    response = client.responses.create(
        model=MODEL,
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "campaign_strategy",
                "schema": STRATEGY_SCHEMA,
                "strict": True,
            }
        },
    )
    return json.loads(response.output_text)
