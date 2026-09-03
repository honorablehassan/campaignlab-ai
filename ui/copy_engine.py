from __future__ import annotations

from typing import Any


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def strategy_placeholder(field: str, context: dict[str, Any] | None = None) -> str:
    context = context or {}
    product = _clean(context.get("product"))
    objective = _clean(context.get("objective"))
    audience = _clean(context.get("audience"))
    geography = _clean(context.get("geography"))

    if field == "product":
        return "e.g. a product launch, pricing change, new market, customer experience, or business idea"

    if field == "custom_objective":
        if product:
            return f"What specifically must change for {product}? e.g. defend share, improve activation, lower CAC"
        return "e.g. Defend share against a new competitor or improve activation after signup"

    if field == "audience":
        if product and objective:
            return f"Who is most affected by this decision if the goal is to {objective.lower()}? e.g. customers, buyers, users, partners, or a specific segment"
        if product:
            return f"Who matters most to the decision about {product}, and in what situation?"
        return "e.g. first-time users, lapsed customers, CFOs at mid-market firms, local diners"

    if field == "geography":
        if audience:
            return f"Where does this decision apply? e.g. U.S. nationwide, Texas, selected metros"
        if product:
            return f"Where should CampaignLab evaluate the decision about {product}? e.g. U.S., Texas, UK, Global"
        return "e.g. Dallas–Fort Worth, U.S. nationwide, UK, selected college towns"

    if field == "context":
        focus = product or "this decision"
        parts = [f"What could materially change the recommendation for {focus}?"]
        if objective:
            parts.append(f"Include anything relevant to {objective.lower()}")
        parts.append("such as current performance, customer economics, competitors, channel constraints, timeline, prior tests, or regulatory limits.")
        return " ".join(parts)

    return ""


def evidence_design_placeholder(handoff: dict[str, Any] | None = None) -> str:
    if handoff:
        strategy = _clean(handoff.get("strategy_name"))
        objective = _clean(handoff.get("objective"))
        suggested = _clean(handoff.get("suggested_experiment"))
        if suggested:
            return f"Pressure-test the strategy: {suggested[:180]}"
        if strategy and objective:
            return f"What evidence would tell us whether '{strategy}' is actually improving {objective.lower()}?"
        if strategy:
            return f"What evidence would make us keep, revise, or reject '{strategy}'?"
    return "e.g. Does the new checkout experience increase completed purchases enough to justify shipping it?"


def evidence_outcome_placeholder(question: str = "", handoff: dict[str, Any] | None = None) -> str:
    question = _clean(question)
    if handoff:
        outcome = _clean(handoff.get("primary_outcome"))
        if outcome:
            return f"Suggested from Strategy: {outcome}"
        objective = _clean(handoff.get("objective"))
        if objective:
            return f"What single metric best captures {objective.lower()}?"
    if question:
        return "Name the primary outcome that would change the decision, e.g. purchase conversion, CAC, funded accounts"
    return "e.g. Purchase conversion, CAC, funded accounts, revenue per visitor"


def dataset_question_placeholder(role_map: dict[str, list[str]] | None = None, filename: str = "") -> str:
    role_map = role_map or {}
    has_treatment = bool(role_map.get("treatment"))
    has_binary = bool(role_map.get("binary_outcome"))
    has_spend = bool(role_map.get("spend"))
    has_revenue = bool(role_map.get("revenue"))
    has_channel = bool(role_map.get("channel") or role_map.get("campaign"))
    has_date = bool(role_map.get("date"))

    if has_treatment and has_binary:
        treatment = role_map["treatment"][0]
        outcome = role_map["binary_outcome"][0]
        return f"e.g. Did {treatment} materially improve {outcome}, and is the effect large enough to act on?"
    if has_spend and has_revenue and has_channel:
        group = (role_map.get("channel") or role_map.get("campaign"))[0]
        return f"e.g. Which {group} deserves more budget once we compare scale, efficiency, and risk?"
    if has_date and has_revenue:
        metric = role_map["revenue"][0]
        return f"e.g. What changed in {metric} over time, where did the break occur, and what should we investigate first?"
    if has_date:
        return "e.g. What changed over time, where are the anomalies, and which pattern is worth acting on?"
    if filename:
        return f"Optional: What decision should {filename} help you make? Leave blank and CampaignLab will discover the strongest supported opportunities."
    return "Optional: What decision should this dataset help you make? Leave blank and CampaignLab will discover the strongest supported opportunities."


def followup_placeholder(kind: str, strategy: dict[str, Any] | None = None) -> str:
    strategy = strategy or {}
    name = _clean(strategy.get("strategy_name")) or "the recommendation"
    if kind == "red_team":
        return f"Optional: attack a specific weakness in {name}, such as economics, audience fit, channel dependence, execution, or measurement."
    if kind == "challenger":
        return f"Describe a genuinely different path that could beat {name}, not a minor variation."
    if kind == "scenario":
        return f"Optional: describe a change in reality that could flip {name}, such as a new competitor, budget cut, deadline shift, or distribution win."
    return ""
