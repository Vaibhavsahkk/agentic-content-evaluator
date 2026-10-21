# Architecture Decision Records (ADRs)

## ADR-01: GroqCloud API (Free Tier) with Direct Python SDK

- **Status**: Approved
- **Context**: The system requires using a production-grade LLM while remaining easily deployable with high performance and low latency. Groq provides fast compute with open weights.
- **Decision**: Use `groq` Python SDK directly with `openai/gpt-oss-120b` for both generation and evaluation.
- **Consequences**: Fast inference (<3 seconds per call); requires careful token-per-minute (TPM) rate limit backoff and recursive strict JSON schema conversion.

---

## ADR-02: LangGraph State Machine for Agentic Flow Control

- **Status**: Approved
- **Context**: The pipeline requires bounded generation, multi-stage evaluation, dynamic feedback injection, and strict retry limits (MAX_RETRIES = 2).
- **Decision**: Model the workflow using LangGraph's `StateGraph` with a typed state dict (`LessonGraphState`) and conditional edges (`route_after_eval`, `route_after_rejection`).
- **Consequences**: High testability, transparent state transitions, and clear separation between nodes and business logic.

---

## ADR-03: SQLite WAL Mode for Durable Cross-Run Memory

- **Status**: Approved
- **Context**: The system must persist run history, attempts, evaluations, rejection logs, and learned rules across application restarts without requiring external database servers (e.g. MongoDB, PostgreSQL).
- **Decision**: Use Python's built-in `sqlite3` with Write-Ahead Logging (`PRAGMA journal_mode = WAL;`) and enforced foreign keys (`PRAGMA foreign_keys = ON;`).
- **Consequences**: Zero installation overhead, durable ACID transactions, instantaneous startup.

---

## ADR-04: Hybrid Evaluator Architecture

- **Status**: Approved
- **Context**: An LLM-as-a-judge alone can be inconsistent on structural constraints (e.g. word count, regex patterns, missing citations). Conversely, deterministic checks cannot assess pedagogical tone or clarity for Class 12 vernacular students.
- **Decision**: Combine Stage A (Deterministic Python checks) and Stage B (Strict structured LLM evaluation), joined by Stage C (Pure Python gatekeeper).
- **Consequences**: Fast rejection of structural errors, high pedagogical fidelity, zero false passes due to model coercion.

---

## ADR-05: REST-Based Graph Execution Interface

- **Status**: Approved
- **Context**: Real-time feedback for multi-step agent runs can be delivered via WebSockets, SSE, or synchronous REST with rich state payloads.
- **Decision**: Expose graph executions via standard FastAPI REST endpoints (`POST /api/lessons/generate`) that return complete typed state structures (runs, attempts, rubric checkpoints, deterministic checks, and diffs).
- **Consequences**: Simple, robust client-server interaction without persistent connection dropouts, proxy incompatibilities, or SSE protocol complexity.

---

## ADR-06: Observability, Secret Redaction, and Configurable Tracing

- **Status**: Approved
- **Context**: Production LLM applications require secret safety and optional observability without enforcing third-party SaaS accounts or network transmission of student/curriculum data.
- **Decision**: Implement built-in regex secret scrubbing via `SecretRedactingFormatter` across all logging. Provide environment-level scaffolding for LangSmith (`LANGSMITH_TRACING=false` by default) so users can enable cloud tracing if desired without requiring external dependencies for core testing.
- **Consequences**: Zero credential leakage, 100% offline testability, zero mandatory external telemetry.
