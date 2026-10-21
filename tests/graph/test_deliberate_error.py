import pytest
from backend.app.graph.workflow import run_lesson_workflow
from backend.app.providers.mock_provider import MockProvider
from backend.app.database.repository import DatabaseRepository

def test_deliberate_error_injection_and_recovery_loop():
    """
    Validates the end-to-end error injection and recovery loop:
    1. Deliberate false claim injected on Attempt 1.
    2. Deterministic and rubric checks detect the false claim.
    3. Workflow records rejection with evidence and correction instruction.
    4. Feedback fed to regeneration.
    5. Attempt 2 does NOT reinject error.
    6. Re-evaluated anew and approved.
    """
    # Provider that outputs clean lesson when not injected
    provider = MockProvider(simulate_eval_pass=True)

    result = run_lesson_workflow(
        topic="Introduction to RAG",
        enable_deliberate_error=True,
        provider=provider,
        max_retries=2
    )

    # Must complete successfully on Attempt 2
    assert result["status"] == "PASSED"
    assert result["attempt_number"] == 2
    assert result["final_approved_lesson"] is not None

    # Rejection log must show Attempt 1 caught the error
    assert len(result["rejection_log"]) == 1
    rejection_1 = result["rejection_log"][0]
    assert rejection_1["attempt_number"] == 1
    assert "deterministic:check_controlled_false_claim" in rejection_1["failed_checkpoints"]
    assert any("retrains model weights" in r.lower() for r in rejection_1["reasons"])

    # Verify SQLite database
    db_rejections = DatabaseRepository.get_rejections_for_run(result["run_id"])
    assert len(db_rejections) == 1
    assert "deterministic:check_controlled_false_claim" in db_rejections[0].failed_checkpoints

    attempts = DatabaseRepository.get_attempts_for_run(result["run_id"])
    assert len(attempts) == 2
    assert attempts[0]["status"] == "REJECTED"
    assert attempts[1]["status"] == "PASSED"
