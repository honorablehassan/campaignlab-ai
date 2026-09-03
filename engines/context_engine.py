import json

from config import MODEL
from core.personality import CAMPAIGNLAB_PERSONALITY
from schemas.context import CONTEXT_SCHEMA


def check_context(client, inputs):
    prompt = f"""
{CAMPAIGNLAB_PERSONALITY}

You are currently operating as CampaignLab's Context Sufficiency Engine.

Your job is NOT to develop the strategy yet.
Your job is to understand what we know, what can reasonably be inferred,
and what remains genuinely unknown.

USER CONTEXT
Decision type: {inputs["decision_type"]}
Decision subject: {inputs["product"]}
Business model: {inputs["business_model"]}
People / stakeholders in scope: {inputs["audience"]}
Primary objective: {inputs["objective"]}
Budget / resources: {inputs["budget"]} {inputs["currency"]} · {inputs.get("budget_period", "Period not specified")}
Geography: {inputs["geography"]}

Additional strategic context:
{inputs["context"] if inputs["context"] else "None provided."}

Additional clarification:
{inputs["clarification"] if inputs["clarification"] else "None provided."}

==================================================
THINK IN THREE BUCKETS
==================================================

1. CONFIRMED CONTEXT
Information explicitly provided by the user.
Do not embellish it.

2. REASONABLE STRATEGIC INFERENCE
Insights that can reasonably be derived from:
- the decision subject or product category
- business model
- customer, user, buyer, or stakeholder situation
- objective
- geography
- established general domain knowledge
- normal business, strategy, product, or marketing logic

Use your domain knowledge.
Do NOT classify something as missing merely because the user did not
explicitly type an implication that a competent strategist could reasonably recognize.
An inference is NOT a confirmed fact about this specific company or campaign.

3. GENUINELY MISSING CONTEXT
Information that:
- cannot responsibly be inferred, AND
- could meaningfully affect the recommendation.
Do not invent these.

==================================================
CONTEXT STATUS
==================================================

SUFFICIENT:
Enough information exists to make a useful recommendation.

PARTIAL:
Some relevant information remains unknown, but CampaignLab can still make
a useful recommendation by explicitly labeling assumptions.

CRITICAL_MISSING:
One missing piece of information could fundamentally change which strategic
direction should be recommended.
Only use critical_missing when CampaignLab truly should not recommend a
direction without asking first.

==================================================
QUESTIONING RULES
==================================================

Do not interrogate the user.
Do not ask for information merely because it would be nice to have.
Real decisions always contain uncertainty.
Infer obvious context.
Ask for consequential context.
Leave genuine uncertainty labeled as uncertainty.
Prefer "partial" over "critical_missing" unless the missing information could
materially change the strategic direction.
If critical context is missing, ask exactly ONE high-value clarifying question.
If context is sufficient or partial, clarifying_question must be an empty string.
Be concise.
"""

    response = client.responses.create(
        model=MODEL,
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "context_sufficiency",
                "schema": CONTEXT_SCHEMA,
                "strict": True,
            }
        },
    )
    return json.loads(response.output_text)
