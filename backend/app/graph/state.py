from typing import TypedDict, List, Dict, Any, Optional

class LessonGraphState(TypedDict, total=False):
    run_id: str
    topic: str
    enable_deliberate_error: bool
    attempt_number: int
    max_retries: int
    
    # Knowledge & Memory
    retrieved_references: List[Dict[str, Any]]
    references_context: str
    learned_guidance: List[Dict[str, Any]]
    
    # Draft generation
    current_draft: str
    draft_history: List[Dict[str, Any]]
    
    # Evaluation results
    deterministic_results: List[Dict[str, Any]]
    rubric_results: List[Dict[str, Any]]
    decision: Optional[Dict[str, Any]]
    rejection_log: List[Dict[str, Any]]
    
    # Final terminal outputs
    final_approved_lesson: Optional[str]
    status: str  # PENDING, IN_PROGRESS, PASSED, FAILED
    error_message: Optional[str]
