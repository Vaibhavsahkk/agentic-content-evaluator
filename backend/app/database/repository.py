import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from backend.app.database.connection import get_db_connection
from backend.app.schemas.evaluation import DeterministicCheckResult, RubricCheckpointResult, RejectionRecord
from backend.app.schemas.evolution import LearnedRule, ImprovementProposal, ContentIssue

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class DatabaseRepository:
    """Repository for managing all persistence logic across runs, evaluations, memory, and evolution."""

    @staticmethod
    def create_run(
        run_id: str,
        topic: str,
        deliberate_error_injected: bool = False,
        max_retries: int = 2,
        gen_model: str = "openai/gpt-oss-120b",
        judge_model: str = "openai/gpt-oss-120b",
        prompt_version: str = "1.0.0",
        rubric_version: str = "1.0.0",
        ref_pack_version: str = "1.0.0"
    ) -> None:
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO runs (
                    run_id, topic, status, deliberate_error_injected,
                    attempts_count, max_retries, gen_model, judge_model,
                    prompt_version, rubric_version, ref_pack_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id, topic, "PENDING", int(deliberate_error_injected),
                    0, max_retries, gen_model, judge_model,
                    prompt_version, rubric_version, ref_pack_version, utc_now_iso()
                )
            )

    @staticmethod
    def update_run_status(
        run_id: str,
        status: str,
        approved_lesson: Optional[str] = None,
        attempts_count: Optional[int] = None,
        completed_at: Optional[str] = None
    ) -> None:
        fields = ["status = ?"]
        values = [status]
        if approved_lesson is not None:
            fields.append("approved_lesson = ?")
            values.append(approved_lesson)
        if attempts_count is not None:
            fields.append("attempts_count = ?")
            values.append(attempts_count)
        if completed_at is not None:
            fields.append("completed_at = ?")
            values.append(completed_at)
        values.append(run_id)

        query = f"UPDATE runs SET {', '.join(fields)} WHERE run_id = ?"
        with get_db_connection() as conn:
            conn.execute(query, values)

    @staticmethod
    def reconcile_orphaned_runs() -> int:
        """
        Reconciles any incomplete runs left in 'PENDING' or 'IN_PROGRESS' state
        due to previous process termination or crashes, marking them as 'FAILED'.
        Also reconciles attempts_count from run_attempts table.
        """
        now = utc_now_iso()
        with get_db_connection() as conn:
            cur = conn.execute(
                """
                UPDATE runs
                SET status = 'FAILED',
                    completed_at = COALESCE(completed_at, ?)
                WHERE status IN ('PENDING', 'IN_PROGRESS')
                """,
                (now,)
            )
            # Reconcile attempts_count from run_attempts where actual attempts were recorded
            conn.execute(
                """
                UPDATE runs
                SET attempts_count = (
                    SELECT COUNT(*) FROM run_attempts WHERE run_attempts.run_id = runs.run_id
                )
                WHERE runs.attempts_count = 0 AND EXISTS (
                    SELECT 1 FROM run_attempts WHERE run_attempts.run_id = runs.run_id
                )
                """
            )
            return cur.rowcount

    @staticmethod
    def record_attempt(
        run_id: str,
        attempt_number: int,
        draft_title: str,
        draft_markdown: str,
        status: str,
        feedback_for_regeneration: Optional[str] = None
    ) -> int:
        with get_db_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO run_attempts (
                    run_id, attempt_number, draft_title, draft_markdown,
                    status, feedback_for_regeneration, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id, attempt_number, draft_title, draft_markdown,
                    status, feedback_for_regeneration, utc_now_iso()
                )
            )
            return cur.lastrowid

    @staticmethod
    def record_deterministic_checks(attempt_id: int, checks: List[DeterministicCheckResult]) -> None:
        with get_db_connection() as conn:
            for c in checks:
                conn.execute(
                    """
                    INSERT INTO deterministic_checks (
                        attempt_id, check_id, name, passed, failure_reason, details
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (attempt_id, c.check_id, c.name, int(c.passed), c.failure_reason, c.details)
                )

    @staticmethod
    def record_rubric_checks(attempt_id: int, checks: List[RubricCheckpointResult]) -> None:
        with get_db_connection() as conn:
            for c in checks:
                conn.execute(
                    """
                    INSERT INTO rubric_checks (
                        attempt_id, checkpoint_id, passed, evidence,
                        failure_reason, correction_instruction, evidence_span
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        attempt_id, c.checkpoint_id, int(c.passed), c.evidence,
                        c.failure_reason, c.correction_instruction, c.evidence_span
                    )
                )

    @staticmethod
    def record_rejection_log(
        run_id: str,
        attempt_number: int,
        failed_checkpoints: List[str],
        reasons: List[str],
        corrective_instructions: List[str],
        changes_required: str,
        draft_snippet: str
    ) -> None:
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO rejection_logs (
                    run_id, attempt_number, failed_checkpoints, reasons,
                    corrective_instructions, changes_required, draft_snippet, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id, attempt_number, json.dumps(failed_checkpoints),
                    json.dumps(reasons), json.dumps(corrective_instructions),
                    changes_required, draft_snippet, utc_now_iso()
                )
            )

    @staticmethod
    def get_run(run_id: str) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if not row:
                return None
            return dict(row)

    @staticmethod
    def get_all_runs(limit: int = 50) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_rejections_for_run(run_id: str) -> List[RejectionRecord]:
        with get_db_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM rejection_logs WHERE run_id = ? ORDER BY attempt_number ASC",
                (run_id,)
            ).fetchall()
            rejections = []
            for r in rows:
                rejections.append(
                    RejectionRecord(
                        attempt_number=r["attempt_number"],
                        timestamp=r["created_at"],
                        failed_checkpoints=json.loads(r["failed_checkpoints"]),
                        reasons=json.loads(r["reasons"]),
                        corrective_instructions=json.loads(r["corrective_instructions"]),
                        changes_required=r["changes_required"],
                        draft_snippet=r["draft_snippet"]
                    )
                )
            return rejections

    @staticmethod
    def get_attempts_for_run(run_id: str) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            attempts_rows = conn.execute(
                "SELECT * FROM run_attempts WHERE run_id = ? ORDER BY attempt_number ASC",
                (run_id,)
            ).fetchall()
            results = []
            for a in attempts_rows:
                att_id = a["id"]
                det_rows = conn.execute(
                    "SELECT * FROM deterministic_checks WHERE attempt_id = ?", (att_id,)
                ).fetchall()
                rub_rows = conn.execute(
                    "SELECT * FROM rubric_checks WHERE attempt_id = ?", (att_id,)
                ).fetchall()
                results.append({
                    "id": att_id,
                    "attempt_number": a["attempt_number"],
                    "draft_title": a["draft_title"],
                    "draft_markdown": a["draft_markdown"],
                    "status": a["status"],
                    "feedback_for_regeneration": a["feedback_for_regeneration"],
                    "created_at": a["created_at"],
                    "deterministic_checks": [
                        {
                            "check_id": d["check_id"],
                            "name": d["name"],
                            "passed": bool(d["passed"]),
                            "failure_reason": d["failure_reason"],
                            "details": d["details"]
                        } for d in det_rows
                    ],
                    "rubric_checkpoints": [
                        {
                            "checkpoint_id": rc["checkpoint_id"],
                            "passed": bool(rc["passed"]),
                            "evidence": rc["evidence"],
                            "failure_reason": rc["failure_reason"],
                            "correction_instruction": rc["correction_instruction"],
                            "evidence_span": rc["evidence_span"]
                        } for rc in rub_rows
                    ]
                })
            return results

    # Self-Evolution & Learned Guidance
    @staticmethod
    def get_approved_rules(limit: int = 10) -> List[LearnedRule]:
        with get_db_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM learned_rules WHERE status = 'APPROVED' ORDER BY evidence_count DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [
                LearnedRule(
                    id=r["id"],
                    category=r["category"],
                    rule_text=r["rule_text"],
                    evidence_count=r["evidence_count"],
                    status=r["status"],
                    created_at=r["created_at"],
                    approved_at=r["approved_at"]
                ) for r in rows
            ]

    @staticmethod
    def get_all_rules() -> List[LearnedRule]:
        with get_db_connection() as conn:
            rows = conn.execute("SELECT * FROM learned_rules ORDER BY created_at DESC").fetchall()
            return [
                LearnedRule(
                    id=r["id"],
                    category=r["category"],
                    rule_text=r["rule_text"],
                    evidence_count=r["evidence_count"],
                    status=r["status"],
                    created_at=r["created_at"],
                    approved_at=r["approved_at"]
                ) for r in rows
            ]

    @staticmethod
    def add_or_increment_candidate_rule(category: str, rule_text: str) -> None:
        with get_db_connection() as conn:
            existing = conn.execute(
                "SELECT id, evidence_count FROM learned_rules WHERE category = ? AND rule_text = ?",
                (category, rule_text)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE learned_rules SET evidence_count = evidence_count + 1 WHERE id = ?",
                    (existing["id"],)
                )
            else:
                conn.execute(
                    """
                    INSERT INTO learned_rules (category, rule_text, evidence_count, status, created_at)
                    VALUES (?, ?, 1, 'CANDIDATE', ?)
                    """,
                    (category, rule_text, utc_now_iso())
                )

    @staticmethod
    def update_rule_status(rule_id: int, status: str) -> bool:
        with get_db_connection() as conn:
            approved_at = utc_now_iso() if status == "APPROVED" else None
            cur = conn.execute(
                "UPDATE learned_rules SET status = ?, approved_at = ? WHERE id = ?",
                (status, approved_at, rule_id)
            )
            return cur.rowcount > 0

    # Improvement Proposals
    @staticmethod
    def get_improvement_proposals() -> List[ImprovementProposal]:
        with get_db_connection() as conn:
            rows = conn.execute("SELECT * FROM improvement_proposals ORDER BY created_at DESC").fetchall()
            return [
                ImprovementProposal(
                    id=r["id"],
                    target=r["target"],
                    title=r["title"],
                    description=r["description"],
                    proposed_diff=r["proposed_diff"],
                    rationale=r["rationale"],
                    status=r["status"],
                    created_at=r["created_at"],
                    reviewed_at=r["reviewed_at"]
                ) for r in rows
            ]

    @staticmethod
    def add_improvement_proposal(target: str, title: str, description: str, proposed_diff: str, rationale: str) -> int:
        with get_db_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO improvement_proposals (target, title, description, proposed_diff, rationale, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'PENDING', ?)
                """,
                (target, title, description, proposed_diff, rationale, utc_now_iso())
            )
            return cur.lastrowid

    @staticmethod
    def update_proposal_status(proposal_id: int, status: str) -> bool:
        with get_db_connection() as conn:
            cur = conn.execute(
                "UPDATE improvement_proposals SET status = ?, reviewed_at = ? WHERE id = ?",
                (status, utc_now_iso(), proposal_id)
            )
            return cur.rowcount > 0

    # Content Issues & Maintenance
    @staticmethod
    def get_content_issues() -> List[ContentIssue]:
        with get_db_connection() as conn:
            rows = conn.execute("SELECT * FROM content_issues ORDER BY detected_at DESC").fetchall()
            return [
                ContentIssue(
                    id=r["id"],
                    topic=r["topic"],
                    issue_type=r["issue_type"],
                    description=r["description"],
                    status=r["status"],
                    detected_at=r["detected_at"],
                    resolved_at=r["resolved_at"],
                    resolution_notes=r["resolution_notes"]
                ) for r in rows
            ]

    @staticmethod
    def add_content_issue(topic: str, issue_type: str, description: str) -> int:
        with get_db_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO content_issues (topic, issue_type, description, status, detected_at)
                VALUES (?, ?, ?, 'OPEN', ?)
                """,
                (topic, issue_type, description, utc_now_iso())
            )
            return cur.lastrowid

    @staticmethod
    def update_content_issue(issue_id: int, status: str, resolution_notes: Optional[str] = None) -> bool:
        with get_db_connection() as conn:
            resolved_at = utc_now_iso() if status == "RESOLVED" else None
            cur = conn.execute(
                "UPDATE content_issues SET status = ?, resolved_at = ?, resolution_notes = ? WHERE id = ?",
                (status, resolved_at, resolution_notes, issue_id)
            )
            return cur.rowcount > 0

    # User Feedback
    @staticmethod
    def add_user_feedback(run_id: str, rating: int, comment: Optional[str] = None) -> int:
        with get_db_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO user_feedback (run_id, rating, comment, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (run_id, rating, comment, utc_now_iso())
            )
            return cur.lastrowid
