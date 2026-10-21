from typing import Literal
from backend.app.graph.state import LessonGraphState
from backend.app.core.logging import logger

def route_after_input_validation(state: LessonGraphState) -> Literal["load_context_and_memory", "persist_final_state"]:
    """
    Evaluates whether the input topic passed validation.
    - If valid: routes to load_context_and_memory.
    - If invalid (status=FAILED): routes directly to persist_final_state, bypassing retrieval and generation.
    """
    if state.get("status") == "FAILED":
        logger.warning(f"Input validation rejected topic '{state.get('topic')}'. Routing to persist_final_state.")
        return "persist_final_state"
    return "load_context_and_memory"

def route_after_eval(state: LessonGraphState) -> Literal["persist_final_state", "record_rejection"]:
    """
    Evaluates whether the draft cleared all gates or if content retries remain.
    - If passed: routes to persist_final_state (status=PASSED).
    - If failed: routes to record_rejection.
    """
    decision = state.get("decision", {})
    overall_passed = decision.get("overall_passed", False)
    
    if overall_passed:
        logger.info("Evaluation gate: PASSED. Proceeding to terminal persistence.")
        return "persist_final_state"
    
    logger.info(f"Evaluation gate: REJECTED on attempt {state.get('attempt_number', 1)}.")
    return "record_rejection"

def route_after_rejection(state: LessonGraphState) -> Literal["generate_lesson", "persist_final_state"]:
    """
    Controls bounded regeneration loop:
    MAX_RETRIES = 2 (1 initial generation + up to 2 retries = 3 total attempts).
    - If attempt_number < 1 + max_retries: routes to generate_lesson for revision.
    - If attempt_number >= 1 + max_retries: terminates loop and routes to persist_final_state (status=FAILED).
    """
    attempt_number = state.get("attempt_number", 1)
    raw_retries = state.get("max_retries", 2)
    # F-06: Strict application-level clamp to at most 2 retries
    max_retries = min(max(int(raw_retries), 1), 2)
    max_total_attempts = 1 + max_retries

    if attempt_number < max_total_attempts:
        logger.info(f"Retries remaining ({attempt_number}/{max_total_attempts}). Regenerating revised draft...")
        return "generate_lesson"
    else:
        logger.warning(f"Exhausted maximum retries ({attempt_number}/{max_total_attempts}). Terminating as FAILED.")
        return "persist_final_state"
