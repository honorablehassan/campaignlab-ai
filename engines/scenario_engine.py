import json

from config import MODEL
from core.personality import CAMPAIGNLAB_PERSONALITY
from engines._shared import bullet_block
from schemas.scenario import SCENARIO_RESULT_SCHEMA, SCENARIO_SETUP_SCHEMA


def generate_scenario_setup(client, inputs, context_result, strategy):
    confirmed = bullet_block(context_result["confirmed_context"], "- None")
    inferences = bullet_block(context_result["reasonable_inferences"], "- None")
    unknowns = bullet_block(context_result["missing_context"], "- None")

    prompt = f"""
{CAMPAIGNLAB_PERSONALITY}

You are operating CampaignLab's SCENARIO LAB SETUP engine.

Identify the SMALL NUMBER of variables most capable of changing CampaignLab's
current strategic call. Do not re-analyze the whole strategy. Do not generate
a long report. Do not ask the user ten questions.

BUSINESS CONTEXT
Decision type: {inputs["decision_type"]}
Product / company: {inputs["product"]}
Business model: {inputs["business_model"]}
Audience: {inputs["audience"]}
Objective: {inputs["objective"]}
Budget: {inputs["budget"]} {inputs["currency"]} · {inputs.get("budget_period", "Period not specified")}
Geography: {inputs["geography"]}
Additional context: {inputs["context"] if inputs["context"] else "None provided."}

CONFIRMED CONTEXT
{confirmed}

REASONABLE INFERENCES
{inferences}

GENUINELY UNKNOWN
{unknowns}

CURRENT CAMPAIGNLAB CALL
Strategy: {strategy["strategy_name"]}
Recommendation: {strategy["recommendation"]}
Why it wins: {strategy["why_it_wins"]}
Assumptions: {json.dumps(strategy["key_assumptions"])}
Risks: {json.dumps(strategy["risks"])}

YOUR TASK
Suggest 2 to 4 PRESSURE POINTS the user can manipulate. A pressure point should
be capable of changing the strategic thesis, not merely a tactic.

Examples may include budget, owned-audience access, customer acquisition
economics, conversion quality, risk tolerance, timeline, geography, partner
access, sales capacity, customer lifetime value, regulation, or brand credibility.
Choose variables for THIS decision.

NUMERIC controls:
- use when a meaningful numeric range exists;
- numeric_current reflects the known value when available;
- numeric_min/max create a realistic decision-testing range;
- numeric_step must be positive;
- unit is concise;
- options = [] and default_option = "".

CATEGORICAL controls:
- use 3 to 5 concise ordered options;
- default_option must be in options;
- all numeric fields = 0 and unit = "".

Do not pretend an unknown current state is known. If it is unknown, say
"Unknown" in current_label and use a neutral default control value.

setup_summary must be ONE concise sentence explaining why these are the levers
most likely to change the call.

Decision compression rule: identify the few variables that matter most, then stop.
"""

    response = client.responses.create(
        model=MODEL,
        input=prompt,
        text={"format": {"type": "json_schema", "name": "scenario_setup", "schema": SCENARIO_SETUP_SCHEMA, "strict": True}},
    )
    return json.loads(response.output_text)


def evaluate_scenario(client, inputs, context_result, strategy, selected_changes, custom_change=""):
    confirmed = bullet_block(context_result["confirmed_context"], "- None")
    inferences = bullet_block(context_result["reasonable_inferences"], "- None")
    unknowns = bullet_block(context_result["missing_context"], "- None")

    prompt = f"""
{CAMPAIGNLAB_PERSONALITY}

You are operating CampaignLab's SCENARIO LAB DECISION engine.

The user changed parts of reality around an existing recommendation. Answer ONE
question: DOES THE STRATEGY STILL HOLD, OR SHOULD CAMPAIGNLAB CHANGE ITS CALL?

ORIGINAL BUSINESS CONTEXT
Decision type: {inputs["decision_type"]}
Product / company: {inputs["product"]}
Business model: {inputs["business_model"]}
Audience: {inputs["audience"]}
Objective: {inputs["objective"]}
Original budget: {inputs["budget"]} {inputs["currency"]} · {inputs.get("budget_period", "Period not specified")}
Geography: {inputs["geography"]}
Additional context: {inputs["context"] if inputs["context"] else "None provided."}

CONFIRMED CONTEXT
{confirmed}

REASONABLE INFERENCES
{inferences}

GENUINELY UNKNOWN
{unknowns}

ORIGINAL CAMPAIGNLAB CALL
Strategy: {strategy["strategy_name"]}
Recommendation: {strategy["recommendation"]}
Why it wins: {strategy["why_it_wins"]}
Assumptions: {json.dumps(strategy["key_assumptions"])}
Risks: {json.dumps(strategy["risks"])}

SCENARIO CHANGES
{json.dumps(selected_changes, indent=2)}

Optional custom change:
{custom_change.strip() or "None."}

DECISION RULES
- strategy_holds: current strategic thesis remains the best available call.
- decision_changed: changed conditions materially alter which strategic thesis is most defensible.
- Do not flip the decision for cosmetic or tactical differences.
- Do not invent evidence.
- User-selected hypotheticals are true only INSIDE THIS SCENARIO.
- If changed, resulting_call states the new strategic direction.
- If it holds, resulting_call reaffirms the current direction.
- confidence means how strongly available information separates the decisions, not probability.
- explain what creates or limits confidence.
- no decision is 100% certain, but make the best available call.
- reversal_condition is the SINGLE most important additional change that could reverse the result.
- Keep every field concise. Do not create a full strategy report. Do not end with extra questions.
Make the call and stop.
"""

    response = client.responses.create(
        model=MODEL,
        input=prompt,
        text={"format": {"type": "json_schema", "name": "scenario_result", "schema": SCENARIO_RESULT_SCHEMA, "strict": True}},
    )
    return json.loads(response.output_text)
