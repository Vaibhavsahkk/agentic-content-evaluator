# Evaluation Rubric & Quality Gating Specification

## 1. Overview

The evaluation system operates as a **hybrid multi-stage gatekeeper**. An educational lesson is never published based on a single model score or an unstructured sentiment. Instead, every lesson draft must pass both objective Python deterministic checks and structured LLM evaluation across six mandatory pedagogical dimensions.

---

## 2. The Six Mandatory Rubric Dimensions

The six core rubric dimensions are evaluated as independent, hard pass/fail checkpoints:

| Dimension ID | Dimension Name | Passing Criteria | Required Evidence / Grounding |
|---|---|---|---|
| `accurate_and_grounded` | Accurate & Grounded | All factual claims align with verified primary sources (Lewis et al. 2020). Specifically: RAG combines parametric memory (model weights) with non-parametric external index; **retrieval does NOT retrain or alter model weights** at inference time. | Must cite verified source IDs (`[REF-01]`, `[REF-03]`) and avoid claiming weight retraining or 100% error-free outputs. |
| `beginner_friendly_language` | Beginner-Friendly Language | Vocabulary and syntax tailored for an Indian Class 12 graduate with a vernacular / non-English-medium background. Short sentences, active voice, everyday words. | Absence of dense academic phrasing; sentences predominantly under 35 words. |
| `teaches_by_example` | Teaches by Example | Features a concrete, relatable real-life scenario demonstrating the complete query, retrieval, and generation flow. | Indian student scenario (e.g. college semester fee deadline, library manual query, bus timetable). |
| `clear_no_unexplained_jargon` | Clear, No Unexplained Jargon | Technical terms (`chunking`, `embedding`, `vector`, `retrieval`) are defined using simple real-world analogies before being used. | Plain-English comparisons (e.g. cutting textbook into pages, digital barcodes, library index cards). |
| `covers_the_key_points` | Covers Key Points | Covers: 1. What RAG is; 2. Why it matters; 3. How it works (Chunking -> Embedding -> Retrieval -> Generation); 4. Worked example; 5. Limitations; 6. Recap. | Explicit sections addressing each core concept without omitting mechanics or limitations. |
| `coherent_teaching_flow` | Coherent Teaching Flow | Smooth pedagogical progression from intuitive concept to mechanical steps to practical scenario and final recap. | Logical section ordering; each concept builds naturally upon the previous one. |

> [!IMPORTANT]
> **No Partial Credit**: Each checkpoint evaluates strictly to `True` or `False`. An overall score of 5 out of 6 is a **FAIL**, triggering regeneration with targeted feedback.

---

## 3. Stage A: Objective Deterministic Checks

Deterministic checks run before the LLM evaluation to catch structural and factual violations cheaply and reliably:

1. **`check_non_empty`**: Validates content length ($> 200$ characters).
2. **`check_controlled_false_claim`**: Scans for the deliberate false assertion *"RAG retrains the language model's weights every time it retrieves"*.
3. **`check_required_sections`**: Verifies presence of the six mandatory section headings.
4. **`check_worked_example`**: Asserts the presence of concrete scenario keywords (college, student, library, fee, policy).
5. **`check_reference_citations`**: Scans for reference tags (`[REF-01]`, `[REF-02]`, `[REF-03]`, `[REF-04]`) and verifies they resolve to verified sources in the reference pack.
6. **`check_jargon_definitions`**: Ensures key technical terms (`embedding`, `chunk`, `vector`) have explanatory cues within a 150-character window.
7. **`check_sentence_readability`**: Flags drafts with multiple sentences exceeding 45 words.

---

## 4. Strict Schema Specification

LLM evaluation responses are validated against the following strict Pydantic model (`RubricCheckpointResult`):

```python
class RubricCheckpointResult(BaseModel):
    checkpoint_id: str
    passed: StrictBool  # Rejects string coercion ("true", "yes", "0")
    evidence: str
    failure_reason: Optional[str] = None
    correction_instruction: Optional[str] = None
    evidence_span: Optional[str] = None
```

- When `passed` is `False`, `failure_reason` and `correction_instruction` are **strictly required**.
- All six mandatory IDs must be present exactly once. Missing or duplicate IDs raise a validation error.

---

## 5. Pure Python Approval Gate

The final publishing decision is calculated strictly in Python application logic (`combiner.py`):

```python
deterministic_passed = all(check.passed for check in deterministic_checks)
rubric_passed = all(checkpoint.passed for checkpoint in rubric_checkpoints)
overall_passed = deterministic_passed and rubric_passed
```

If `overall_passed` is `False`, a `RejectionRecord` is generated and saved to SQLite, and an actionable feedback block is formulated for the next regeneration attempt.
