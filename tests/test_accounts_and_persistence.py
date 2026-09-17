from copy import deepcopy
import pytest

from core.auth import ANONYMOUS, identity_from_claims
from core.decision_repository import SQLiteDecisionRepository
from core.outcome_learning import observe_outcome
from engines.decision_kernel import decision_from_evidence


def _decision(call="Proceed."):
    return decision_from_evidence(
        question="Should we proceed?",
        analytical_result=None,
        call=call,
        next_action="Collect the required evidence.",
    )


def test_identity_requires_authenticated_stable_claims():
    assert identity_from_claims({}) == ANONYMOUS
    assert identity_from_claims({"is_logged_in": False, "email": "x@example.com"}) == ANONYMOUS
    identity = identity_from_claims({"is_logged_in": True, "sub": "abc", "email": "USER@example.com", "name": "User"})
    assert identity.authenticated is True
    assert identity.user_id == "oidc:abc"
    assert identity.email == "user@example.com"


def test_repository_isolates_users_and_upserts_decisions(tmp_path):
    repository = SQLiteDecisionRepository(tmp_path / "memory.db")
    decision = _decision()
    repository.save("user-a", decision)
    assert len(repository.list("user-a")) == 1
    assert repository.list("user-b") == []

    changed = deepcopy(decision)
    changed["call"] = "Changed call."
    repository.save("user-a", changed)
    assert len(repository.list("user-a")) == 1
    assert repository.list("user-a")[0]["call"] == "Changed call."


def test_repository_updates_outcomes_and_supports_deletion(tmp_path):
    repository = SQLiteDecisionRepository(tmp_path / "memory.db")
    decision = _decision()
    repository.save("user-a", decision)
    updated = repository.update_outcome(
        "user-a",
        decision["decision_id"],
        status="observed",
        actual_outcome="Revenue increased.",
    )
    assert updated["outcome_status"] == "observed"
    assert repository.list("user-a")[0]["actual_outcome"] == "Revenue increased."
    repository.delete("user-a", decision["decision_id"])
    assert repository.list("user-a") == []


def test_repository_rejects_unknown_outcome_status(tmp_path):
    repository = SQLiteDecisionRepository(tmp_path / "memory.db")
    decision = _decision()
    repository.save("user-a", decision)
    with pytest.raises(ValueError):
        repository.update_outcome("user-a", decision["decision_id"], status="invented")


def test_delete_all_never_crosses_user_boundary(tmp_path):
    repository = SQLiteDecisionRepository(tmp_path / "memory.db")
    repository.save("user-a", _decision("A"))
    repository.save("user-b", _decision("B"))
    repository.delete_all("user-a")
    assert repository.list("user-a") == []
    assert len(repository.list("user-b")) == 1


def test_repository_persists_observations_per_user(tmp_path):
    repository = SQLiteDecisionRepository(tmp_path / "memory.db")
    decision = _decision()
    observation = observe_outcome(decision, actual_value=2.0)
    repository.save_observation("user-a", observation)
    assert len(repository.list_observations("user-a")) == 1
    assert repository.list_observations("user-b") == []


def test_delete_decision_also_deletes_its_observations(tmp_path):
    repository = SQLiteDecisionRepository(tmp_path / "memory.db")
    decision = _decision()
    repository.save("user-a", decision)
    repository.save_observation("user-a", observe_outcome(decision, actual_value=2.0))
    repository.delete("user-a", decision["decision_id"])
    assert repository.list("user-a") == []
    assert repository.list_observations("user-a") == []


def test_repository_healthcheck_reports_local_boundary(tmp_path):
    health = SQLiteDecisionRepository(tmp_path / "memory.db").healthcheck()
    assert health["ok"] is True
    assert health["backend"] == "sqlite"
    assert health["production_multi_tenant"] is False
