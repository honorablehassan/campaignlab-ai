"""Persistent Decision Memory repository.

SQLite is the local/default implementation. Production can replace this
repository behind the same interface with managed Postgres.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from typing import Any


def default_database_path() -> Path:
    configured = os.environ.get("CAMPAIGNLAB_DB_PATH", "").strip()
    return Path(configured) if configured else Path.cwd() / ".campaignlab" / "campaignlab.db"


class SQLiteDecisionRepository:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else default_database_path()

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS decisions (
                user_id TEXT NOT NULL,
                decision_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                source TEXT NOT NULL,
                outcome_status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                PRIMARY KEY (user_id, decision_id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS outcome_observations (
                user_id TEXT NOT NULL,
                decision_id TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                PRIMARY KEY (user_id, decision_id, observed_at)
            )
            """
        )
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass
        return connection

    def healthcheck(self) -> dict[str, Any]:
        with self._connect() as connection:
            integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
            decisions = int(connection.execute("SELECT COUNT(*) FROM decisions").fetchone()[0])
        return {"ok": integrity.lower() == "ok", "integrity": integrity, "decisions": decisions, "backend": "sqlite", "production_multi_tenant": False}

    def save(self, user_id: str, decision: dict[str, Any]) -> None:
        if not user_id.strip():
            raise ValueError("user_id is required.")
        payload = deepcopy(decision)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO decisions (user_id, decision_id, created_at, updated_at, source, outcome_status, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, decision_id) DO UPDATE SET
                    updated_at=excluded.updated_at,
                    source=excluded.source,
                    outcome_status=excluded.outcome_status,
                    payload_json=excluded.payload_json
                """,
                (
                    user_id,
                    str(payload["decision_id"]),
                    str(payload.get("created_at") or now),
                    now,
                    str(payload.get("source") or "CampaignLab"),
                    str(payload.get("outcome_status") or "not_tracked"),
                    json.dumps(payload, ensure_ascii=False),
                ),
            )

    def list(self, user_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM decisions WHERE user_id=? ORDER BY updated_at DESC LIMIT ?",
                (user_id, max(1, min(int(limit), 500))),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def update_outcome(self, user_id: str, decision_id: str, *, status: str, actual_outcome: str = "") -> dict[str, Any]:
        if status not in {"not_tracked", "planned", "acted", "observed"}:
            raise ValueError("Unsupported decision outcome status.")
        records = self.list(user_id, limit=500)
        record = next((item for item in records if item.get("decision_id") == decision_id), None)
        if record is None:
            raise KeyError("Decision is not in persistent memory.")
        record["outcome_status"] = status
        record["actual_outcome"] = actual_outcome.strip()
        self.save(user_id, record)
        return deepcopy(record)

    def delete(self, user_id: str, decision_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM outcome_observations WHERE user_id=? AND decision_id=?", (user_id, decision_id))
            connection.execute("DELETE FROM decisions WHERE user_id=? AND decision_id=?", (user_id, decision_id))

    def delete_all(self, user_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM decisions WHERE user_id=?", (user_id,))
            connection.execute("DELETE FROM outcome_observations WHERE user_id=?", (user_id,))

    def save_observation(self, user_id: str, observation: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO outcome_observations (user_id, decision_id, observed_at, payload_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, decision_id, observed_at) DO UPDATE SET payload_json=excluded.payload_json
                """,
                (
                    user_id,
                    str(observation["decision_id"]),
                    str(observation["observed_at"]),
                    json.dumps(observation, ensure_ascii=False),
                ),
            )

    def list_observations(self, user_id: str, *, limit: int = 500) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM outcome_observations WHERE user_id=? ORDER BY observed_at DESC LIMIT ?",
                (user_id, max(1, min(int(limit), 5000))),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]
