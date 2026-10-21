import pytest
from backend.app.reference_pack.loader import (
    load_reference_pack,
    search_reference_pack,
    get_all_reference_ids
)

def test_load_reference_pack():
    pack = load_reference_pack()
    assert pack.topic == "Introduction to RAG"
    assert len(pack.items) >= 4
    ids = get_all_reference_ids()
    assert "REF-01" in ids
    assert "REF-02" in ids
    assert "REF-03" in ids
    assert "REF-04" in ids

def test_search_reference_pack_bounded():
    # Query for retrieval and parametric memory
    results = search_reference_pack("parametric memory weights", max_results=2)
    assert len(results) <= 2
    assert any(r.source_id == "REF-01" for r in results)

    # Upper bound enforced (max_results clamped to 5 by Pydantic)
    results_all = search_reference_pack("RAG", max_results=5)
    assert len(results_all) <= 5

def test_search_reference_pack_empty_on_mismatch():
    results = search_reference_pack("quantum photosynthesis biological chlorophyll", max_results=3)
    assert len(results) == 0
