-- Self-Evaluating GenAI Lesson Content Generator Database Schema
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('PENDING', 'IN_PROGRESS', 'PASSED', 'FAILED')),
    deliberate_error_injected INTEGER NOT NULL DEFAULT 0,
    attempts_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 2,
    approved_lesson TEXT,
    gen_model TEXT,
    judge_model TEXT,
    prompt_version TEXT,
    rubric_version TEXT,
    ref_pack_version TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS run_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    draft_title TEXT,
    draft_markdown TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('PASSED', 'REJECTED', 'FAILED')),
    feedback_for_regeneration TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS deterministic_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL,
    check_id TEXT NOT NULL,
    name TEXT NOT NULL,
    passed INTEGER NOT NULL CHECK(passed IN (0, 1)),
    failure_reason TEXT,
    details TEXT,
    FOREIGN KEY(attempt_id) REFERENCES run_attempts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rubric_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL,
    checkpoint_id TEXT NOT NULL,
    passed INTEGER NOT NULL CHECK(passed IN (0, 1)),
    evidence TEXT NOT NULL,
    failure_reason TEXT,
    correction_instruction TEXT,
    evidence_span TEXT,
    FOREIGN KEY(attempt_id) REFERENCES run_attempts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rejection_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    failed_checkpoints TEXT NOT NULL,
    reasons TEXT NOT NULL,
    corrective_instructions TEXT NOT NULL,
    changes_required TEXT NOT NULL,
    draft_snippet TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS learned_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    rule_text TEXT NOT NULL,
    evidence_count INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL CHECK(status IN ('CANDIDATE', 'APPROVED', 'REJECTED')) DEFAULT 'CANDIDATE',
    created_at TEXT NOT NULL,
    approved_at TEXT
);

CREATE TABLE IF NOT EXISTS improvement_proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target TEXT NOT NULL CHECK(target IN ('PROMPT', 'RUBRIC')),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    proposed_diff TEXT NOT NULL,
    rationale TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('PENDING', 'APPROVED', 'REJECTED')) DEFAULT 'PENDING',
    created_at TEXT NOT NULL,
    reviewed_at TEXT
);

CREATE TABLE IF NOT EXISTS content_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    issue_type TEXT NOT NULL CHECK(issue_type IN ('OUTDATED_CONCEPT', 'DEPRECATED_LIBRARY', 'WRONG_SYNTAX', 'BROKEN_EXAMPLE')),
    description TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('OPEN', 'INVESTIGATING', 'RESOLVED')) DEFAULT 'OPEN',
    detected_at TEXT NOT NULL,
    resolved_at TEXT,
    resolution_notes TEXT
);

CREATE TABLE IF NOT EXISTS user_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

-- Indexes for fast lookup
CREATE INDEX IF NOT EXISTS idx_run_attempts_run_id ON run_attempts(run_id);
CREATE INDEX IF NOT EXISTS idx_rejection_logs_run_id ON rejection_logs(run_id);
CREATE INDEX IF NOT EXISTS idx_deterministic_attempt_id ON deterministic_checks(attempt_id);
CREATE INDEX IF NOT EXISTS idx_rubric_attempt_id ON rubric_checks(attempt_id);
CREATE INDEX IF NOT EXISTS idx_learned_rules_status ON learned_rules(status);
