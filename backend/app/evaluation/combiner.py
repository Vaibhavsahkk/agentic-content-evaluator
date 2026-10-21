from typing import List, Tuple
from datetime import datetime, timezone
from backend.app.schemas.evaluation import (
    DeterministicCheckResult,
    RubricCheckpointResult,
    EvaluationDecision,
    RejectionRecord,
    MANDATORY_CHECKPOINT_IDS
)

def combine_evaluations(
    attempt_number: int,
    draft_text: str,
    deterministic_checks: List[DeterministicCheckResult],
    rubric_checkpoints: List[RubricCheckpointResult]
) -> Tuple[EvaluationDecision, RejectionRecord]:
    """
    Pure Python gatekeeper: Computes final pass/fail decision.
    Passes ONLY IF all deterministic checks pass AND all 6 rubric dimensions pass.
    """
    det_passed = all(c.passed for c in deterministic_checks)
    
    # Check all 6 checkpoints present, exact, and passing
    rubric_ids = {c.checkpoint_id for c in rubric_checkpoints}
    has_exact_checkpoints = rubric_ids == set(MANDATORY_CHECKPOINT_IDS) and len(rubric_checkpoints) == len(MANDATORY_CHECKPOINT_IDS)
    rub_passed = det_passed and has_exact_checkpoints and all(c.passed for c in rubric_checkpoints)
    
    overall_passed = det_passed and rub_passed

    failed_reasons = []
    failed_checkpoints = []
    corrective_instructions = []

    # Collect deterministic failures
    for dc in deterministic_checks:
        if not dc.passed:
            failed_checkpoints.append(f"deterministic:{dc.check_id}")
            msg = f"[DETERMINISTIC - {dc.name}]: {dc.failure_reason}"
            if dc.details:
                msg += f" (Details: {dc.details})"
            failed_reasons.append(msg)
            corrective_instructions.append(f"Resolve objective check '{dc.name}': {dc.failure_reason}")

    # Collect rubric failures
    for rc in rubric_checkpoints:
        if not rc.passed:
            failed_checkpoints.append(f"rubric:{rc.checkpoint_id}")
            failed_reasons.append(f"[RUBRIC - {rc.checkpoint_id}]: {rc.failure_reason}")
            if rc.correction_instruction:
                corrective_instructions.append(f"[{rc.checkpoint_id}]: {rc.correction_instruction}")

    if overall_passed:
        decision = EvaluationDecision(
            overall_passed=True,
            status="PASSED",
            deterministic_passed=True,
            rubric_passed=True,
            deterministic_checks=deterministic_checks,
            rubric_checkpoints=rubric_checkpoints,
            failure_summary=None,
            actionable_feedback_for_regeneration=None
        )
        rejection_record = RejectionRecord(
            attempt_number=attempt_number,
            timestamp=datetime.now(timezone.utc).isoformat(),
            failed_checkpoints=[],
            reasons=[],
            corrective_instructions=[],
            changes_required="None - Lesson cleared all quality and accuracy bars.",
            draft_snippet=draft_text[:300] + "..." if len(draft_text) > 300 else draft_text
        )
    else:
        feedback_lines = []
        feedback_lines.append("The following quality checkpoints failed:")
        for r in failed_reasons:
            feedback_lines.append(f"- {r}")
        feedback_lines.append("\nPlease apply these specific corrections on regeneration:")
        for c in corrective_instructions:
            feedback_lines.append(f"* {c}")

        feedback_text = "\n".join(feedback_lines)

        decision = EvaluationDecision(
            overall_passed=False,
            status="REJECTED",
            deterministic_passed=det_passed,
            rubric_passed=rub_passed,
            deterministic_checks=deterministic_checks,
            rubric_checkpoints=rubric_checkpoints,
            failure_summary="; ".join(failed_reasons),
            actionable_feedback_for_regeneration=feedback_text
        )
        rejection_record = RejectionRecord(
            attempt_number=attempt_number,
            timestamp=datetime.now(timezone.utc).isoformat(),
            failed_checkpoints=failed_checkpoints,
            reasons=failed_reasons,
            corrective_instructions=corrective_instructions,
            changes_required=feedback_text,
            draft_snippet=draft_text[:300] + "..." if len(draft_text) > 300 else draft_text
        )

    return decision, rejection_record
