import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from backend.app.graph.state import LessonGraphState
from backend.app.graph.nodes import create_nodes
from backend.app.graph.edges import route_after_input_validation, route_after_eval, route_after_rejection
from backend.app.providers.base import LLMProvider
from backend.app.providers.groq_provider import GroqProvider
from backend.app.providers.mock_provider import MockProvider
from backend.app.database.repository import DatabaseRepository
from backend.app.core.config import settings
from backend.app.core.logging import logger

def build_lesson_graph(provider: Optional[LLMProvider] = None):
    """Compiles and returns the LangGraph executable state machine."""
    if provider is None:
        if settings.GROQ_API_KEY:
            provider = GroqProvider()
        else:
            logger.warning("GROQ_API_KEY unset; defaulting to MockProvider for offline execution.")
            provider = MockProvider()

    nodes = create_nodes(provider)
    workflow = StateGraph(LessonGraphState)

    # Register Nodes
    workflow.add_node("validate_input", nodes["validate_input_node"])
    workflow.add_node("load_context_and_memory", nodes["load_context_and_memory_node"])
    workflow.add_node("retrieve_references", nodes["retrieve_references_node"])
    workflow.add_node("generate_lesson", nodes["generate_lesson_node"])
    workflow.add_node("inject_deliberate_error", nodes["inject_deliberate_error_node"])
    workflow.add_node("evaluate", nodes["evaluate_node"])
    workflow.add_node("record_rejection", nodes["record_rejection_node"])
    workflow.add_node("persist_final_state", nodes["persist_final_state_node"])

    # Linear and conditional entry edges
    workflow.add_edge(START, "validate_input")
    
    # Conditional branching from input validation gate (F-01)
    workflow.add_conditional_edges(
        "validate_input",
        route_after_input_validation,
        {
            "load_context_and_memory": "load_context_and_memory",
            "persist_final_state": "persist_final_state"
        }
    )
    
    workflow.add_edge("load_context_and_memory", "retrieve_references")
    workflow.add_edge("retrieve_references", "generate_lesson")
    workflow.add_edge("generate_lesson", "inject_deliberate_error")
    workflow.add_edge("inject_deliberate_error", "evaluate")

    # Conditional branching from evaluation gate
    workflow.add_conditional_edges(
        "evaluate",
        route_after_eval,
        {
            "persist_final_state": "persist_final_state",
            "record_rejection": "record_rejection"
        }
    )

    # Conditional branching from rejection log
    workflow.add_conditional_edges(
        "record_rejection",
        route_after_rejection,
        {
            "generate_lesson": "generate_lesson",
            "persist_final_state": "persist_final_state"
        }
    )

    workflow.add_edge("persist_final_state", END)

    app = workflow.compile()
    return app

def run_lesson_workflow(
    topic: str = "Introduction to RAG",
    enable_deliberate_error: bool = False,
    provider: Optional[LLMProvider] = None,
    max_retries: int = 2
) -> Dict[str, Any]:
    """High-level runner executing the LangGraph state machine from start to finish with exception-safe persistence."""
    app = build_lesson_graph(provider=provider)
    run_id = str(uuid.uuid4())
    safe_max_retries = min(max(int(max_retries), 1), 2)
    initial_state: LessonGraphState = {
        "run_id": run_id,
        "topic": topic,
        "enable_deliberate_error": enable_deliberate_error,
        "max_retries": safe_max_retries,
        "attempt_number": 0,
        "draft_history": [],
        "rejection_log": []
    }
    logger.info(f"Starting LangGraph lesson workflow for topic '{topic}' (Run ID: {run_id}, Demo mode: {enable_deliberate_error})...")
    try:
        final_state = app.invoke(initial_state)
        return final_state
    except Exception as e:
        logger.error(f"Unhandled exception in LangGraph workflow for run {run_id}: {e}")
        # F-11 & F-04: Ensure failure state is permanently recorded in SQLite to prevent orphaned PENDING runs
        try:
            existing = DatabaseRepository.get_run(run_id)
            if not existing:
                DatabaseRepository.create_run(
                    run_id=run_id,
                    topic=topic,
                    deliberate_error_injected=enable_deliberate_error,
                    max_retries=safe_max_retries
                )
            DatabaseRepository.update_run_status(
                run_id=run_id,
                status="FAILED",
                completed_at=datetime.now(timezone.utc).isoformat()
            )
        except Exception as db_err:
            logger.error(f"Failed to record terminal failure state in database: {db_err}")
        raise
