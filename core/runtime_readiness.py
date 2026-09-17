"""Truthful deployment checks; these report capability rather than implying it."""

from __future__ import annotations

import os
from typing import Any

from core.auth import auth_configured
from core.decision_repository import SQLiteDecisionRepository


def deployment_readiness() -> dict[str, Any]:
    checks: list[dict[str, str]] = []
    api = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    checks.append({"name": "OpenAI secret", "status": "ready" if api else "local_action", "detail": "Configured through the environment." if api else "Add OPENAI_API_KEY through deployment secrets to enable AI reasoning."})
    auth = auth_configured()
    checks.append({"name": "Account identity", "status": "ready" if auth else "optional", "detail": "OIDC is configured." if auth else "Anonymous session mode is active; configure Streamlit OIDC before multi-user launch."})
    try:
        database = SQLiteDecisionRepository().healthcheck()
        db_ok = bool(database["ok"])
        detail = "Local SQLite integrity check passed. Replace it with managed encrypted storage and database-layer authorization before multi-instance SaaS." if db_ok else f"SQLite integrity check returned {database['integrity']}."
    except Exception as exc:
        db_ok = False
        detail = f"Decision Memory storage is unavailable: {exc}"
    checks.append({"name": "Decision storage", "status": "local_only" if db_ok else "blocked", "detail": detail})
    checks.append({"name": "Evidence retention", "status": "ready", "detail": "Uploaded evidence is processed in memory and raw rows are not written to CampaignLab telemetry."})
    production_ready = all(item["status"] == "ready" for item in checks)
    return {"production_ready": production_ready, "checks": checks}
