import pytest
from backend.app.database.repository import DatabaseRepository
from backend.app.schemas.evaluation import DeterministicCheckResult, RubricCheckpointResult

def test_database_crud_lifecycle():
    run_id = "test-run-101"
    topic = "Introduction to RAG"
    
    # 1. Create Run
    DatabaseRepository.create_run(
        run_id=run_id,
        topic=topic,
        deliberate_error_injected=False,
        max_retries=2
    )
    
    run = DatabaseRepository.get_run(run_id)
    assert run is not None
    assert run["run_id"] == run_id
    assert run["topic"] == topic
    assert run["status"] == "PENDING"
    assert run["attempts_count"] == 0

    # 2. Record Attempt 1 (Rejected)
    attempt_id = DatabaseRepository.record_attempt(
        run_id=run_id,
        attempt_number=1,
        draft_title="RAG Lesson Draft 1",
        draft_markdown="# Lesson Draft 1",
        status="REJECTED",
        feedback_for_regeneration="Explain embeddings in simpler English."
    )
    assert attempt_id > 0

    # Record deterministic check
    det_checks = [
        DeterministicCheckResult(
            check_id="check_sections",
            name="Required Sections",
            passed=True
        ),
        DeterministicCheckResult(
            check_id="check_jargon",
            name="Unexplained Jargon",
            passed=False,
            failure_reason="Used 'vector space' without beginner definition."
        )
    ]
    DatabaseRepository.record_deterministic_checks(attempt_id, det_checks)

    # Record rubric checks
    rub_checks = [
        RubricCheckpointResult(
            checkpoint_id="clear_no_unexplained_jargon",
            passed=False,
            evidence="Used 'high-dimensional latent space'",
            failure_reason="Too complex for class 12 beginner",
            correction_instruction="Define embeddings as number tags"
        )
    ]
    DatabaseRepository.record_rubric_checks(attempt_id, rub_checks)

    # Record rejection log
    DatabaseRepository.record_rejection_log(
        run_id=run_id,
        attempt_number=1,
        failed_checkpoints=["clear_no_unexplained_jargon"],
        reasons=["Too complex for class 12 beginner"],
        corrective_instructions=["Define embeddings as number tags"],
        changes_required="Simplify vocabulary",
        draft_snippet="# Lesson Draft 1..."
    )

    rejections = DatabaseRepository.get_rejections_for_run(run_id)
    assert len(rejections) == 1
    assert rejections[0].attempt_number == 1
    assert "clear_no_unexplained_jargon" in rejections[0].failed_checkpoints

    # 3. Record Attempt 2 (Passed)
    attempt_2_id = DatabaseRepository.record_attempt(
        run_id=run_id,
        attempt_number=2,
        draft_title="RAG Lesson Draft 2",
        draft_markdown="# Final Passing Lesson",
        status="PASSED"
    )
    assert attempt_2_id > attempt_id

    DatabaseRepository.update_run_status(
        run_id=run_id,
        status="PASSED",
        approved_lesson="# Final Passing Lesson",
        attempts_count=2
    )

    updated_run = DatabaseRepository.get_run(run_id)
    assert updated_run["status"] == "PASSED"
    assert updated_run["attempts_count"] == 2
    assert updated_run["approved_lesson"] == "# Final Passing Lesson"

def test_learned_rules_and_proposals():
    # Test candidate rule addition
    DatabaseRepository.add_or_increment_candidate_rule(
        category="jargon",
        rule_text="Always compare embeddings to book library index cards."
    )
    rules = DatabaseRepository.get_all_rules()
    assert len(rules) == 1
    assert rules[0].status == "CANDIDATE"
    assert rules[0].evidence_count == 1

    # Increment evidence on recurrence
    DatabaseRepository.add_or_increment_candidate_rule(
        category="jargon",
        rule_text="Always compare embeddings to book library index cards."
    )
    rules_updated = DatabaseRepository.get_all_rules()
    assert rules_updated[0].evidence_count == 2

    # Approve rule
    rule_id = rules_updated[0].id
    assert DatabaseRepository.update_rule_status(rule_id, "APPROVED") is True
    approved = DatabaseRepository.get_approved_rules()
    assert len(approved) == 1
    assert approved[0].status == "APPROVED"

    # Test improvement proposal
    prop_id = DatabaseRepository.add_improvement_proposal(
        target="PROMPT",
        title="Clarify chunking analogy",
        description="Add paragraph on slicing chapters into pages",
        proposed_diff="+ Add analogy",
        rationale="Helps non-English background learners"
    )
    assert prop_id > 0
    props = DatabaseRepository.get_improvement_proposals()
    assert len(props) == 1
    assert props[0].status == "PENDING"
    assert DatabaseRepository.update_proposal_status(prop_id, "APPROVED") is True
