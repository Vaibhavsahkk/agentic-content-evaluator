# Curriculum Systems R&D Notes & Experiments

## 1. Executive Summary

Engineering automated curriculum systems requires continuous R&D to benchmark models, refine evaluation rubrics, and eliminate pedagogical bottlenecks. This document captures engineering observations and lessons learned from deploying `openai/gpt-oss-120b` on GroqCloud.

---

## 2. Model Evaluation Experiments

### Experiment 1: Evaluator Strict JSON-Schema Mode vs JSON-Object Mode
- **Objective**: Determine optimal structured-output mode for the 6-checkpoint LLM Judge on GroqCloud.
- **Hypothesis**: Direct Pydantic 2 schema export works out of the box with Groq strict schema.
- **Observed Finding**: Groq strict mode requires recursive `additionalProperties: false` on all nested schema definitions (including `$defs/RubricCheckpointResult`) and requires all properties to be explicitly listed in `required`. Standard Pydantic 2 schemas omit these on nested models, causing HTTP 400 errors.
- **Remediation**: Implemented `make_groq_strict_schema()` transformer in `groq_provider.py` which recursively traverses the schema dict and applies strict constraints. Also added a robust fallback to `json_object` mode with automatic Pydantic validation.

### Experiment 2: Rate Limit (TPM) Behavior on Free Tier
- **Objective**: Assess stability of multi-attempt generation loops under free-tier quota limits (8,000 TPM limit for `openai/gpt-oss-120b`).
- **Observed Finding**: A full 3-attempt cycle with large prompts and structured evaluations can exceed 8,000 tokens within a rolling 60-second window, triggering HTTP 429.
- **Remediation**: Built `_execute_with_backoff()` with exponential backoff and jitter that dynamically parses retry hints (e.g. `try again in 15ms` or `2s`) from Groq error responses, preventing job aborts.

### Experiment 3: Citation Grounding in Learner Outputs
- **Objective**: Test model compliance with inline source citations (`[REF-01]`, `[REF-02]`).
- **Observed Finding**: Generic prompt instructions resulted in the model referencing concepts without bracketed tags.
- **Remediation**: Updated `build_user_generator_prompt` with explicit mandatory requirements to cite `[REF-01]` through `[REF-04]` whenever defining core mechanisms (parametric vs non-parametric memory, chunking, embeddings). Updated deterministic regex in `deterministic.py` to match word boundaries `\b(REF-\d+)\b`.

---

## 3. Quarterly R&D Recommendations

1. **Prompt Compression**: Introduce concise structured summaries for retrieved context to decrease prompt token load by 35%, increasing headroom on free-tier TPM limits.
2. **Sub-Topic Expansion**: Broaden the reference pack to cover *RAG Evaluation Metrics* (Faithfulness, Answer Relevance) and *Advanced Retrieval* (Hybrid Keyword + Dense Search).
3. **Automated Regression Suite**: Gate all candidate prompt/rubric updates against our 28-test verification suite prior to promoting rules to `APPROVED` status.
