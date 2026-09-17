"""Normalize deterministic outputs without discarding their method-specific detail."""

from __future__ import annotations

from typing import Any

from schemas.analytical_result import ANALYTICAL_RESULT_VERSION


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _first(result: dict[str, Any], *names: str) -> float | None:
    for name in names:
        value = _number(result.get(name))
        if value is not None:
            return value
    return None


def _direction(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "neutral"


def analytical_result(
    method_id: str,
    result: dict[str, Any],
    *,
    question: str = "",
) -> dict[str, Any]:
    """Create the common evidence envelope while preserving the raw result separately."""
    estimate = _first(result, "absolute_lift", "effect", "estimate", "difference", "coefficient")
    low = _first(result, "ci_low", "confidence_interval_low", "lower")
    high = _first(result, "ci_high", "confidence_interval_high", "upper")
    verdict = str(result.get("verdict") or result.get("decision") or "REVIEW").upper()
    reason = str(result.get("verdict_reason") or result.get("interpretation") or result.get("warning") or "Review the method-specific result and diagnostics.")
    threshold = _first(result, "business_threshold", "threshold")
    warnings = result.get("warnings") or []
    if isinstance(warnings, str):
        warnings = [warnings]

    integrity: list[dict[str, str]] = []
    if "srm_status" in result:
        status = "pass" if result["srm_status"] == "pass" else "fail"
        integrity.append({"name": "Sample ratio", "status": status, "detail": f"SRM status: {result['srm_status']}."})
    if "robustness_status" in result:
        raw = str(result["robustness_status"])
        status = "pass" if raw == "robust" else "fail" if raw == "integrity_risk" else "warning"
        integrity.append({"name": "Robustness cross-check", "status": status, "detail": f"Robustness status: {raw}."})
    if not integrity:
        integrity.append({"name": "Method diagnostics", "status": "not_available", "detail": "Read the method-specific diagnostics in the preserved raw result."})

    unit = "proportion difference" if method_id == "analyze_binary_ab" else str(result.get("effect_unit") or "source units")
    estimand = {
        "analyze_binary_ab": "Treatment-minus-control conversion-rate difference",
        "analyze_continuous_ab_dataset": "Treatment-minus-control mean difference",
        "analyze_cuped": "CUPED-adjusted treatment-minus-control mean difference",
        "run_difference_in_differences": "Difference-in-Differences treatment effect",
        "run_event_study": "Treatment effect by relative time",
        "run_interrupted_time_series": "Level and slope change after intervention",
    }.get(method_id, str(result.get("estimand") or f"Primary result from {method_id}"))

    return {
        "version": ANALYTICAL_RESULT_VERSION,
        "method_id": method_id,
        "question": question.strip(),
        "status": "blocked" if result.get("status") == "blocked" else "complete",
        "estimand": estimand,
        "estimate": {"value": estimate, "unit": unit, "direction": _direction(estimate)},
        "uncertainty": {
            "kind": "confidence_interval" if low is not None and high is not None else "method_specific",
            "level": 0.95 if low is not None and high is not None else None,
            "low": low,
            "high": high,
        },
        "decision": {"verdict": verdict, "business_threshold": threshold, "reason": reason},
        "integrity_checks": integrity,
        "assumptions": [str(x) for x in (result.get("assumptions") or [])],
        "warnings": [str(x) for x in warnings],
        "provenance": {"deterministic": True, "engine": method_id, "raw_result_preserved": True},
    }
