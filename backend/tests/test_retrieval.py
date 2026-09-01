import pytest

from app.retrieval import chunk_document, match_candidate_to_role, retrieve, role_evidence
from tests.factories import make_candidate, make_posting


def test_hybrid_retrieval_returns_ranked_cited_results():
    results = retrieve(make_posting(), limit=2)
    assert len(results) == 2
    assert all(result.citation.startswith("strategy:") for result in results)
    assert any("Python" in result.text for result in results)


def test_retrieval_limit_and_source_filter_are_enforced():
    assert retrieve(make_posting(), limit=0) == []
    assert len(retrieve(make_posting(), limit=20, source="strategy")) == 4
    assert retrieve(make_posting(), source="missing") == []


def test_document_chunking_preserves_citations_and_overlap():
    chunks = chunk_document("one two three four five six", "resume", chunk_size=4, overlap=2)
    assert [chunk.citation for chunk in chunks] == ["resume:chunk-1", "resume:chunk-2"]
    assert chunks[0].text.split()[-2:] == chunks[1].text.split()[:2]


def test_document_chunking_rejects_invalid_configuration():
    with pytest.raises(ValueError):
        chunk_document("content", "resume", chunk_size=5, overlap=5)


def test_candidate_role_match_returns_cited_explicit_resume_evidence():
    profile = make_candidate()
    result = match_candidate_to_role(make_posting(), profile, profile.evidence)
    assert result["qualification"] in {"strong", "partial"}
    assert result["matched_evidence"]
    assert result["matched_evidence"][0]["citation"].startswith("candidate:")
    assert result["confidence"] == "explicit"


def test_candidate_role_match_honors_hard_location_and_c2c_filters():
    profile = make_candidate()
    posting = make_posting(
        location="Remote, India",
        description="W2 only. No C2C or third parties. Build Python FastAPI services.",
    )
    result = match_candidate_to_role(posting, profile, profile.evidence)
    assert result["qualification"] == "blocked"
    assert len(result["disqualifiers"]) >= 2


def test_role_document_keeps_metadata_and_chunk_citations():
    evidence = role_evidence(make_posting())
    assert evidence[0].citation == "role:metadata"
    assert all(item.citation.startswith("role:") for item in evidence)
