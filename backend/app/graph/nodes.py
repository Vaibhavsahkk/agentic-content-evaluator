import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from backend.app.graph.state import LessonGraphState
from backend.app.core.security import validate_topic_input, inspect_for_prompt_injection, wrap_untrusted_context
from backend.app.database.repository import DatabaseRepository
from backend.app.reference_pack.loader import search_reference_pack, load_reference_pack
from backend.app.tools.reference_lookup import SEARCH_REFERENCE_TOOL_SPEC, execute_reference_tool
from backend.app.prompts.generator_prompt import (
    build_system_generator_prompt,
    build_user_generator_prompt,
    build_regeneration_prompt
)
from backend.app.evaluation.deterministic import run_deterministic_checks
from backend.app.evaluation.llm_judge import evaluate_lesson_with_llm
from backend.app.evaluation.combiner import combine_evaluations
from backend.app.providers.base import LLMProvider
from backend.app.schemas.evolution import LearnedRule
from backend.app.core.logging import logger

CONTROLLED_FALSE_INJECTION = (
    "\n\n> **System Note on Architecture**: A key advantage of RAG is that it retrains the language model's weights every time it retrieves a document from the external database.\n\n"
)

def summarize_draft_changes(prev_draft: str, new_draft: str) -> str:
    """
    F-05: Computes a factual summary of actual changes made during regeneration.
    Compares content length, structural sections, error claim removal, and citations.
    """
    import re
    changes = []
    prev_words = len(prev_draft.split())
    new_words = len(new_draft.split())
    changes.append(f"Content volume: updated from {prev_words} words to {new_words} words ({new_words - prev_words:+d} words)")

    # Check for removal of false weight retraining claim
    false_kw = ["retrains the language model's weights", "retrain model weights", "modifies model weights", "retrains the model's weights"]
    if any(k in prev_draft.lower() for k in false_kw) and not any(k in new_draft.lower() for k in false_kw):
        changes.append("Removed factually false claim asserting that RAG retrains neural network weights upon document retrieval")

    # Check for structural section additions
    prev_headers = set(re.findall(r"^#{1,3}\s+(.+)$", prev_draft, re.MULTILINE))
    new_headers = set(re.findall(r"^#{1,3}\s+(.+)$", new_draft, re.MULTILINE))
    added_headers = new_headers - prev_headers
    if added_headers:
        clean_headers = [h.strip() for h in added_headers]
        changes.append(f"Added structural sections: {', '.join(sorted(clean_headers))}")

    # Check for newly added citations
    prev_cits = set(re.findall(r"\[REF-\d+\]", prev_draft))
    new_cits = set(re.findall(r"\[REF-\d+\]", new_draft))
    added_cits = new_cits - prev_cits
    if added_cits:
        changes.append(f"Added primary reference citations: {', '.join(sorted(added_cits))}")

    if not changes:
        return "Refined terminology and simplified explanations for Class 12 beginner accessibility."
    return "; ".join(changes)

