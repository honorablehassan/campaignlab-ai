"""Deterministic convergence layer for CampaignLab results.

AI and statistical engines supply evidence. This module decides how strongly
CampaignLab may speak and always produces the same auditable output contract.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from schemas.decision import DECISION_OBJECT_VERSION


def _clean(items: list[Any] | None, limit: int = 8) -> list[str]:
    return [str(item).strip() for item in (items or []) if str(item).strip()][:limit]


def _evidence(statement: str, source: str, kind: str, strength: str) -> dict[str, str]:
    return {"statement": statement.strip(), "source": source, "kind": kind, "strength": strength}


def _confidence(score: int, basis: str, *, allow_high: bool = False) -> dict[str, Any]:
    score = max(0, min(100, int(round(score))))
    if score >= 80 and allow_high:
        label = "High"
    elif score >= 65:
        label = "Moderate"
    elif score >= 40:
        label = "Cautious"
    else:
        label = "Low"
    return {"label": label, "score": score, "basis": basis}


def _id(source: str, question: str, call: str) -> str:
    payload = json.dumps([source, question.strip(), call.strip()], ensure_ascii=False).encode("utf-8")
    return "cld_" + hashlib.sha256(payload).hexdigest()[:16]


def _base(*, source: str, question: str, call: str) -> dict[str, Any]:
    return {
        "decision_id": _id(source, question, call),
        "version": DECISION_OBJECT_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": source,
        "question": question.strip(),
        "call": call.strip(),
        "disposition": "investigate",
        "confidence": _confidence(0, "No evidence has been evaluated."),
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "assumptions": [],
        "alternatives_considered": [],
        "critical_uncertainties": [],
        "value_of_information": {
            "worth_resolving": False,
            "reason": "No consequential unresolved uncertainty was identified.",
            "smallest_next_check": "No additional check is required before the next action.",
        },
        "flip_conditions": [],
        "next_action": "Review the available evidence.",
        "predicted_outcome": "",
        "prediction": {"metric": "", "direction": "unknown", "point": None, "low": None, "high": None, "unit": ""},
        "outcome_status": "not_tracked",
        "actual_outcome": "",
        "provenance": {"deterministic": False, "methods": [], "warnings": []},
    }


def decision_from_strategy(
    strategy: dict[str, Any],
    context: dict[str, Any],
    inputs: dict[str, Any],
    *,
    battle: dict[str, Any] | None = None,
    red_team: dict[str, Any] | None = None,
    scenario: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Converge Strategy Lab outputs without inventing statistical certainty."""
    subject = str(inputs.get("product") or strategy.get("strategy_name") or "the decision")
    question = f"What is the strongest available strategy for {subject}?"
    call = str(strategy.get("recommendation") or strategy.get("strategy_name") or "Investigate before acting.")
    d = _base(source="Strategy Lab", question=question, call=call)

    status = context.get("context_status", "partial")
    score = {"sufficient": 68, "partial": 52, "critical_missing": 28}.get(status, 45)
    basis = "Strategic confidence reflects context completeness and adversarial checks; it is not a causal probability."

    confirmed = _clean(context.get("confirmed_context"), 6)
    inferred = _clean(context.get("reasonable_inferences"), 6)
    d["supporting_evidence"] = [
        _evidence(item, "User-provided context", "user_context", "moderate") for item in confirmed
    ]
    if strategy.get("why_it_wins"):
        d["supporting_evidence"].append(
            _evidence(str(strategy["why_it_wins"]), "Strategy Engine", "inference", "moderate")
        )
    d["assumptions"] = _clean(strategy.get("key_assumptions")) + inferred[:2]
    d["critical_uncertainties"] = _clean(context.get("missing_context")) + _clean(strategy.get("risks"), 4)
    d["contradicting_evidence"] = []

    if strategy.get("devils_advocate"):
        d["contradicting_evidence"].append(
            _evidence(str(strategy["devils_advocate"]), "Strategy Engine self-critique", "inference", "moderate")
        )

    if battle:
        alternatives = [battle.get("challenger_1", {}).get("name"), battle.get("challenger_2", {}).get("name")]
        d["alternatives_considered"] = _clean(alternatives)
        d["flip_conditions"] = _clean(battle.get("flip_conditions"))
        battle_conf = battle.get("confidence", "Low")
        score += {"High": 8, "Moderate": 3, "Low": -8}.get(battle_conf, 0)
        winner = battle.get("winner")
        if winner and winner not in {"original", "no_clear_winner"}:
            score -= 12
            d["contradicting_evidence"].append(
                _evidence(str(battle.get("why_winner") or "A challenger outperformed the original strategy."), "Strategy Arena", "inference", "moderate")
            )

    if red_team:
        verdict = red_team.get("verdict")
        score += {"Survives": 8, "Survives with caution": -4, "Rethink": -22}.get(verdict, 0)
        danger = str(red_team.get("most_dangerous_assumption") or "").strip()
        if danger:
            d["contradicting_evidence"].append(_evidence(danger, "Devil's Advocate", "inference", "moderate"))
        if not d["flip_conditions"]:
            d["flip_conditions"] = _clean(red_team.get("contrary_evidence_needed"))

    if scenario:
        if scenario.get("status") == "decision_changed":
            score -= 15
            d["flip_conditions"] = _clean([scenario.get("reversal_condition"), scenario.get("dominant_variable")])
        else:
            score += 4

    d["confidence"] = _confidence(score, basis)
    consequential = bool(d["critical_uncertainties"] or d["flip_conditions"]) and score < 75
    next_check = str(strategy.get("suggested_experiment") or "Run the smallest credible check against the most consequential assumption.")
    d["value_of_information"] = {
        "worth_resolving": consequential,
        "reason": (
            "One or more unresolved assumptions could realistically change the recommendation."
            if consequential else "The remaining uncertainty is not currently large enough to block a reversible next step."
        ),
        "smallest_next_check": next_check,
    }
    d["disposition"] = "investigate" if status == "critical_missing" else ("act_with_guardrails" if score < 75 else "act")
    d["next_action"] = next_check if d["disposition"] == "investigate" else call
    d["predicted_outcome"] = str(strategy.get("why_it_wins") or "")
    d["provenance"] = {
        "deterministic": False,
        "methods": ["context assessment", "strategy synthesis"] + (["strategy comparison"] if battle else []) + (["red team"] if red_team else []) + (["scenario analysis"] if scenario else []),
        "warnings": ["This is strategic reasoning, not a measured causal effect."],
    }
    return d


