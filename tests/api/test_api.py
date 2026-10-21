import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.repository import DatabaseRepository
from backend.app.providers.mock_provider import MockProvider

client = TestClient(app)

def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "groq_model" in data
    assert data["max_retries"] == 2

def test_generate_endpoint_mocked(monkeypatch):
    # Monkeypatch build_lesson_graph to use MockProvider
    from backend.app.graph import workflow
    original_build = workflow.build_lesson_graph

    def mock_build(provider=None):
        return original_build(provider=MockProvider(simulate_eval_pass=True))

    monkeypatch.setattr(workflow, "build_lesson_graph", mock_build)

    payload = {
        "topic": "Introduction to RAG",
        "enable_deliberate_error": False
    }
    resp = client.post("/api/generate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "PASSED"
    assert data["topic"] == "Introduction to RAG"
    assert data["approved_lesson"] is not None
    assert data["attempts_count"] == 1
    assert "run_id" in data

    run_id = data["run_id"]

    # Test run details endpoint
    resp_run = client.get(f"/api/runs/{run_id}")
    assert resp_run.status_code == 200
    run_data = resp_run.json()
    assert run_data["run_id"] == run_id
    assert len(run_data["attempts"]) == 1

    # Test rejections endpoint (0 rejections for clean pass)
    resp_rej = client.get(f"/api/runs/{run_id}/rejections")
    assert resp_rej.status_code == 200
    assert len(resp_rej.json()) == 0

def test_run_not_found():
    resp = client.get("/api/runs/non-existent-uuid-123")
    assert resp.status_code == 404

def test_rules_and_review():
    DatabaseRepository.add_or_increment_candidate_rule(
        category="tone",
        rule_text="Use encouraging language when defining complex words."
    )
    rules_resp = client.get("/api/rules")
    assert rules_resp.status_code == 200
    rules = rules_resp.json()
    assert len(rules) >= 1

    rule_id = rules[0]["id"]
    rev_resp = client.post(f"/api/rules/{rule_id}/review", json={"status": "APPROVED"})
    assert rev_resp.status_code == 200
    assert "APPROVED" in rev_resp.json()["message"]

def test_proposals_and_issues():
    # Test proposal creation
    prop_payload = {
        "target": "RUBRIC",
        "title": "Stricter Jargon Check",
        "description": "Require everyday analogies for embeddings",
        "proposed_diff": "+ Analogy requirement",
        "rationale": "Better support for vernacular learners"
    }
    prop_resp = client.post("/api/proposals", json=prop_payload)
    assert prop_resp.status_code == 200
    assert "proposal_id" in prop_resp.json()

    # Test content issue creation
    issue_payload = {
        "topic": "Introduction to RAG",
        "issue_type": "OUTDATED_CONCEPT",
        "description": "Old embedding library syntax in previous material"
    }
    issue_resp = client.post("/api/content-issues", json=issue_payload)
    assert issue_resp.status_code == 200
    assert "issue_id" in issue_resp.json()

def test_user_feedback():
    run_id = "test-feedback-run"
    DatabaseRepository.create_run(run_id=run_id, topic="Intro to RAG")
    fb_payload = {
        "run_id": run_id,
        "rating": 5,
        "comment": "Very clear analogies for Class 12 students!"
    }
    resp = client.post("/api/feedback", json=fb_payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "recorded"
