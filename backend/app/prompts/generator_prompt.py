from typing import List, Optional
from backend.app.schemas.evolution import LearnedRule
from backend.app.core.security import wrap_untrusted_context

def build_system_generator_prompt(approved_rules: Optional[List[LearnedRule]] = None) -> str:
    rules_text = ""
    if approved_rules:
        rules_text = "\n### Previously Learned Editorial Guidelines (Approved from Historical Runs):\n"
        for r in approved_rules:
            rules_text += f"- [{r.category.upper()}]: {r.rule_text}\n"

    return f"""You are a master curriculum engineer specializing in clear, accessible AI curriculum.
Your mission is to teach cutting-edge Generative AI concepts to beginner students.

### Target Learner Profile:
- A student who just finished Class 12 in India.
- Limited English vocabulary; studied in a vernacular / non-English-medium school.
- Eager to start an AI career, but starts from absolute zero.
- Does NOT know AI jargon. Every technical word must be introduced with a simple real-life analogy before using it.

### Editorial Guidelines:
1. Use simple, short, clear English sentences. Avoid complex multi-clause sentences.
2. Ground all factual assertions in the provided reference sources using bracketed tags like [REF-01], [REF-02], [REF-03], [REF-04]. In particular, chunking and embeddings concepts must cite [REF-02].
3. Teach by concrete example. Use relatable Indian student situations (e.g., college semester fees, library books, train ticket rules). Always include an explicit note stating that the college/institution scenario is a fictional illustrative example.
4. Clearly distinguish between what the AI model learned during training (its internal brain/weights) and external document facts retrieved at question time.
5. Emphasize that retrieving a document DOES NOT retrain the model's neural network weights [REF-01].
6. Acknowledge that RAG helps reduce hallucinations, but cannot guarantee 100% accuracy if the retrieved documents are incomplete or wrong [REF-04].
{rules_text}
### Required Lesson Sections (in clear Markdown format):
# [Lesson Title]
## 1. What is RAG?
## 2. Why Does RAG Matter?
## 3. How RAG Works Step-by-Step (Include Chunking, Embeddings, Retrieval, Generation)
## 4. Concrete Worked Example (Relatable college/library query scenario with fictional disclaimer note)
## 5. Limitations and Common Misunderstandings (Emphasize: No weight retraining; Not 100% error-free)
## 6. Key Takeaways (Bullet points)
## References (Summary table of all cited references [REF-01] to [REF-04])
"""

def build_user_generator_prompt(topic: str, references_context: str) -> str:
    safe_topic = wrap_untrusted_context("topic", topic)
    safe_ref = wrap_untrusted_context("reference_sources", references_context) if references_context else "No reference context provided."
    return f"""Please generate a complete, standalone beginner lesson on the topic specified in the block below:
{safe_topic}

### Verified Reference Sources to Ground Your Lesson:
{safe_ref}

CRITICAL MANDATORY INSTRUCTIONS:
1. You MUST include explicit reference citations like [REF-01], [REF-02], [REF-03], [REF-04] in the text when explaining facts (e.g. how RAG combines parametric and non-parametric memory [REF-01], chunking and embeddings [REF-02], university handbook example [REF-03], limitations [REF-04]).
2. Use all 6 required section headings exactly as specified, plus a terminal ## References table.
3. If using a college or institutional scenario, include an explicit disclaimer stating it is a fictional illustrative example.
4. Keep English simple and beginner-friendly for a Class 12 student in India.

Write the full lesson in high-quality standalone Markdown.
"""

def build_regeneration_prompt(
    topic: str,
    previous_draft: str,
    feedback: str,
    references_context: str
) -> str:
    safe_topic = wrap_untrusted_context("topic", topic)
    safe_prev = wrap_untrusted_context("previous_draft", previous_draft)
    safe_feedback = wrap_untrusted_context("evaluation_feedback", feedback)
    safe_ref = wrap_untrusted_context("reference_sources", references_context) if references_context else "No reference context provided."
    return f"""The previous draft for the lesson was evaluated by the automated quality system and REJECTED due to specific quality or accuracy failures.

### Target Topic:
{safe_topic}

### Actionable Evaluation Feedback and Correction Instructions:
{safe_feedback}

### Verified Reference Sources:
{safe_ref}

### Previous Draft to Revise:
{safe_prev}

### Your Task:
Regenerate the lesson to FIX all cited issues while preserving the correct parts.
1. Strictly follow each correction instruction given above.
2. Ensure all 6 required sections are present, along with the ## References section.
3. Ensure reference tags like [REF-01], [REF-02], [REF-03], [REF-04] are included inline in the text (chunking & embeddings cite [REF-02]).
4. Include an explicit note clarifying any institutional example is fictional.
5. Keep the language simple for an Indian Class 12 beginner.
6. Correct any false claims or unexplained jargon.
7. Provide the complete updated lesson in Markdown.
"""
