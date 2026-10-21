import pytest
from backend.app.graph.workflow import run_lesson_workflow
from backend.app.providers.mock_provider import MockProvider
from backend.app.database.repository import DatabaseRepository

def test_graph_first_attempt_pass():
    provider = MockProvider(simulate_eval_pass=True)
    result = run_lesson_workflow(
        topic="Introduction to RAG",
        enable_deliberate_error=False,
        provider=provider,
        max_retries=2
    )

    assert result["status"] == "PASSED"
    assert result["attempt_number"] == 1
    assert result["final_approved_lesson"] is not None
    assert "# Introduction to RAG" in result["final_approved_lesson"]
    assert len(result["rejection_log"]) == 0

    # Verify SQLite persistence
    run_record = DatabaseRepository.get_run(result["run_id"])
    assert run_record["status"] == "PASSED"
    assert run_record["attempts_count"] == 1

def test_graph_regeneration_recovery():
    # Attempt 1 fails on jargon, Attempt 2 passes
    class TwoAttemptProvider(MockProvider):
        def __init__(self):
            super().__init__()
            self.attempt = 0

        def generate_structured(self, messages, schema, model=None, temperature=0.1):
            self.attempt += 1
            if self.attempt == 1:
                # First attempt fails clear_no_unexplained_jargon
                self.simulate_eval_failures = ["clear_no_unexplained_jargon"]
            else:
                self.simulate_eval_failures = []
            return super().generate_structured(messages, schema, model, temperature)

    provider = TwoAttemptProvider()
    result = run_lesson_workflow(
        topic="Introduction to RAG",
        enable_deliberate_error=False,
        provider=provider,
        max_retries=2
    )

    assert result["status"] == "PASSED"
    assert result["attempt_number"] == 2
    assert result["final_approved_lesson"] is not None
    assert len(result["rejection_log"]) == 1
    assert "rubric:clear_no_unexplained_jargon" in result["rejection_log"][0]["failed_checkpoints"]

    # Verify DB rejection log
    db_rejections = DatabaseRepository.get_rejections_for_run(result["run_id"])
    assert len(db_rejections) == 1
    assert db_rejections[0].attempt_number == 1

def test_graph_exhaustion_terminates_failed():
    # Persistent failure across all 3 attempts
    provider = MockProvider(
        simulate_eval_pass=False,
        simulate_eval_failures=["accurate_and_grounded"]
    )
    result = run_lesson_workflow(
        topic="Introduction to RAG",
        enable_deliberate_error=False,
        provider=provider,
        max_retries=2  # Initial + 2 retries = 3 total attempts
    )

    assert result["status"] == "FAILED"
    assert result["attempt_number"] == 3
    # A failed lesson must NEVER be marked as approved!
    assert result["final_approved_lesson"] is None
    assert len(result["rejection_log"]) == 3

    # Check database
    run_record = DatabaseRepository.get_run(result["run_id"])
    assert run_record["status"] == "FAILED"
    assert run_record["approved_lesson"] is None
    assert run_record["attempts_count"] == 3
