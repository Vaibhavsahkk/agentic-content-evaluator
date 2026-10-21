import re
from typing import List, Tuple
from backend.app.schemas.evaluation import DeterministicCheckResult
from backend.app.reference_pack.loader import get_all_reference_ids

# Controlled false claim string for test error detection showcase
CONTROLLED_FALSE_CLAIM_PATTERN = re.compile(
    r"retrains?\s+(the\s+)?(language\s+model'?s?\s+)?weights\s+every\s+time(\s+it\s+retrieves)?",
    re.IGNORECASE
)

REQUIRED_SECTION_KEYWORDS = [
    ("what_is_rag", ["what is rag", "what is retrieval-augmented"]),
    ("why_it_matters", ["why does rag matter", "why rag matters", "why it matters", "importance of rag"]),
    ("how_it_works", ["how rag works", "how it works", "steps", "step-by-step"]),
    ("worked_example", ["worked example", "concrete example", "example", "scenario", "practical example"]),
    ("limitations", ["limitation", "misunderstanding", "what rag cannot do", "common mistakes"]),
    ("takeaways", ["key takeaways", "recap", "summary", "conclusion"])
]

def run_deterministic_checks(draft_text: str) -> List[DeterministicCheckResult]:
    """
    Executes all Stage A deterministic Python checks against the lesson text.
    Each check is isolated, named, and returns pass/fail with failure details.
    """
    results: List[DeterministicCheckResult] = []
    # Normalize unicode hyphens and dashes (\u2010-\u2015, \u2212) to standard ASCII '-'
    normalized_draft = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]", "-", draft_text) if draft_text else ""
    text_lower = normalized_draft.lower() if normalized_draft else ""

    # Check 1: Non-empty & minimum length
    if not draft_text or len(draft_text.strip()) < 200:
        results.append(
            DeterministicCheckResult(
                check_id="check_non_empty",
                name="Content Completeness & Minimum Length",
                passed=False,
                failure_reason="Lesson draft is empty or too short (< 200 characters).",
                details="Expected a complete lesson with multiple sections."
            )
        )
        return results  # Short-circuit if empty
    else:
        results.append(
            DeterministicCheckResult(
                check_id="check_non_empty",
                name="Content Completeness & Minimum Length",
                passed=True
            )
        )

    # Check 2: Deliberate Injected Error Detection (Controlled false claim)
    false_claim_match = CONTROLLED_FALSE_CLAIM_PATTERN.search(draft_text)
    # Check if text affirms this false claim without negating it (e.g. "RAG retrains the language model's weights every time")
    if false_claim_match:
        # Check if it was preceded by negation like "does not", "doesn't", "no", "false"
        start = max(0, false_claim_match.start() - 30)
        preceding = draft_text[start:false_claim_match.start()].lower()
        if not any(neg in preceding for neg in ["not", "never", "no", "doesn't", "does not"]):
            results.append(
                DeterministicCheckResult(
                    check_id="check_controlled_false_claim",
                    name="Grounding & Accuracy: Weight Retraining Verification",
                    passed=False,
                    failure_reason=(
                        "Factually false statement detected: Claimed that RAG retrains model weights on retrieval. "
                        "Retrieval operates dynamically at inference time and does NOT modify model weights."
                    ),
                    details=f"Detected match: '{false_claim_match.group(0)}'"
                )
            )
        else:
            results.append(
                DeterministicCheckResult(
                    check_id="check_controlled_false_claim",
                    name="Grounding & Accuracy: Weight Retraining Verification",
                    passed=True
                )
            )
    else:
        results.append(
            DeterministicCheckResult(
                check_id="check_controlled_false_claim",
                name="Grounding & Accuracy: Weight Retraining Verification",
                passed=True
            )
        )

    # Check 3: Required Sections Coverage
    missing_sections = []
    for section_id, keywords in REQUIRED_SECTION_KEYWORDS:
        if not any(kw in text_lower for kw in keywords):
            missing_sections.append(section_id)

    if missing_sections:
        results.append(
            DeterministicCheckResult(
                check_id="check_required_sections",
                name="Mandatory Structural Sections",
                passed=False,
                failure_reason=f"Missing mandatory sections: {', '.join(missing_sections)}.",
                details="Lesson must cover What RAG is, Why it matters, How it works, Worked example, Limitations, and Recap."
            )
        )
    else:
        results.append(
            DeterministicCheckResult(
                check_id="check_required_sections",
                name="Mandatory Structural Sections",
                passed=True
            )
        )

    # Check 4: Worked Example Verification
    example_indicators = ["example", "scenario", "student", "college", "library", "handbook", "question"]
    example_hits = sum(1 for ind in example_indicators if ind in text_lower)
    if example_hits < 2:
        results.append(
            DeterministicCheckResult(
                check_id="check_worked_example",
                name="Relatable Concrete Example Presence",
                passed=False,
                failure_reason="Worked example lacks concrete scenario details (e.g. college or library student use case).",
                details="Beginners need a relatable worked example to grasp RAG mechanics."
            )
        )
    else:
        results.append(
            DeterministicCheckResult(
                check_id="check_worked_example",
                name="Relatable Concrete Example Presence",
                passed=True
            )
        )

    # Check 5: Reference ID Citations and Resolution
    raw_refs = re.findall(r"\bREF[-_\s]?0?(\d+)\b", normalized_draft, re.IGNORECASE)
    cited_refs = [f"REF-{int(num):02d}" for num in raw_refs] if raw_refs else re.findall(r"\b(REF-\d+)\b", normalized_draft)
    known_ref_ids = set(get_all_reference_ids())
    
    if not cited_refs:
        results.append(
            DeterministicCheckResult(
                check_id="check_reference_citations",
                name="Grounded Source Citations",
                passed=False,
                failure_reason="No primary source references cited (expected tags such as [REF-01], [REF-02]).",
                details="Factual claims must be linked to verified reference pack sources."
            )
        )
    else:
        invalid_refs = [ref for ref in set(cited_refs) if ref not in known_ref_ids]
        if invalid_refs:
            results.append(
                DeterministicCheckResult(
                    check_id="check_reference_citations",
                    name="Grounded Source Citations",
                    passed=False,
                    failure_reason=f"Cited references do not resolve to known reference pack IDs: {invalid_refs}.",
                    details=f"Known valid references are: {list(known_ref_ids)}"
                )
            )
        else:
            results.append(
                DeterministicCheckResult(
                    check_id="check_reference_citations",
                    name="Grounded Source Citations",
                    passed=True
                )
            )

    # Check 6: Jargon Explanation Heuristic
    # Key terms must have nearby explanatory cues
    jargon_terms = ["embedding", "chunk", "vector", "retrieval"]
    unexplained = []
    for term in jargon_terms:
        if term in text_lower:
            # Check if there is an explanatory word within 150 characters of the term
            matches = [m.start() for m in re.finditer(re.escape(term), text_lower)]
            has_explanation = False
            for pos in matches:
                window = text_lower[max(0, pos - 100): min(len(text_lower), pos + 150)]
                if any(cue in window for cue in ["meaning", "called", "like", "analog", "number", "barcode", "piece", "cut", "small", "compare", "search", "means", "is a"]):
                    has_explanation = True
                    break
            if not has_explanation:
                unexplained.append(term)

    if unexplained:
        results.append(
            DeterministicCheckResult(
                check_id="check_jargon_definitions",
                name="Jargon Demystification & Plain English Definitions",
                passed=False,
                failure_reason=f"Technical term(s) used without beginner explanation: {', '.join(unexplained)}.",
                details="Terms must be introduced with a simple analogy before relying on them."
            )
        )
    else:
        results.append(
            DeterministicCheckResult(
                check_id="check_jargon_definitions",
                name="Jargon Demystification & Plain English Definitions",
                passed=True
            )
        )

    # Check 7: Readability sentence length check
    sentences = re.split(r"[.!?]+", draft_text)
    overly_long = [s.strip() for s in sentences if len(s.strip().split()) > 45]
    if len(overly_long) > 3:
        results.append(
            DeterministicCheckResult(
                check_id="check_sentence_readability",
                name="Sentence Readability for Class 12 ESL Learners",
                passed=False,
                failure_reason=f"Found {len(overly_long)} sentences exceeding 45 words, which impairs beginner comprehension.",
                details="Break complex compound sentences into shorter, direct statements."
            )
        )
    else:
        results.append(
            DeterministicCheckResult(
                check_id="check_sentence_readability",
                name="Sentence Readability for Class 12 ESL Learners",
                passed=True
            )
        )

    return results
