import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Body, status
from pydantic import BaseModel, Field

from backend.app.schemas.run import RunCreateRequest, RunResponse, RunSummary, RunAttempt
from backend.app.schemas.evaluation import RejectionRecord
from backend.app.schemas.evolution import LearnedRule, ImprovementProposal, ContentIssue, UserFeedback
from backend.app.database.repository import DatabaseRepository
from backend.app.graph.workflow import run_lesson_workflow
from backend.app.core.config import settings
from backend.app.core.logging import logger

router = APIRouter()

class ReviewStatusRequest(BaseModel):
    status: str = Field(description="New status, e.g. APPROVED or REJECTED")

class IssueStatusUpdateRequest(BaseModel):
    status: str = Field(description="New status, e.g. INVESTIGATING or RESOLVED")
    resolution_notes: Optional[str] = None

class FeedbackCreateRequest(BaseModel):
    run_id: str
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None

class ProposalCreateRequest(BaseModel):
    target: str = Field(description="PROMPT or RUBRIC")
    title: str
    description: str
    proposed_diff: str
    rationale: str

class ContentIssueCreateRequest(BaseModel):
    topic: str
    issue_type: str = Field(description="OUTDATED_CONCEPT, DEPRECATED_LIBRARY, WRONG_SYNTAX, BROKEN_EXAMPLE")
    description: str

@router.get("/health", tags=["System"])
def health_check():
    """Health check endpoint reporting API, database, and model provider status."""
    db_ok = False
    try:
        from backend.app.database.connection import get_db_connection
        with get_db_connection() as conn:
            conn.execute("SELECT 1").fetchone()
            db_ok = True
    except Exception as e:
        logger.error(f"Health check DB ping failed: {e}")

    return {
        "status": "healthy" if db_ok else "degraded",
        "database_connected": db_ok,
        "environment": settings.ENVIRONMENT,
        "groq_configured": bool(settings.GROQ_API_KEY),
        "groq_model": settings.GROQ_MODEL,
        "judge_model": settings.GROQ_JUDGE_MODEL,
        "langsmith_tracing": settings.LANGSMITH_TRACING,
        "max_retries": settings.MAX_RETRIES
    }

@router.post("/api/generate", response_model=RunResponse, tags=["Generator"])
def generate_lesson_endpoint(payload: RunCreateRequest):
    """
    Executes the full LangGraph agentic generation and evaluation state machine.
    Generates, evaluates against 6 mandatory dimensions, and regenerates on failure (up to MAX_RETRIES).
    """
    try:
        final_state = run_lesson_workflow(
            topic=payload.topic,
            enable_deliberate_error=payload.enable_deliberate_error,
            max_retries=settings.MAX_RETRIES
        )
    except Exception as e:
        logger.error(f"Pipeline execution error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline error: {str(e)}"
        )

    run_id = final_state["run_id"]
    attempts_data = DatabaseRepository.get_attempts_for_run(run_id)
    rejections = DatabaseRepository.get_rejections_for_run(run_id)

    formatted_attempts = [
        RunAttempt(
            attempt_number=a["attempt_number"],
            draft_title=a["draft_title"],
            draft_markdown=a["draft_markdown"],
            status=a["status"],
            deterministic_checks=a["deterministic_checks"],
            rubric_checkpoints=a["rubric_checkpoints"],
            feedback_for_regeneration=a["feedback_for_regeneration"],
            created_at=a["created_at"]
        )
        for a in attempts_data
    ]

    return RunResponse(
        run_id=run_id,
        topic=final_state["topic"],
        status=final_state["status"],
        attempts_count=final_state.get("attempt_number", len(formatted_attempts)),
        max_retries=settings.MAX_RETRIES,
        approved_lesson=final_state.get("final_approved_lesson"),
        deliberate_error_injected=payload.enable_deliberate_error,
        rejection_log=rejections,
        attempts=formatted_attempts,
        metrics={
            "attempts_made": len(formatted_attempts),
            "rejections_count": len(rejections),
            "terminal_passed": final_state["status"] == "PASSED"
        },
        created_at=formatted_attempts[0].created_at if formatted_attempts else "",
        completed_at=final_state.get("completed_at")
    )

@router.get("/api/history", response_model=List[RunSummary], tags=["History"])
def get_run_history():
    """Returns recent lesson generation runs and summary outcomes."""
    runs = DatabaseRepository.get_all_runs(limit=50)
    summaries = []
    for r in runs:
        summaries.append(
            RunSummary(
                run_id=r["run_id"],
                topic=r["topic"],
                status=r["status"],
                attempts_count=r["attempts_count"],
                deliberate_error_injected=bool(r["deliberate_error_injected"]),
                created_at=r["created_at"],
                completed_at=r["completed_at"]
            )
        )
    return summaries

