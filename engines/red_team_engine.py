import json

from config import MODEL
from core.personality import CAMPAIGNLAB_PERSONALITY
from engines._shared import bullet_block
from schemas.red_team import RED_TEAM_SCHEMA


def generate_red_team(
    client,
    inputs,
    context_result,
    strategy,
    attack_focus="",
):
    confirmed = bullet_block(context_result["confirmed_context"], "- None")
    inferences = bullet_block(context_result["reasonable_inferences"], "- None")
    unknowns = bullet_block(context_result["missing_context"], "- None")

    focus_instruction = (
        f"The user specifically wants you to stress-test this area:\n{attack_focus}"
        if attack_focus.strip()
        else "No special attack focus was provided. Attack the highest-risk parts of the recommendation."
    )

    prompt = f"""
{CAMPAIGNLAB_PERSONALITY}

You are operating CampaignLab's RED TEAM engine.

Your job is to perform ONE bounded stress test of the current strategy.

You are not here to generate a second strategy.
You are not here to rewrite the recommendation.
You are not here to create an endless critique loop.

Your job is to identify whether the current recommendation survives serious scrutiny.

==================================================
BUSINESS CONTEXT
==================================================
Decision type: {inputs["decision_type"]}
Product / company: {inputs["product"]}
Business model: {inputs["business_model"]}
Audience: {inputs["audience"]}
Objective: {inputs["objective"]}
Budget: {inputs["budget"]} {inputs["currency"]} · {inputs.get("budget_period", "Period not specified")}
Geography: {inputs["geography"]}
Additional context: {inputs["context"] if inputs["context"] else "None provided."}

==================================================
CONFIRMED CONTEXT
==================================================
{confirmed}

==================================================
REASONABLE INFERENCES
==================================================
{inferences}

==================================================
GENUINELY UNKNOWN
==================================================
{unknowns}

==================================================
CURRENT STRATEGY
==================================================
Name: {strategy["strategy_name"]}

Recommendation:
{strategy["recommendation"]}

Why CampaignLab preferred it:
{strategy["why_it_wins"]}

Current assumptions:
{json.dumps(strategy["key_assumptions"])}

Current risks:
{json.dumps(strategy["risks"])}

==================================================
ATTACK FOCUS
==================================================
{focus_instruction}

==================================================
YOUR TASK
==================================================

Return a sharp, decision-useful red-team assessment.

1. MOST DANGEROUS ASSUMPTION
Choose the single assumption most capable of breaking the recommendation.
It may be explicit in the strategy or implicit in the logic.

2. FAILURE MODES
Identify 2-4 concrete ways the strategy could fail.
Do not pad the list with generic marketing risks.

3. CONTRARY EVIDENCE NEEDED
Identify 1-3 observations, measurements, or facts that would materially weaken
or disprove the current recommendation.

4. WHAT WE ARE UNDERESTIMATING
Name the factor CampaignLab may be giving too little weight.

5. CHEAPEST NEXT CHECK
Recommend the cheapest credible piece of data, validation, or experiment that
would reduce the most important uncertainty.
Do not design the full experiment here.

6. VERDICT
Choose exactly one:
- Survives
- Survives with caution
- Rethink

"Survives" means the recommendation remains defensible despite the attack.
"Survives with caution" means it remains the current lean, but one or more
uncertainties could realistically change the decision.
"Rethink" means the current recommendation should not remain the working
strategy without resolving a major flaw.

==================================================
EPISTEMIC RULES
==================================================

- Do not invent external evidence.
- Do not invent company capabilities or historical performance.
- Do not turn an inference into a confirmed fact.
- Use unknowns as uncertainty, not as permission to hallucinate.
- Do not manufacture objections just to sound skeptical.
- Do not recommend another analysis after the verdict.
- Keep the Red Team bounded and terminal.
"""

    response = client.responses.create(
        model=MODEL,
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "strategy_red_team",
                "schema": RED_TEAM_SCHEMA,
                "strict": True,
            }
        },
    )

    return json.loads(response.output_text)
