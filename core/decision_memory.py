"""Small session-backed decision memory for the pre-account CampaignLab beta."""

from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, MutableMapping


MEMORY_KEY = "decision_memory"


def remember_decision(state: MutableMapping[str, Any], decision: dict[str, Any], *, limit: int = 50) -> list[dict[str, Any]]:
    records = list(state.get(MEMORY_KEY) or [])
    record = deepcopy(decision)
    records = [item for item in records if item.get("decision_id") != record.get("decision_id")]
    records.insert(0, record)
    state[MEMORY_KEY] = records[:limit]
    return deepcopy(state[MEMORY_KEY])


def update_memory_outcome(
    state: MutableMapping[str, Any],
    decision_id: str,
    *,
    status: str,
    actual_outcome: str = "",
) -> dict[str, Any]:
    if status not in {"not_tracked", "planned", "acted", "observed"}:
        raise ValueError("Unsupported decision outcome status.")
    records = list(state.get(MEMORY_KEY) or [])
    for item in records:
        if item.get("decision_id") == decision_id:
            item["outcome_status"] = status
            item["actual_outcome"] = actual_outcome.strip()
            state[MEMORY_KEY] = records
            return deepcopy(item)
    raise KeyError("Decision is not in memory.")


def export_memory(state: MutableMapping[str, Any]) -> bytes:
    payload = {
        "format": "campaignlab-decision-memory",
        "version": "2.0",
        "decisions": state.get(MEMORY_KEY) or [],
        "outcome_observations": state.get("outcome_observations") or [],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def forget_decision(state: MutableMapping[str, Any], decision_id: str) -> None:
    state[MEMORY_KEY] = [item for item in (state.get(MEMORY_KEY) or []) if item.get("decision_id") != decision_id]
    state["outcome_observations"] = [item for item in (state.get("outcome_observations") or []) if item.get("decision_id") != decision_id]


def forget_all(state: MutableMapping[str, Any]) -> None:
    state[MEMORY_KEY] = []
    state["outcome_observations"] = []