@router.get("/api/runs/{run_id}", response_model=RunResponse, tags=["History"])
def get_run_details(run_id: str):
    """Returns complete attempt history, deterministic checks, and rubric scores for a run."""
    run_record = DatabaseRepository.get_run(run_id)
    if not run_record:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")

    attempts_data = DatabaseRepository.get_attempts_for_run(run_id)
    rejections = DatabaseRepository.get_rejections_for_run(run_id)

    formatted_attempts = [
        RunAttempt(
            attempt_number=a["attempt_number"],
            draft_title=a["draft_title"],
            draft_markdown=a["draft_markdown"],
            status=a["status"],
            deterministic_checks=a["deterministic_checks"],
            rubric_checkpoints=a["rubric_checkpoints"],
            feedback_for_regeneration=a["feedback_for_regeneration"],
            created_at=a["created_at"]
        )
        for a in attempts_data
    ]

    return RunResponse(
        run_id=run_id,
        topic=run_record["topic"],
        status=run_record["status"],
        attempts_count=run_record["attempts_count"],
        max_retries=run_record["max_retries"],
        approved_lesson=run_record["approved_lesson"],
        deliberate_error_injected=bool(run_record["deliberate_error_injected"]),
        rejection_log=rejections,
        attempts=formatted_attempts,
        metrics={
            "attempts_made": len(formatted_attempts),
            "rejections_count": len(rejections)
        },
        created_at=run_record["created_at"],
        completed_at=run_record["completed_at"]
    )

@router.get("/api/runs/{run_id}/rejections", response_model=List[RejectionRecord], tags=["Rejection Logs"])
def get_run_rejections(run_id: str):
    """Returns specific rejection records explaining what failed, why, and what was changed on retry."""
    return DatabaseRepository.get_rejections_for_run(run_id)

# Self-Evolution & Memory Endpoints
@router.get("/api/rules", response_model=List[LearnedRule], tags=["Self-Evolution"])
def get_rules():
    """Returns learned editorial guidance rules persisted across runs."""
    return DatabaseRepository.get_all_rules()

@router.post("/api/rules/{rule_id}/review", tags=["Self-Evolution"])
def review_rule(rule_id: int, payload: ReviewStatusRequest):
    """Approve or reject a candidate learned rule."""
    if payload.status not in ["APPROVED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Status must be APPROVED or REJECTED.")
    success = DatabaseRepository.update_rule_status(rule_id, payload.status)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found.")
    return {"message": f"Rule {rule_id} marked as {payload.status}."}

# Improvement Proposals
@router.get("/api/proposals", response_model=List[ImprovementProposal], tags=["Self-Evolution"])
def get_proposals():
    """Returns prompt and rubric improvement proposals."""
    return DatabaseRepository.get_improvement_proposals()

@router.post("/api/proposals", response_model=Dict[str, Any], tags=["Self-Evolution"])
def create_proposal(payload: ProposalCreateRequest):
    """Create a new candidate improvement proposal."""
    pid = DatabaseRepository.add_improvement_proposal(
        target=payload.target,
        title=payload.title,
        description=payload.description,
        proposed_diff=payload.proposed_diff,
        rationale=payload.rationale
    )
    return {"proposal_id": pid, "status": "PENDING"}

@router.post("/api/proposals/{proposal_id}/review", tags=["Self-Evolution"])
def review_proposal(proposal_id: int, payload: ReviewStatusRequest):
    """Review and approve/reject an improvement proposal."""
    if payload.status not in ["APPROVED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Status must be APPROVED or REJECTED.")
    success = DatabaseRepository.update_proposal_status(proposal_id, payload.status)
    if not success:
        raise HTTPException(status_code=404, detail="Proposal not found.")
    return {"message": f"Proposal {proposal_id} marked as {payload.status}."}

# Content Freshness & Issues
@router.get("/api/content-issues", response_model=List[ContentIssue], tags=["Content Maintenance"])
def get_content_issues():
    """Returns tracked issues for outdated concepts, deprecated libraries, or broken syntax."""
    return DatabaseRepository.get_content_issues()

@router.post("/api/content-issues", tags=["Content Maintenance"])
def create_content_issue(payload: ContentIssueCreateRequest):
    """Record an identified content defect or freshness issue."""
    issue_id = DatabaseRepository.add_content_issue(
        topic=payload.topic,
        issue_type=payload.issue_type,
        description=payload.description
    )
    return {"issue_id": issue_id, "status": "OPEN"}

@router.post("/api/content-issues/{issue_id}/status", tags=["Content Maintenance"])
def update_issue_status(issue_id: int, payload: IssueStatusUpdateRequest):
    """Update content issue status and investigation resolution notes."""
    success = DatabaseRepository.update_content_issue(
        issue_id=issue_id,
        status=payload.status,
        resolution_notes=payload.resolution_notes
    )
    if not success:
        raise HTTPException(status_code=404, detail="Content issue not found.")
    return {"message": f"Issue {issue_id} updated to {payload.status}."}

# User Feedback
@router.post("/api/feedback", tags=["Feedback"])
def submit_feedback(payload: FeedbackCreateRequest):
    """Submit rating and comments on generated lessons to guide continuous improvement."""
    fid = DatabaseRepository.add_user_feedback(
        run_id=payload.run_id,
        rating=payload.rating,
        comment=payload.comment
    )
    return {"feedback_id": fid, "status": "recorded"}

# Artifact export
@router.get("/api/artifacts/lesson", tags=["Export"])
def get_approved_lesson_file():
    """Returns the markdown text of the latest approved lesson artifact."""
    artifact_path = Path(__file__).resolve().parent.parent.parent.parent / "artifacts" / "lesson.md"
    if not artifact_path.exists():
        raise HTTPException(status_code=404, detail="No approved lesson artifact found.")
    with open(artifact_path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"content": content, "filename": "lesson.md"}
