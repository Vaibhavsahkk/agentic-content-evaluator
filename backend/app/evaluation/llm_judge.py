from typing import List, Dict, Any
from backend.app.schemas.evaluation import LLMEvaluationResponse, RubricCheckpointResult, MANDATORY_CHECKPOINT_IDS
from backend.app.providers.base import LLMProvider
from backend.app.core.security import wrap_untrusted_context
from backend.app.core.logging import logger

EVALUATOR_SYSTEM_PROMPT = """You are an expert AI Curriculum Evaluation Judge.
Your role is to rigorously evaluate an educational lesson on 'Introduction to RAG' designed for an Indian Class 12 graduate from a vernacular or non-English-medium background.

You MUST evaluate the lesson against EXACTLY the six mandatory checkpoints:
1. 'accurate_and_grounded': All technical claims must be accurate according to primary references. CRITICAL: Any claim that RAG retrains or modifies model weights upon document retrieval MUST FAIL.
2. 'beginner_friendly_language': Simple words, short sentences, accessible to a learner with basic English. No dense academic prose.
3. 'teaches_by_example': Includes a relatable real-life worked example (such as a college student querying a library policy or semester fee circular).
4. 'clear_no_unexplained_jargon': Technical words (embedding, chunk, vector, retriever) must be defined with clear analogies before use.
5. 'covers_the_key_points': Fully addresses What RAG is, Why it matters, How it works (Chunking -> Embedding -> Retrieval -> Generation), and its limitations.
6. 'coherent_teaching_flow': Smooth pedagogical structure moving logically from intuition to mechanics to practical scenario to takeaways.

CRITICAL INSTRUCTIONS:
- Every checkpoint is HARD PASS/FAIL. There is NO partial credit.
- You must return all 6 checkpoints exactly once with matching checkpoint_id.
- For any checkpoint where passed is false, you MUST provide:
  * failure_reason: Why it failed with direct reference to the text.
  * correction_instruction: Exact actionable steps for the writer to fix it.
  * evidence_span: The offending or missing text excerpt.
- For passed checkpoints, failure_reason and correction_instruction may be null.
"""

def evaluate_lesson_with_llm(
    draft_text: str,
    provider: LLMProvider,
    references_context: str
) -> LLMEvaluationResponse:
    """
    Executes Stage B LLM evaluation using strict structured schema output.
    """
    safe_draft = wrap_untrusted_context("lesson_draft", draft_text)
    safe_ref = wrap_untrusted_context("reference_sources", references_context) if references_context else "No external reference context provided."
    messages = [
        {"role": "system", "content": EVALUATOR_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"### Reference Context Available to Generator:\n{safe_ref}\n\n"
                f"### Lesson Draft to Evaluate:\n{safe_draft}\n\n"
                "Please evaluate this lesson against all 6 mandatory rubric dimensions."
            )
        }
    ]

    result = provider.generate_structured(
        messages=messages,
        schema=LLMEvaluationResponse,
        temperature=0.1
    )
    
    logger.info(f"LLM Judge completed evaluation in {result.latency_ms:.1f}ms (model: {result.model})")
    return result.parsed
