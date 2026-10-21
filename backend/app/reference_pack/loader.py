import json
import re
from pathlib import Path
from typing import List, Optional
from backend.app.schemas.reference import ReferencePack, ReferenceItem, ReferenceQuery, ReferenceSearchResult
from backend.app.core.logging import logger

_CACHED_PACK: Optional[ReferencePack] = None

def get_reference_pack_path() -> Path:
    return Path(__file__).resolve().parent / "rag_reference.json"

def load_reference_pack() -> ReferencePack:
    global _CACHED_PACK
    if _CACHED_PACK is not None:
        return _CACHED_PACK

    path = get_reference_pack_path()
    if not path.exists():
        raise FileNotFoundError(f"Reference pack file not found at {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = [ReferenceItem(**item) for item in data.get("items", [])]
    _CACHED_PACK = ReferencePack(
        pack_name=data.get("pack_name", "Curated Reference Pack"),
        version=data.get("version", "1.0.0"),
        topic=data.get("topic", "Introduction to RAG"),
        items=items
    )
    logger.info(f"Loaded reference pack with {len(items)} primary sources (v{_CACHED_PACK.version})")
    return _CACHED_PACK

def search_reference_pack(query: str, max_results: int = 3) -> List[ReferenceSearchResult]:
    """
    Controlled local lookup tool that searches curated reference materials.
    - Strictly bounded (max_results clamped 1-5).
    - Only reads in-memory curated pack.
    - No filesystem, no network, no code execution.
    """
    # Validate via Pydantic model
    validated_query = ReferenceQuery(query=query.strip(), max_results=max_results)
    pack = load_reference_pack()
    
    # Tokenize query terms for keyword scoring
    terms = [re.escape(w.lower()) for w in re.findall(r"\w+", validated_query.query) if len(w) > 2]
    if not terms:
        return []

    scored_items = []
    for item in pack.items:
        score = 0
        searchable_text = f"{item.title} {' '.join(item.claims)} {item.excerpt}".lower()
        matched_claims = []
        for term in terms:
            if re.search(r"\b" + term + r"\b", searchable_text):
                score += 2
        for claim in item.claims:
            if any(term in claim.lower() for term in terms):
                matched_claims.append(claim)

        if score > 0 or matched_claims:
            scored_items.append((score, item, matched_claims))

    # Sort descending by score
    scored_items.sort(key=lambda x: x[0], reverse=True)
    results = []
    for _, item, matched_claims in scored_items[:validated_query.max_results]:
        results.append(
            ReferenceSearchResult(
                source_id=item.source_id,
                title=item.title,
                url=item.url,
                excerpt=item.excerpt,
                matched_claims=matched_claims if matched_claims else item.claims[:2]
            )
        )
    return results

def get_all_reference_ids() -> List[str]:
    pack = load_reference_pack()
    return [item.source_id for item in pack.items]