def decision_from_mmm(
    *,
    move: str,
    outcome: str,
    model_result: dict[str, Any],
    readiness_status: str,
    gain_pct: float,
    next_check: str,
    caveat: str,
) -> dict[str, Any]:
    """Convert a fitted MMM and optimizer output into a guarded decision."""
    question = f"How should the media mix change to improve {outcome}?"
    d = _base(source="Marketing Mix Model", question=question, call=move)
    model = model_result.get("model", {})
    strength = model.get("evidence_strength", "Limited")
    score = {"Moderate": 68, "Limited-to-moderate": 54, "Limited": 32}.get(strength, 35)
    if readiness_status == "caution":
        score -= 8
    improvement = float(model.get("media_holdout_improvement", 0.0))
    backtest_share = float(model.get("positive_backtest_share", 0.0))
    control_sensitivity = float(model.get("max_control_sensitivity", 0.0))
    calibrations = model.get("experiment_calibration") or []
    if improvement >= 0.10:
        score += 5
    elif improvement < 0.02:
        score -= 8

    d["confidence"] = _confidence(
        score,
        "Confidence combines data readiness, unseen-period performance, and media's incremental predictive value over baseline. It remains capped because this MMM is observational.",
    )
    d["supporting_evidence"] = [
        _evidence(f"{strength} model evidence after chronological holdout validation.", "Native MMM", "model_diagnostic", "moderate" if strength != "Limited" else "weak"),
        _evidence(f"Media improved unseen-period error versus baseline by {improvement:+.1%}.", "Native MMM holdout", "calculated", "moderate" if improvement >= 0.05 else "weak"),
        _evidence(f"The constrained allocation changes modeled media response by {gain_pct:+.1%}.", "Budget optimizer", "calculated", "moderate"),
    ]
    d["supporting_evidence"].append(
        _evidence(f"Media beat the baseline in {backtest_share:.0%} of expanding-window checks.", "Native MMM backtests", "model_diagnostic", "moderate" if backtest_share >= .67 else "weak")
    )
    if calibrations:
        channels = ", ".join(str(item.get("channel")) for item in calibrations)
        d["supporting_evidence"].append(
            _evidence(f"Experimental evidence calibrated the modeled response for {channels} within the supplied contrast and scope.", "Experiment calibration", "experimental_calibration", "strong")
        )
    d["contradicting_evidence"] = [
        _evidence(caveat, "MMM causal guardrail", "model_diagnostic", "strong")
    ]
    if control_sensitivity >= .75:
        d["contradicting_evidence"].append(
            _evidence(f"Removing one selected control changed at least one channel contribution by {control_sensitivity:.0%}.", "Control sensitivity", "model_diagnostic", "strong")
        )
    d["assumptions"] = [
        "Historical relationships remain informative for the proposed allocation period.",
        "Selected controls capture the most important non-media demand drivers.",
        "Channel response remains within the observed support range.",
        "Any supplied experimental result is transportable only to its stated channel, population, outcome, period and spend contrast.",
    ]
    d["alternatives_considered"] = ["Hold the current media mix"]
    d["critical_uncertainties"] = [caveat]
    d["flip_conditions"] = [
        "A credible incrementality test contradicts the modeled channel lift.",
        "Material demand drivers were omitted or changed after the modeled period.",
        "Required spend falls outside historical support.",
    ]
    worthwhile = strength != "Limited" and abs(gain_pct) >= 0.02
    d["value_of_information"] = {
        "worth_resolving": worthwhile,
        "reason": (
            "The modeled upside is consequential enough that causal validation could change the allocation decision."
            if worthwhile else "The current model does not show enough supported upside to justify an expensive validation study."
        ),
        "smallest_next_check": next_check,
    }
    d["disposition"] = "hold" if strength == "Limited" else "act_with_guardrails"
    d["next_action"] = next_check if worthwhile else move
    d["predicted_outcome"] = f"Approximately {gain_pct:+.1%} change in modeled media response at the specified budget."
    d["prediction"] = {
        "metric": outcome,
        "direction": "increase" if gain_pct > 0 else "decrease" if gain_pct < 0 else "no_change",
        "point": float(gain_pct),
        "low": None,
        "high": None,
        "unit": "proportional change",
    }
    d["provenance"] = {
        "deterministic": True,
        "methods": ["native MMM V2 beta", "rolling validation", "expanding-window backtests", "chronological holdout", "conditional block bootstrap", "baseline benchmark", "leave-one-control-out sensitivity", "constrained budget optimization"] + (["experiment calibration"] if calibrations else []),
        "warnings": [model_result.get("warning", "Observational MMM does not prove causality.")],
    }
    return d


