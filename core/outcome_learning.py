"""Compare CampaignLab predictions with reality and summarize calibration."""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean
from typing import Any

from schemas.outcome import OUTCOME_OBSERVATION_VERSION


def _actual_direction(value: float) -> str:
    if value > 0:
        return "increase"
    if value < 0:
        return "decrease"
    return "no_change"


def observe_outcome(decision: dict[str, Any], *, actual_value: float, notes: str = "") -> dict[str, Any]:
    prediction = decision.get("prediction") or {}
    predicted = prediction.get("point")
    low, high = prediction.get("low"), prediction.get("high")
    predicted_direction = str(prediction.get("direction") or "unknown")
    direction_correct = None if predicted_direction == "unknown" else predicted_direction == _actual_direction(float(actual_value))
    error = None if predicted is None else float(actual_value) - float(predicted)
    inside = None if low is None or high is None else float(low) <= float(actual_value) <= float(high)
    if predicted is None:
        label = "Outcome recorded; the original decision had no numeric prediction to score."
    elif direction_correct and (inside is not False):
        label = "Prediction was directionally correct" + (" and inside its stated interval." if inside else ".")
    elif direction_correct:
        label = "Direction was correct, but magnitude fell outside the stated interval."
    else:
        label = "Reality moved against the predicted direction."
    return {
        "version": OUTCOME_OBSERVATION_VERSION,
        "decision_id": str(decision["decision_id"]),
        "source": str(decision.get("source") or "CampaignLab"),
        "observed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metric": str(prediction.get("metric") or "decision outcome"),
        "predicted_direction": predicted_direction,
        "predicted_value": float(predicted) if predicted is not None else None,
        "predicted_low": float(low) if low is not None else None,
        "predicted_high": float(high) if high is not None else None,
        "actual_value": float(actual_value),
        "unit": str(prediction.get("unit") or "source units"),
        "notes": notes.strip(),
        "score": {"direction_correct": direction_correct, "error": error, "inside_interval": inside, "label": label},
    }


def calibration_summary(observations: list[dict[str, Any]]) -> dict[str, Any]:
    scored_direction = [x["score"]["direction_correct"] for x in observations if x.get("score", {}).get("direction_correct") is not None]
    errors = [float(x["score"]["error"]) for x in observations if x.get("score", {}).get("error") is not None]
    intervals = [x["score"]["inside_interval"] for x in observations if x.get("score", {}).get("inside_interval") is not None]
    return {
        "observations": len(observations),
        "direction_accuracy": mean(scored_direction) if scored_direction else None,
        "mean_error": mean(errors) if errors else None,
        "mean_absolute_error": mean(abs(x) for x in errors) if errors else None,
        "interval_coverage": mean(intervals) if intervals else None,
        "enough_for_pattern": len(observations) >= 10,
        "warning": "Fewer than 10 observed decisions: treat this as history, not a stable calibration estimate." if len(observations) < 10 else "Calibration summary is descriptive and may still reflect selection bias in which outcomes were recorded.",
    }
