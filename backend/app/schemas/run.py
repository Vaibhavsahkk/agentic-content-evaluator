from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from backend.app.schemas.evaluation import RejectionRecord, DeterministicCheckResult, RubricCheckpointResult

class RunCreateRequest(BaseModel):
    topic: str = Field(default="Introduction to RAG", description="Topic for lesson generation")
    enable_deliberate_error: bool = Field(default=False, description="Flag for test demonstration: inject controlled false claim to verify evaluation gate")

class RunAttempt(BaseModel):
    attempt_number: int
    draft_title: str
    draft_markdown: str
    status: Literal["PASSED", "REJECTED", "FAILED"]
    deterministic_checks: List[DeterministicCheckResult]
    rubric_checkpoints: List[RubricCheckpointResult]
    feedback_for_regeneration: Optional[str] = None
    created_at: str

class RunResponse(BaseModel):
    run_id: str
    topic: str
    status: Literal["PENDING", "IN_PROGRESS", "PASSED", "FAILED"]
    attempts_count: int
    max_retries: int
    approved_lesson: Optional[str] = None
    deliberate_error_injected: bool
    rejection_log: List[RejectionRecord]
    attempts: List[RunAttempt]
    metrics: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    completed_at: Optional[str] = None

class RunSummary(BaseModel):
    run_id: str
    topic: str
    status: str
    attempts_count: int
    deliberate_error_injected: bool
    created_at: str
    completed_at: Optional[str] = None
