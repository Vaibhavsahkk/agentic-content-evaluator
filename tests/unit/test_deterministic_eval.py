import pytest
from backend.app.evaluation.deterministic import run_deterministic_checks

def test_deterministic_empty_draft():
    results = run_deterministic_checks("")
    assert len(results) == 1
    assert results[0].check_id == "check_non_empty"
    assert results[0].passed is False

def test_deterministic_controlled_false_claim_detected():
    text = (
        "# Introduction to RAG\n\n"
        "## 1. What is RAG\nRAG is an AI technique.\n\n"
        "## 2. Why RAG Matters\nRAG retrains the language model's weights every time it retrieves a document from the external knowledge base.\n\n"
        "## 3. How RAG Works\nWe retrieve chunks.\n\n"
        "## 4. Worked Example\nA student queries the college library.\n\n"
        "## 5. Limitations\nSome limits exist.\n\n"
        "## 6. Key Takeaways\nRecap points [REF-01]."
    )
    results = run_deterministic_checks(text)
    false_claim_check = next(r for r in results if r.check_id == "check_controlled_false_claim")
    assert false_claim_check.passed is False
    assert "Claimed that RAG retrains model weights" in false_claim_check.failure_reason

def test_deterministic_negated_claim_passes():
    text = (
        "# Introduction to RAG\n\n"
        "## 1. What is RAG\nRAG stands for Retrieval-Augmented Generation [REF-01].\n\n"
        "## 2. Why RAG Matters\nIt allows models to answer from fresh documents.\n\n"
        "## 3. How RAG Works\nIt uses chunking and vector embeddings [REF-02].\n\n"
        "## 4. Worked Example\nIn our college library, a student checks book renewal fees.\n\n"
        "## 5. Limitations\nCrucially, RAG does not retrain the language model's weights every time it retrieves a document [REF-01].\n\n"
        "## 6. Key Takeaways\nRecap of points [REF-03]."
    )
    results = run_deterministic_checks(text)
    false_claim_check = next(r for r in results if r.check_id == "check_controlled_false_claim")
    assert false_claim_check.passed is True

def test_deterministic_missing_sections():
    # Only What is RAG, missing other 5 sections
    text = "# Introduction to RAG\n\n## 1. What is RAG\nRAG retrieves data [REF-01]. " * 10
    results = run_deterministic_checks(text)
    section_check = next(r for r in results if r.check_id == "check_required_sections")
    assert section_check.passed is False
    assert "Missing mandatory sections" in section_check.failure_reason

def test_deterministic_invalid_reference_citation():
    text = (
        "# Introduction to RAG\n\n"
        "## 1. What is RAG\nRAG is great [REF-999].\n\n"
        "## 2. Why RAG Matters\nFacts matter.\n\n"
        "## 3. How RAG Works\nSteps here.\n\n"
        "## 4. Worked Example\nA college student queries a policy.\n\n"
        "## 5. Limitations\nLimits.\n\n"
        "## 6. Key Takeaways\nRecap."
    )
    results = run_deterministic_checks(text)
    ref_check = next(r for r in results if r.check_id == "check_reference_citations")
    assert ref_check.passed is False
    assert "REF-999" in ref_check.failure_reason
