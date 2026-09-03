import json

from config import MODEL
from core.personality import CAMPAIGNLAB_PERSONALITY
from engines._shared import bullet_block
from schemas.battle import BATTLE_SCHEMA


def generate_strategy_battle(
    client,
    inputs,
    context_result,
    original_strategy,
    battle_mode,
    user_challenger,
):
    confirmed = bullet_block(context_result["confirmed_context"], "- None")
    inferences = bullet_block(context_result["reasonable_inferences"], "- None")
    unknowns = bullet_block(context_result["missing_context"], "- None")

    if battle_mode == "I have something in mind":
        challenger_instruction = f"""
The user has nominated this challenger:
{user_challenger}

Use that idea as Challenger 1.
You must then generate ONE additional strategically distinct challenger as Challenger 2.
Do not merely create a minor variation of either strategy.
"""
    else:
        challenger_instruction = """
The user wants CampaignLab to find the challengers.
Generate TWO strategically distinct challengers.
They should represent genuinely different strategic theses,
not small changes to channels, messaging, or budget splits.
"""

    prompt = f"""
{CAMPAIGNLAB_PERSONALITY}

You are operating CampaignLab's STRATEGY BATTLE engine.
You already made a strategic recommendation.
Now your job is to try to beat it.
This is NOT an exercise in defending your earlier answer.
If a challenger is stronger, say so.

==================================================
ORIGINAL BUSINESS CONTEXT
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
ORIGINAL CAMPAIGNLAB STRATEGY
==================================================
Name: {original_strategy["strategy_name"]}
Recommendation: {original_strategy["recommendation"]}
Why: {original_strategy["why_it_wins"]}
Assumptions: {json.dumps(original_strategy["key_assumptions"])}
Risks: {json.dumps(original_strategy["risks"])}

==================================================
CHALLENGER INSTRUCTIONS
==================================================
{challenger_instruction}

==================================================
HOW THE BATTLE WORKS
==================================================
Compare exactly THREE strategies:
1. Original strategy
2. Challenger 1
3. Challenger 2

A challenger should differ at the level of strategic thesis.
Good differences might involve:
- demand capture vs demand creation
- broad market vs focused segment
- direct acquisition vs partnerships/distribution
- performance-led vs brand-led
- short-term economics vs long-term strategic position
- centralized campaign vs ecosystem strategy

Do NOT make three slightly different media plans.

==================================================
SCORECARD
==================================================
Use these SIX core criteria:
1. Business Impact
2. Budget Fit
3. Speed to Learning
4. Execution Ease
5. Evidence Strength
6. Risk Control

Then add exactly ONE contextual personality criterion that is genuinely relevant.
Possible examples:
- Room-Winning Potential
- Big-Swing Potential
- CFO Friendliness
- Organizational Headache
- Strategic Optionality
- Competitive Surprise
- Leadership Appeal

Do not force a joke. Choose one that actually helps illuminate the decision.

==================================================
RATING RULES
==================================================
Use only: Strong, Moderate, Weak.
These are qualitative CampaignLab judgments.
Do NOT create numeric scores.
Do NOT pretend they are calculated.
For every criterion, provide a concise BASIS explaining why the three strategies
received their ratings.
The basis must come from confirmed user context, reasonable strategic inference,
clearly identified unknowns, or legitimate general domain reasoning.
Do not invent external facts.
Do not fabricate citations.
CampaignLab does NOT currently have external research evidence for this battle
unless such evidence was explicitly provided by the user.

==================================================
CAMPAIGNLAB'S CALL
==================================================
Pick: original, challenger_1, challenger_2, or no_clear_winner.
The original strategy is allowed to lose.
Do not pick a winner merely because CampaignLab generated the original first.
Optimize for the user's objective, business context, budget, risk, feasibility,
evidence, and ability to learn.

==================================================
CONFIDENCE
==================================================
Confidence means: HOW STRONGLY DOES THE AVAILABLE INFORMATION SEPARATE THE STRATEGIES?
It does NOT mean the probability CampaignLab is correct.
Use: Low, Moderate, High.
Explain what is creating or limiting confidence.

==================================================
WHAT WOULD FLIP THE DECISION?
==================================================
Identify 1-3 specific conditions or pieces of evidence that could cause another
strategy to become preferable. These should be meaningful decision boundaries.
Do not continue into another analysis.
This Battle is a bounded decision comparison.
End with the decision.
"""

    response = client.responses.create(
        model=MODEL,
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "strategy_battle",
                "schema": BATTLE_SCHEMA,
                "strict": True,
            }
        },
    )
    return json.loads(response.output_text)
