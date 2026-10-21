from typing import Optional, Literal
from pydantic import BaseModel, Field

class LearnedRule(BaseModel):
    id: Optional[int] = None
    category: str = Field(description="Failure pattern category (e.g. jargon, example_depth, grounding)")
    rule_text: str = Field(description="Actionable guidance rule for generation")
    evidence_count: int = Field(default=1, description="Number of observed recurring failures")
    status: Literal["CANDIDATE", "APPROVED", "REJECTED"] = Field(default="CANDIDATE")
    created_at: str
    approved_at: Optional[str] = None

class ImprovementProposal(BaseModel):
    id: Optional[int] = None
    target: Literal["PROMPT", "RUBRIC"]
    title: str
    description: str
    proposed_diff: str
    rationale: str
    status: Literal["PENDING", "APPROVED", "REJECTED"] = Field(default="PENDING")
    created_at: str
    reviewed_at: Optional[str] = None

class ContentIssue(BaseModel):
    id: Optional[int] = None
    topic: str
    issue_type: Literal["OUTDATED_CONCEPT", "DEPRECATED_LIBRARY", "WRONG_SYNTAX", "BROKEN_EXAMPLE"]
    description: str
    status: Literal["OPEN", "INVESTIGATING", "RESOLVED"] = Field(default="OPEN")
    detected_at: str
    resolved_at: Optional[str] = None
    resolution_notes: Optional[str] = None

class UserFeedback(BaseModel):
    id: Optional[int] = None
    run_id: str
    rating: int = Field(ge=1, le=5, description="1 to 5 rating")
    comment: Optional[str] = None
    created_at: str
