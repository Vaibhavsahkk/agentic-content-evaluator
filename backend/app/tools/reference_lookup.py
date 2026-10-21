from typing import Dict, Any, List
import json
from backend.app.reference_pack.loader import search_reference_pack
from backend.app.core.logging import logger

SEARCH_REFERENCE_TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "search_reference_pack",
        "description": (
            "Search the curated reference pack for authoritative primary sources and verified factual claims "
            "regarding Retrieval-Augmented Generation (RAG)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Specific search query keywords, e.g. 'parametric memory weights' or 'chunking embeddings'"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of source results to return (between 1 and 5)",
                    "default": 3
                }
            },
            "required": ["query"],
            "additionalProperties": False
        }
    }
}

def execute_reference_tool(arguments: Dict[str, Any]) -> str:
    """
    Executes a bounded search across the curated reference pack.
    Returns a formatted JSON string of retrieved evidence.
    """
    query = arguments.get("query", "").strip()
    max_results = min(max(int(arguments.get("max_results", 3)), 1), 5)
    
    if not query:
        return json.dumps({"error": "Query parameter cannot be empty.", "results": []})
        
    try:
        results = search_reference_pack(query, max_results=max_results)
        serialized = [
            {
                "source_id": r.source_id,
                "title": r.title,
                "url": r.url,
                "matched_claims": r.matched_claims,
                "excerpt": r.excerpt
            }
            for r in results
        ]
        logger.info(f"Executed reference lookup for query '{query}': returned {len(serialized)} results.")
        return json.dumps({"results": serialized, "count": len(serialized)}, indent=2)
    except Exception as e:
        logger.error(f"Error executing reference tool: {e}")
        return json.dumps({"error": str(e), "results": []})
