# Content Freshness & Maintenance Policy

## 1. Objective

To maintain educational excellence, curriculum content must remain technically accurate, authoritative, and up to date. The system includes built-in tracking for source verification, library deprecations, and defect remediation.

---

## 2. Curated Primary Sources for Introduction to RAG

| Source ID | Title & Publication | Verified URL | Key Facts Grounded | Verification Date |
|---|---|---|---|---|
| `REF-01` | *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* (Lewis et al., NeurIPS 2020) | https://arxiv.org/abs/2005.11401 | Combines parametric memory (weights) with non-parametric memory (external index); retrieval occurs dynamically at inference time and does **NOT** alter neural weights. | 2026-10-21 |
| `REF-02` | *LlamaIndex Documentation: Core Concepts* (LlamaIndex Core Team, 2023) | https://docs.llamaindex.ai/en/stable/getting_started/concepts/ | Chunking breaks long text into coherent pieces; embeddings map text to geometric semantic vectors for nearest-neighbor search. | 2026-10-21 |
| `REF-03` | *LangChain RAG Architecture Guide* (LangChain Team, 2024) | https://python.langchain.com/docs/tutorials/rag/ | Two-phase lifecycle (Ingestion vs. Generation); allows models to query private/recent documents without retraining. | 2026-10-21 |
| `REF-04` | *Prompt Engineering: Grounding & Hallucination Mitigations* (Anthropic, 2024) | https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview | Grounding reduces hallucination but cannot guarantee 100% accuracy; missing context causes gaps; rubrics are required to verify output. | 2026-10-21 |

---

## 3. Defect & Freshness Issue Tracking Workflow

The SQLite database and REST API track content defects across four standard categories:
1. `OUTDATED_CONCEPT`: E.g., presenting older fine-tuning paradigms as necessary for simple QA.
2. `DEPRECATED_LIBRARY`: E.g., legacy LangChain v0.1 syntax or obsolete vector store APIs.
3. `WRONG_SYNTAX`: Syntax errors or mismatched versions in code snippets.
4. `BROKEN_EXAMPLE`: Outdated API endpoints or fictional imports.

### Remediation Procedure (1-Week SLA):
1. **Detection**: Defect logged via `POST /api/content-issues` with topic, issue type, and description.
2. **Investigation**: Curriculum engineer reproduces the issue against reference documentation.
3. **Correction**: 
   - If reference pack is outdated: update `rag_reference.json` and bump version (e.g. `1.1.0`).
   - If prompt produces obsolete syntax: submit an `ImprovementProposal` via `POST /api/proposals`.
4. **Resolution**: Update issue status to `RESOLVED` with resolution notes via `POST /api/content-issues/{id}/status`.
