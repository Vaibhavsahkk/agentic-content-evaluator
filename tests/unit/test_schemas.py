import pytest
from pydantic import ValidationError
from backend.app.schemas.evaluation import (
    RubricCheckpointResult,
    LLMEvaluationResponse,
    MANDATORY_CHECKPOINT_IDS
)
from backend.app.schemas.reference import ReferenceQuery
from backend.app.schemas.lesson import LessonDraft, LessonSection

def test_rubric_checkpoint_strict_bool():
    # Valid boolean
    valid = RubricCheckpointResult(
        checkpoint_id="accurate_and_grounded",
        passed=True,
        evidence="Accurate citation of REF-01"
    )
    assert valid.passed is True

    # Coercion rejection: string "true" or "yes" or 1 must fail strict bool validation
    with pytest.raises(ValidationError):
        RubricCheckpointResult(
            checkpoint_id="accurate_and_grounded",
            passed="true",  # type: ignore
            evidence="Evidence"
        )

def test_failed_checkpoint_requires_reason_and_correction():
    # If passed is False, failure_reason and correction_instruction cannot be empty
    with pytest.raises(ValidationError) as exc:
        RubricCheckpointResult(
            checkpoint_id="teaches_by_example",
            passed=False,
            evidence="No example found",
            failure_reason="",
            correction_instruction=""
        )
    assert "failure_reason was empty" in str(exc.value)

def test_llm_evaluation_response_mandatory_checkpoints():
    # All 6 checkpoints must be present
    checkpoints = [
        RubricCheckpointResult(
            checkpoint_id=cid,
            passed=True,
            evidence="Valid"
        )
        for cid in MANDATORY_CHECKPOINT_IDS
    ]
    resp = LLMEvaluationResponse(checkpoints=checkpoints, evaluator_summary="All passed")
    assert len(resp.checkpoints) == 6

    # Missing a checkpoint must raise ValidationError
    with pytest.raises(ValidationError) as exc:
        LLMEvaluationResponse(checkpoints=checkpoints[:5], evaluator_summary="Incomplete")
    assert "missing mandatory checkpoints" in str(exc.value)

    # Duplicate checkpoint ID must raise ValidationError
    duplicated = checkpoints + [checkpoints[0]]
    with pytest.raises(ValidationError) as exc:
        LLMEvaluationResponse(checkpoints=duplicated, evaluator_summary="Duplicate")
    assert "Duplicate checkpoint IDs detected" in str(exc.value)

def test_reference_query_bounds():
    # Valid query
    q = ReferenceQuery(query="vector embedding", max_results=3)
    assert q.max_results == 3

    # Exceeding upper bound of 5 must raise ValidationError
    with pytest.raises(ValidationError):
        ReferenceQuery(query="vector embedding", max_results=10)

    # Empty query must raise ValidationError
    with pytest.raises(ValidationError):
        ReferenceQuery(query="", max_results=3)

def test_lesson_draft_full_text():
    draft = LessonDraft(
        title="Intro to RAG",
        target_audience="Class 12 student",
        summary="Overview of RAG",
        sections=[
            LessonSection(section_title="What is RAG", content="Content here", grounded_reference_ids=["REF-01"])
        ],
        worked_example="College handbook QA",
        key_takeaways=["RAG retrieves facts", "Does not retrain weights"],
        references_cited=["REF-01"],
        markdown_content="# Intro to RAG\nFull markdown text here that is sufficiently long."
    )
    assert "Intro to RAG" in draft.get_full_text()
