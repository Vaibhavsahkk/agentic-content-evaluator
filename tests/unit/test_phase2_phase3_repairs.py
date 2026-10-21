import os
import pytest
from backend.app.core.config import settings
from backend.app.core.security import validate_topic_input
from backend.app.database.repository import DatabaseRepository
from backend.app.graph.nodes import summarize_draft_changes
from backend.app.evaluation.deterministic import run_deterministic_checks

def test_f04_reconcile_orphaned_runs(setup_test_db):
    """F-04: Verify that abandoned PENDING runs are reconciled to FAILED on startup."""
    repo = DatabaseRepository()
    # Create an orphaned run
    run_id = "test-orphan-run-123"
    repo.create_run(run_id=run_id, topic="Introduction to RAG", deliberate_error_injected=False)
    
    # Verify initial state is PENDING with completed_at=None
    initial_run = repo.get_run(run_id)
    assert initial_run["status"] == "PENDING"
    assert initial_run["completed_at"] is None
    
    # Reconcile orphaned runs
    reconciled_count = repo.reconcile_orphaned_runs()
    assert reconciled_count >= 1
    
    # Verify updated state is FAILED with completed_at timestamp
    updated_run = repo.get_run(run_id)
    assert updated_run["status"] == "FAILED"
    assert updated_run["completed_at"] is not None

def test_f10_topic_grounding_validation():
    """F-10: Verify that topic input requires RAG-related keywords to avoid out-of-domain failures."""
    # Valid RAG topics
    is_valid, topic = validate_topic_input("Introduction to RAG")
    assert is_valid is True
    assert topic == "Introduction to RAG"
    
    is_valid, topic = validate_topic_input("Retrieval-Augmented Generation basics")
    assert is_valid is True
    assert topic == "Retrieval-Augmented Generation basics"
    
    is_valid, topic = validate_topic_input("rag pipeline architecture")
    assert is_valid is True
    assert topic == "rag pipeline architecture"
    
    # Out of domain topics must be rejected early with clear feedback
    is_valid, error = validate_topic_input("Photosynthesis in desert plants")
    assert is_valid is False
    assert "verified curriculum grounding scope" in error
    
    is_valid, error = validate_topic_input("Modern stock market trading algorithms")
    assert is_valid is False
    assert "verified curriculum grounding scope" in error

def test_f05_summarize_draft_changes():
    """F-05: Verify that draft changes diff produces meaningful summaries between attempts."""
    draft_v1 = (
        "# Introduction to RAG\n"
        "RAG retrains the language model's weights every time it retrieves a document.\n"
        "Chunking breaks texts into pieces."
    )
    draft_v2 = (
        "# Introduction to RAG\n"
        "Retrieval happens dynamically at inference time and does not retrain weights.\n"
        "Chunking breaks texts into pieces [REF-02]."
    )
    
    diff_summary = summarize_draft_changes(draft_v1, draft_v2)
    assert "Removed factually false claim asserting that RAG retrains neural network weights" in diff_summary
    assert "Added primary reference citations: [REF-02]" in diff_summary

def test_f14_f15_lesson_citations_and_references():
    """F-14 & F-15: Verify that artifacts/lesson.md contains all 4 citations, disclaimer, and references table."""
    lesson_path = os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "lesson.md")
    assert os.path.exists(lesson_path), "artifacts/lesson.md must exist"
    
    with open(lesson_path, "r", encoding="utf-8") as f:
        lesson_text = f.read()
        
    # All 4 reference IDs must be cited
    assert "[REF-01]" in lesson_text
    assert "[REF-02]" in lesson_text
    assert "[REF-03]" in lesson_text
    assert "[REF-04]" in lesson_text
    
    # Fictional disclaimer must be present in Section 4
    assert "fictional illustrative example" in lesson_text.lower()
    
    # References table must be present
    assert "References" in lesson_text
    assert "https://arxiv.org/abs/2005.11401" in lesson_text
    assert "https://docs.llamaindex.ai" in lesson_text
    
    # Deterministic checks must 100% pass on this lesson
    checks = run_deterministic_checks(lesson_text)
    failed_checks = [c for c in checks if not c.passed]
    assert len(failed_checks) == 0, f"Deterministic checks failed: {failed_checks}"
