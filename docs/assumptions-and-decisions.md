# Assumptions & Technical Decisions Log

This document records the design decisions and technical assumptions made during the development of the Agentic Content Evaluator.

---

## 1. Summary of Decisions

| ID | Topic | Decision | Justification | Reversibility |
|---|---|---|---|---|
| **DEC-01** | Model Provider | GroqCloud API | Ultra-low latency (<3s per generation), official support for tool-calling and strict JSON schema. | High: Provider abstraction layer allows swapping to OpenAI/Anthropic. |
| **DEC-02** | Primary Model | `openai/gpt-oss-120b` | State-of-the-art open-weights reasoning model available on GroqCloud. | High: Configurable via `.env` (`GROQ_MODEL`, `GROQ_JUDGE_MODEL`). |
| **DEC-03** | Agentic Orchestrator | LangGraph `StateGraph` | Explicit state machine with typed state and inspectable transitions; avoids monolithic procedural scripts. | Medium: Graph logic is clean and decoupled from business rules. |
| **DEC-04** | Knowledge Base | In-memory Curated JSON Reference Pack | 4 authoritative primary sources for RAG (Lewis et al. 2020, LlamaIndex, LangChain, Anthropic); avoids vector DB dependency overhead. | High: Can integrate Qdrant/Chroma if document volume exceeds 1,000 files. |
| **DEC-05** | Database Engine | SQLite (WAL mode, Foreign Keys ON) | Standard library, zero external service dependency, instant local setup, durable cross-run persistence. | High: Repository pattern allows swapping to PostgreSQL. |
| **DEC-06** | Rate Limit Handling | Exponential Backoff with Jitter | Absorbs rate limit fluctuations smoothly without failing jobs during multi-attempt runs. | High: Contained entirely in `groq_provider.py`. |
| **DEC-07** | Frontend Stack | React 19 + Vite + Tailwind CSS | Fast compilation, modern clean interface, mounted statically in FastAPI for zero-config single command execution. | High: Decoupled REST API contracts. |

---

## 2. Core Functional Requirements vs. Architectural Choices

### Core Functional Requirements:
1. Topic: *Introduction to RAG*.
2. Learner: Foundational learner profile with zero AI knowledge.
3. Complete Loop: Generate -> Evaluate -> Regenerate if needed -> Final Decision.
4. Hard Pass/Fail Rubric covering the 6 specified dimensions.
5. Max 1-2 retries (so loop always terminates).
6. Output: Approved lesson + detailed rejection log.
7. Deliberate Error Demonstration catching and recovering from an injected false claim.
8. Persistent cross-run memory and self-evolution.

### Implementation Choices:
1. **Direct Groq SDK over LangChain wrappers**: Eliminates abstraction bloat, guarantees direct control over strict schema and tool calling.
2. **Two-Stage Hybrid Evaluator**: Stage A deterministic Python checks catch objective flaws (empty text, false claim, missing sections) before LLM evaluation, saving API quota and latency.
3. **Pure Python Approval Gate**: The LLM judge's output is purely informative; the final decision is strictly computed in Python code to prevent hallucinated passes.
4. **Mock Provider Harness**: Complete offline testability enabling CI/CD without API keys or quota consumption.