def decision_from_evidence(
    *,
    question: str,
    analytical_result: dict[str, Any] | None,
    call: str | None = None,
    next_action: str | None = None,
    arbitration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Converge a deterministic Evidence Lab result or an explicitly blocked plan."""
    if analytical_result is None:
        d = _base(
            source="Evidence Lab",
            question=question or "What can the available evidence support?",
            call=call or "Do not make the decision from this evidence yet.",
        )
        d["disposition"] = "investigate"
        d["confidence"] = _confidence(25, "No deterministic analysis completed, so CampaignLab is returning a plan rather than an evidence-backed conclusion.")
        d["critical_uncertainties"] = ["No executable deterministic result is available yet."]
        d["value_of_information"] = {
            "worth_resolving": True,
            "reason": "The missing evidence currently prevents a defensible conclusion.",
            "smallest_next_check": next_action or "Complete the recommended deterministic analysis.",
        }
        d["next_action"] = next_action or "Complete the recommended deterministic analysis."
        d["provenance"] = {"deterministic": False, "methods": ["evidence planning"], "warnings": ["This is a plan, not an executed result."]}
        return d

    method = str(analytical_result.get("method_id") or "deterministic analysis")
    verdict = str(analytical_result.get("decision", {}).get("verdict") or "REVIEW").upper()
    reason = str(analytical_result.get("decision", {}).get("reason") or "Review the analytical result.")
    default_call = {
        "SHIP": "Proceed with the tested change.",
        "DON'T SHIP": "Do not proceed with the tested change.",
        "HOLD": "Hold the decision until the uncertainty is reduced.",
    }.get(verdict, "Treat this as evidence to investigate, not a final call.")
    d = _base(source="Evidence Lab", question=question or "What does the evidence support?", call=call or default_call)

    checks = analytical_result.get("integrity_checks") or []
    failed = [x for x in checks if x.get("status") == "fail"]
    cautions = [x for x in checks if x.get("status") in {"warning", "not_available"}]
    interval = analytical_result.get("uncertainty") or {}
    low, high = interval.get("low"), interval.get("high")
    estimate = analytical_result.get("estimate") or {}
    estimate_value = estimate.get("value")

    score = 76 if verdict in {"SHIP", "DON'T SHIP"} else 54 if verdict == "HOLD" else 42
    score -= 28 if failed else 8 if cautions else 0
    if low is None or high is None:
        score -= 6
    if arbitration:
        score += int(arbitration.get("confidence_adjustment") or 0)
    allow_high = verdict in {"SHIP", "DON'T SHIP"} and not failed and not cautions
    d["confidence"] = _confidence(
        score,
        "Confidence is derived from the deterministic decision rule, uncertainty interval, and integrity checks—not from the fluency of the AI explanation.",
        allow_high=allow_high,
    )
    d["disposition"] = "act" if verdict == "SHIP" and not failed else "hold" if verdict in {"HOLD", "DON'T SHIP"} or failed else "investigate"

    estimate_text = f"Estimated {analytical_result.get('estimand', 'effect')}"
    if estimate_value is not None:
        estimate_text += f": {float(estimate_value):+.4g} {estimate.get('unit', '')}".rstrip()
    d["supporting_evidence"] = [_evidence(estimate_text + ".", method, "calculated", "strong")]
    if low is not None and high is not None:
        d["supporting_evidence"].append(
            _evidence(f"The {int(float(interval.get('level') or .95) * 100)}% interval runs from {float(low):+.4g} to {float(high):+.4g}.", method, "calculated", "strong")
        )
    d["supporting_evidence"].append(_evidence(reason, method, "model_diagnostic", "strong" if not failed else "weak"))
    d["contradicting_evidence"] = [
        _evidence(str(x.get("detail") or x.get("name")), method, "model_diagnostic", "strong" if x.get("status") == "fail" else "moderate")
        for x in failed + cautions
    ]
    if arbitration:
        for item in (arbitration.get("conflicts") or []) + (arbitration.get("comparability_warnings") or []):
            d["contradicting_evidence"].append(
                _evidence(str(item), "Evidence Arbitration", "model_diagnostic", "strong" if arbitration.get("status") == "conflict" else "moderate")
            )
        d["supporting_evidence"].append(
            _evidence(str(arbitration.get("reason") or "Evidence was arbitrated."), "Evidence Arbitration", "model_diagnostic", "moderate")
        )
    d["assumptions"] = _clean(analytical_result.get("assumptions"))
    d["critical_uncertainties"] = _clean(analytical_result.get("warnings")) + [str(x.get("detail")) for x in failed]
    if arbitration and arbitration.get("status") in {"conflict", "not_comparable", "directional_agreement"}:
        d["critical_uncertainties"] += _clean(arbitration.get("conflicts")) + _clean(arbitration.get("comparability_warnings"))
    d["flip_conditions"] = [
        "A repeated or better-identified analysis reverses the effect direction.",
        "An integrity check fails or the decision-relevant business threshold changes.",
    ]
    arbitration_requires_work = bool(arbitration and arbitration.get("status") in {"conflict", "not_comparable"})
    worth_resolving = verdict in {"HOLD", "REVIEW"} or bool(failed) or arbitration_requires_work
    smallest_check = next_action or (
        str(arbitration.get("next_evidence")) if arbitration_requires_work
        else "Fix the failed integrity check and rerun the analysis." if failed
        else "Run the smallest adequately powered follow-up that could settle the decision."
    )
    d["value_of_information"] = {
        "worth_resolving": worth_resolving,
        "reason": "Remaining uncertainty could change the decision." if worth_resolving else "The executed evidence supports a reversible next action without waiting for another study.",
        "smallest_next_check": smallest_check,
    }
    d["next_action"] = smallest_check if worth_resolving else (next_action or d["call"])
    d["predicted_outcome"] = estimate_text
    d["prediction"] = {
        "metric": analytical_result.get("estimand", "effect"),
        "direction": "increase" if estimate_value is not None and float(estimate_value) > 0 else "decrease" if estimate_value is not None and float(estimate_value) < 0 else "no_change" if estimate_value == 0 else "unknown",
        "point": float(estimate_value) if estimate_value is not None else None,
        "low": float(low) if low is not None else None,
        "high": float(high) if high is not None else None,
        "unit": str(estimate.get("unit") or ""),
    }
    d["provenance"] = {
        "deterministic": True,
        "methods": [method, "analytical result contract"] + (["evidence arbitration"] if arbitration else []) + ["decision kernel"],
        "warnings": _clean(analytical_result.get("warnings")),
    }
    return d


def update_outcome(decision: dict[str, Any], *, status: str, actual_outcome: str = "") -> dict[str, Any]:
    if status not in {"not_tracked", "planned", "acted", "observed"}:
        raise ValueError("Unsupported decision outcome status.")
    updated = deepcopy(decision)
    updated["outcome_status"] = status
    updated["actual_outcome"] = actual_outcome.strip()
    return updated