def create_nodes(provider: LLMProvider):
    """Factory creating bound graph node functions using the injected LLM provider."""

    def validate_input_node(state: LessonGraphState) -> Dict[str, Any]:
        raw_topic = state.get("topic", "Introduction to RAG")
        run_id = state.get("run_id") or str(uuid.uuid4())
        deliberate_error = state.get("enable_deliberate_error", False)
        max_retries = min(max(int(state.get("max_retries", 2)), 1), 2)

        is_valid, validated_topic_or_err = validate_topic_input(raw_topic)
        if not is_valid:
            logger.warning(f"Validation failed for topic '{raw_topic}': {validated_topic_or_err}")
            # Register run as FAILED immediately so database has full audit trail
            try:
                DatabaseRepository.create_run(
                    run_id=run_id,
                    topic=raw_topic or "<EMPTY_TOPIC>",
                    deliberate_error_injected=deliberate_error,
                    max_retries=max_retries
                )
                DatabaseRepository.update_run_status(
                    run_id=run_id,
                    status="FAILED",
                    attempts_count=0,
                    completed_at=datetime.now(timezone.utc).isoformat()
                )
            except Exception as e:
                logger.error(f"Error persisting failed validation run: {e}")

            return {
                "run_id": run_id,
                "topic": raw_topic,
                "status": "FAILED",
                "error_message": validated_topic_or_err,
                "attempt_number": 0,
                "draft_history": [],
                "rejection_log": []
            }

        topic = validated_topic_or_err

        # Register run in database
        DatabaseRepository.create_run(
            run_id=run_id,
            topic=topic,
            deliberate_error_injected=deliberate_error,
            max_retries=max_retries
        )

        return {
            "run_id": run_id,
            "topic": topic,
            "enable_deliberate_error": deliberate_error,
            "max_retries": max_retries,
            "attempt_number": 0,
            "draft_history": [],
            "rejection_log": [],
            "status": "IN_PROGRESS"
        }

    def load_context_and_memory_node(state: LessonGraphState) -> Dict[str, Any]:
        # Cross-run memory: Retrieve previously approved editorial rules
        approved_rules = DatabaseRepository.get_approved_rules(limit=5)
        logger.info(f"Retrieved {len(approved_rules)} approved historical rules from memory.")

        # Load curated reference pack metadata
        pack = load_reference_pack()
        return {
            "learned_guidance": [r.model_dump() for r in approved_rules]
        }

    def retrieve_references_node(state: LessonGraphState) -> Dict[str, Any]:
        topic = state.get("topic", "Introduction to RAG")
        retrieved_refs = []

        # Attempt model tool-calling
        try:
            tool_msg = [
                {"role": "system", "content": "You are a research assistant. Use the search_reference_pack tool to query sources for the lesson topic."},
                {"role": "user", "content": f"Find primary reference sources to ground the lesson on '{topic}'."}
            ]
            tool_result = provider.call_with_tools(
                messages=tool_msg,
                tools=[SEARCH_REFERENCE_TOOL_SPEC]
            )

            if tool_result.tool_calls:
                for tc in tool_result.tool_calls:
                    if tc.function_name == "search_reference_pack":
                        res_str = execute_reference_tool(tc.arguments)
                        retrieved_refs.extend(search_reference_pack(tc.arguments.get("query", topic), max_results=3))
        except Exception as e:
            logger.warning(f"Model tool calling encountered error or unavailable, falling back to deterministic search: {e}")

        # Deterministic retrieval fallback if model didn't call tool or returned empty
        if not retrieved_refs:
            retrieved_refs = search_reference_pack(topic, max_results=4)

        # Build formatted reference context
        context_parts = []
        for r in retrieved_refs:
            context_parts.append(
                f"[{r.source_id}] {r.title} ({r.url})\n"
                f"Key Facts:\n" + "\n".join(f"- {c}" for c in r.matched_claims) + "\n"
                f"Supporting Excerpt: \"{r.excerpt}\"\n"
            )
        formatted_context = "\n".join(context_parts)

        return {
            "retrieved_references": [r.model_dump() for r in retrieved_refs],
            "references_context": formatted_context
        }

    def generate_lesson_node(state: LessonGraphState) -> Dict[str, Any]:
        attempt_number = state.get("attempt_number", 0) + 1
        topic = state["topic"]
        references_context = state.get("references_context", "")
        approved_rules = [LearnedRule(**r) for r in state.get("learned_guidance", [])]

        system_prompt = build_system_generator_prompt(approved_rules=approved_rules)
        
        if attempt_number == 1:
            # Initial generation attempt
            user_prompt = build_user_generator_prompt(topic, references_context)
        else:
            # Bounded regeneration attempt: incorporate specific rejection feedback
            last_decision = state.get("decision", {})
            feedback = last_decision.get("actionable_feedback_for_regeneration", "Fix previous errors.")
            prev_draft = state.get("current_draft", "")
            user_prompt = build_regeneration_prompt(topic, prev_draft, feedback, references_context)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        logger.info(f"Generating lesson draft (Attempt {attempt_number})...")
        gen_result = provider.generate_text(messages=messages, temperature=0.7)
        draft_content = gen_result.content

        actual_changes = None
        if attempt_number > 1 and prev_draft:
            actual_changes = summarize_draft_changes(prev_draft, draft_content)
            logger.info(f"Regeneration changes applied: {actual_changes}")

        out_state = {
            "attempt_number": attempt_number,
            "current_draft": draft_content
        }
        if actual_changes:
            rejection_logs = list(state.get("rejection_log", []))
            if rejection_logs:
                rejection_logs[-1]["actual_changes_made"] = actual_changes
                out_state["rejection_log"] = rejection_logs

        return out_state

    def inject_deliberate_error_node(state: LessonGraphState) -> Dict[str, Any]:
        """
        Isolated demonstration-only code path for evaluation gate verification.
        Injects the controlled false claim ONLY on attempt 1 if enable_deliberate_error is set.
        Never executes on subsequent regeneration attempts.
        """
        if state.get("enable_deliberate_error") and state.get("attempt_number") == 1:
            current = state.get("current_draft", "")
            logger.warning("[DEMO MODE]: Injecting controlled false claim into lesson draft for evaluator demonstration.")
            # Inject into section 2 or 3
            if "## 2. Why" in current:
                parts = current.split("## 2. Why", 1)
                modified = parts[0] + "## 2. Why" + CONTROLLED_FALSE_INJECTION + parts[1]
            else:
                modified = current + CONTROLLED_FALSE_INJECTION
            return {"current_draft": modified}
        return {}

    def evaluate_node(state: LessonGraphState) -> Dict[str, Any]:
        attempt_number = state["attempt_number"]
        draft_text = state["current_draft"]
        references_context = state.get("references_context", "")
        run_id = state["run_id"]

        logger.info(f"Evaluating lesson draft (Attempt {attempt_number})...")

        # Stage A: Deterministic Checks
        det_checks = run_deterministic_checks(draft_text)

        # Stage B: LLM Judge Evaluator
        llm_response = evaluate_lesson_with_llm(
            draft_text=draft_text,
            provider=provider,
            references_context=references_context
        )

        # Stage C: Python Combiner
        decision, rejection_record = combine_evaluations(
            attempt_number=attempt_number,
            draft_text=draft_text,
            deterministic_checks=det_checks,
            rubric_checkpoints=llm_response.checkpoints
        )

        # Persist attempt record to SQLite
        attempt_id = DatabaseRepository.record_attempt(
            run_id=run_id,
            attempt_number=attempt_number,
            draft_title=f"Lesson Draft Attempt {attempt_number}",
            draft_markdown=draft_text,
            status=decision.status,
            feedback_for_regeneration=decision.actionable_feedback_for_regeneration
        )

        # Persist checks
        DatabaseRepository.record_deterministic_checks(attempt_id, det_checks)
        DatabaseRepository.record_rubric_checks(attempt_id, llm_response.checkpoints)

        # Update draft history
        history = list(state.get("draft_history", []))
        history.append({
            "attempt_number": attempt_number,
            "draft": draft_text,
            "decision": decision.model_dump(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return {
            "deterministic_results": [d.model_dump() for d in det_checks],
            "rubric_results": [r.model_dump() for r in llm_response.checkpoints],
            "decision": decision.model_dump(),
            "draft_history": history
        }

    def record_rejection_node(state: LessonGraphState) -> Dict[str, Any]:
        decision_dict = state.get("decision", {})
        run_id = state["run_id"]
        attempt_number = state["attempt_number"]
        draft_text = state["current_draft"]
        
        rejection_logs = list(state.get("rejection_log", []))

        failed_checkpoints = []
        reasons = []
        instructions = []

        for d in state.get("deterministic_results", []):
            if not d.get("passed"):
                failed_checkpoints.append(f"deterministic:{d.get('check_id')}")
                reasons.append(d.get("failure_reason") or "Failed deterministic check")
                instructions.append(f"Fix deterministic check: {d.get('name')}")

        for r in state.get("rubric_results", []):
            if not r.get("passed"):
                failed_checkpoints.append(f"rubric:{r.get('checkpoint_id')}")
                reasons.append(r.get("failure_reason") or "Failed rubric dimension")
                if r.get("correction_instruction"):
                    instructions.append(r.get("correction_instruction"))

        rejection_record = {
            "attempt_number": attempt_number,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "failed_checkpoints": failed_checkpoints,
            "reasons": reasons,
            "corrective_instructions": instructions,
            "changes_required": decision_dict.get("actionable_feedback_for_regeneration") or "Quality revisions required.",
            "draft_snippet": draft_text[:300] + "..." if len(draft_text) > 300 else draft_text
        }

        # Save to SQLite rejection_logs table
        DatabaseRepository.record_rejection_log(
            run_id=run_id,
            attempt_number=attempt_number,
            failed_checkpoints=failed_checkpoints,
            reasons=reasons,
            corrective_instructions=instructions,
            changes_required=rejection_record["changes_required"],
            draft_snippet=rejection_record["draft_snippet"]
        )

        rejection_logs.append(rejection_record)

        # Self-evolution: If recurring failure observed, add candidate rule
        if any("jargon" in cp for cp in failed_checkpoints):
            DatabaseRepository.add_or_increment_candidate_rule(
                category="jargon",
                rule_text="Explicitly define technical terms with simple real-world Indian student analogies."
            )
        if any("weight" in r.lower() or "retrain" in r.lower() for r in reasons):
            DatabaseRepository.add_or_increment_candidate_rule(
                category="grounding",
                rule_text="Explicitly state that RAG operates at inference time and does not retrain neural weights."
            )

        return {"rejection_log": rejection_logs}

    def persist_final_state_node(state: LessonGraphState) -> Dict[str, Any]:
        run_id = state.get("run_id") or str(uuid.uuid4())

        # If run reached here due to early validation failure
        if state.get("status") == "FAILED" and state.get("error_message"):
            logger.warning(f"Persisting terminal validation failure for run {run_id}: {state.get('error_message')}")
            DatabaseRepository.update_run_status(
                run_id=run_id,
                status="FAILED",
                approved_lesson=None,
                attempts_count=0,
                completed_at=datetime.now(timezone.utc).isoformat()
            )
            return {
                "run_id": run_id,
                "status": "FAILED",
                "final_approved_lesson": None,
                "error_message": state.get("error_message")
            }

        decision_dict = state.get("decision", {})
        overall_passed = decision_dict.get("overall_passed", False)
        attempts_count = state.get("attempt_number", 1)
        completed_at = datetime.now(timezone.utc).isoformat()

        if overall_passed:
            final_status = "PASSED"
            approved_lesson = state.get("current_draft")
            logger.info(f"Run {run_id} PASSED after {attempts_count} attempt(s). Approved lesson persisted.")
        else:
            final_status = "FAILED"
            approved_lesson = None  # Failed lesson is NEVER marked as approved
            logger.warning(f"Run {run_id} FAILED after exhausting {attempts_count} attempt(s).")

        DatabaseRepository.update_run_status(
            run_id=run_id,
            status=final_status,
            approved_lesson=approved_lesson,
            attempts_count=attempts_count,
            completed_at=completed_at
        )

        return {
            "run_id": run_id,
            "status": final_status,
            "final_approved_lesson": approved_lesson
        }

    return {
        "validate_input_node": validate_input_node,
        "load_context_and_memory_node": load_context_and_memory_node,
        "retrieve_references_node": retrieve_references_node,
        "generate_lesson_node": generate_lesson_node,
        "inject_deliberate_error_node": inject_deliberate_error_node,
        "evaluate_node": evaluate_node,
        "record_rejection_node": record_rejection_node,
        "persist_final_state_node": persist_final_state_node
    }
