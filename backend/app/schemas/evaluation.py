from typing import List, Optional, Literal
from pydantic import BaseModel, Field, StrictBool, model_validator

# The six mandatory rubric dimensions required by the evaluation specification
MANDATORY_CHECKPOINT_IDS = [
    "accurate_and_grounded",
    "beginner_friendly_language",
    "teaches_by_example",
    "clear_no_unexplained_jargon",
    "covers_the_key_points",
    "coherent_teaching_flow"
]

RubricCheckpointId = Literal[
    "accurate_and_grounded",
    "beginner_friendly_language",
    "teaches_by_example",
    "clear_no_unexplained_jargon",
    "covers_the_key_points",
    "coherent_teaching_flow"
]

class RubricCheckpointResult(BaseModel):
    checkpoint_id: RubricCheckpointId = Field(description="Must match one of the 6 mandatory checkpoint IDs exactly")
    passed: StrictBool = Field(description="Strict boolean pass/fail with no partial credit")
    evidence: str = Field(description="Direct citation or reasoning from the lesson draft")
    failure_reason: Optional[str] = Field(default=None, description="Detailed explanation if checkpoint failed")
    correction_instruction: Optional[str] = Field(default=None, description="Actionable instruction for the generator on regeneration")
    evidence_span: Optional[str] = Field(default=None, description="Exact text excerpt from the lesson if applicable")

    @model_validator(mode="after")
    def validate_failure_fields(self):
        if not self.passed:
            if not self.failure_reason or not self.failure_reason.strip():
                raise ValueError(f"Checkpoint '{self.checkpoint_id}' failed but failure_reason was empty.")
            if not self.correction_instruction or not self.correction_instruction.strip():
                raise ValueError(f"Checkpoint '{self.checkpoint_id}' failed but correction_instruction was empty.")
        return self

class LLMEvaluationResponse(BaseModel):
    checkpoints: List[RubricCheckpointResult] = Field(description="Exact list of evaluated checkpoints")
    evaluator_summary: str = Field(description="Summary of the evaluation across the 6 dimensions")

    @model_validator(mode="after")
    def validate_mandatory_checkpoints(self):
        ids = [c.checkpoint_id for c in self.checkpoints]
        missing = [req for req in MANDATORY_CHECKPOINT_IDS if req not in ids]
        if missing:
            raise ValueError(f"Evaluation missing mandatory checkpoints: {missing}")
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate checkpoint IDs detected in evaluation response: {ids}")
        if len(ids) != len(MANDATORY_CHECKPOINT_IDS) or set(ids) != set(MANDATORY_CHECKPOINT_IDS):
            raise ValueError(f"Evaluation must contain exactly the 6 mandatory checkpoints, received {len(ids)}: {ids}")
        return self

class DeterministicCheckResult(BaseModel):
    check_id: str
    name: str
    passed: bool
    failure_reason: Optional[str] = None
    details: Optional[str] = None

class RejectionRecord(BaseModel):
    attempt_number: int
    timestamp: str
    failed_checkpoints: List[str]
    reasons: List[str]
    corrective_instructions: List[str]
    changes_required: str
    draft_snippet: str
    actual_changes_made: Optional[str] = None

class EvaluationDecision(BaseModel):
    overall_passed: bool
    status: Literal["PASSED", "REJECTED", "FAILED"]
    deterministic_passed: bool
    rubric_passed: bool
    deterministic_checks: List[DeterministicCheckResult]
    rubric_checkpoints: List[RubricCheckpointResult]
    failure_summary: Optional[str] = None
    actionable_feedback_for_regeneration: Optional[str] = None
