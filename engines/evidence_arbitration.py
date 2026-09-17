"""Deterministic rules for reconciling multiple analytical results."""

from __future__ import annotations

from typing import Any

from schemas.evidence_arbitration import EVIDENCE_ARBITRATION_VERSION


IDENTIFICATION = {
    "analyze_binary_ab": ("randomized", 80),
    "analyze_continuous_ab_dataset": ("randomized", 80),
    "analyze_cuped": ("randomized_adjusted", 84),
    "analyze_abn_dataset": ("randomized", 78),
    "run_difference_in_differences": ("quasi_experimental", 68),
    "run_event_study": ("quasi_experimental", 70),
    "run_interrupted_time_series": ("quasi_experimental", 62),
    "bootstrap_group_difference": ("associational_comparison", 48),
    "fit_linear_regression": ("observational", 42),
    "fit_logistic_regression": ("observational", 42),
    "analyze_marketing_efficiency": ("descriptive_attribution", 28),
    "fit_tree_model": ("predictive", 25),
    "analyze_cohort_retention": ("descriptive", 25),
    "analyze_funnel": ("descriptive", 22),
    "segment_kmeans": ("descriptive", 18),
    "detect_anomalies": ("descriptive", 18),
}


def _rank(result: dict[str, Any]) -> dict[str, Any]:
    method = str(result.get("method_id") or "unknown")
    identification, score = IDENTIFICATION.get(method, ("unknown", 15))
    checks = result.get("integrity_checks") or []
    if any(x.get("status") == "fail" for x in checks):
        score -= 45
    elif any(x.get("status") == "warning" for x in checks):
        score -= 12
    uncertainty = result.get("uncertainty") or {}
    if uncertainty.get("low") is not None and uncertainty.get("high") is not None:
        score += 5
    warnings = [str(x) for x in (result.get("warnings") or [])]
    score -= min(15, 3 * len(warnings))
    return {
        "method_id": method,
        "identification": identification,
        "score": max(0, int(score)),
        "verdict": str(result.get("decision", {}).get("verdict") or "REVIEW").upper(),
        "direction": str(result.get("estimate", {}).get("direction") or "unknown"),
        "estimand": str(result.get("estimand") or "unknown"),
        "warnings": warnings,
    }


def arbitrate_evidence(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Rank evidence and identify agreement, conflict, or non-comparability."""
    ranked = sorted((_rank(item) for item in results), key=lambda x: x["score"], reverse=True)
    if not ranked:
        return {
            "version": EVIDENCE_ARBITRATION_VERSION,
            "status": "insufficient",
            "dominant_method": None,
            "resolved_verdict": "REVIEW",
            "confidence_adjustment": -25,
            "reason": "No executed analytical evidence is available to arbitrate.",
            "ranked_evidence": [],
            "conflicts": [],
            "comparability_warnings": [],
            "next_evidence": "Execute the strongest eligible deterministic method.",
        }

    dominant = ranked[0]
    if len(ranked) == 1:
        return {
            "version": EVIDENCE_ARBITRATION_VERSION,
            "status": "insufficient",
            "dominant_method": dominant["method_id"],
            "resolved_verdict": dominant["verdict"],
            "confidence_adjustment": 0,
            "reason": "Only one executed result is available; no cross-method arbitration was required.",
            "ranked_evidence": ranked,
            "conflicts": [],
            "comparability_warnings": [],
            "next_evidence": "Add independent evidence only if it could realistically change the decision.",
        }

    estimands = {x["estimand"] for x in ranked}
    directions = {x["direction"] for x in ranked if x["direction"] != "unknown"}
    verdicts = {x["verdict"] for x in ranked}
    comparability = []
    if len(estimands) > 1:
        comparability.append("The methods do not state the same estimand; numerical results must not be pooled or averaged.")

    conflicts = []
    if len(directions) > 1:
        conflicts.append("Executed methods point in different effect directions.")
    if len(verdicts) > 1:
        conflicts.append("Executed methods imply different decision verdicts.")

    if conflicts:
        status = "conflict"
        adjustment = -18
        reason = f"Evidence conflicts. CampaignLab gives provisional priority to {dominant['method_id']} because its identification and diagnostics rank higher, but lowers confidence."
        next_evidence = "Resolve whether the methods measured the same population, outcome and period; then run the strongest feasible causal check."
    elif comparability:
        status = "directional_agreement" if len(directions) <= 1 else "not_comparable"
        adjustment = -7
        reason = "The evidence points in a similar direction, but the estimands differ, so agreement is directional rather than numerical confirmation."
        next_evidence = "Align the population, outcome, comparison and time window before treating the results as replication."
    else:
        status = "agreement"
        adjustment = 8
        reason = "Independent executed results agree on both direction and decision under the same stated estimand."
        next_evidence = "Do not collect more evidence unless the decision is costly, irreversible or outside the observed support."

    return {
        "version": EVIDENCE_ARBITRATION_VERSION,
        "status": status,
        "dominant_method": dominant["method_id"],
        "resolved_verdict": dominant["verdict"],
        "confidence_adjustment": adjustment,
        "reason": reason,
        "ranked_evidence": ranked,
        "conflicts": conflicts,
        "comparability_warnings": comparability,
        "next_evidence": next_evidence,
    }
