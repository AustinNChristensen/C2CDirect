"""Inspectable hybrid retrieval with a deterministic local fallback.

The same scoring contract can be backed by PostgreSQL full-text search and pgvector in production.
"""

import re
from dataclasses import dataclass
from math import sqrt

from .models import CandidateEvidenceIn, CandidateProfileUpdate, JobPostingIn


@dataclass
class Evidence:
    text: str
    source: str
    citation: str = ""
    metadata: dict[str, str] | None = None


def chunk_document(
    text: str, source: str, chunk_size: int = 120, overlap: int = 20
) -> list[Evidence]:
    """Split source material into traceable word chunks for indexing."""
    if chunk_size < 1 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk_size must be positive and overlap must be smaller")
    words = text.split()
    chunks: list[Evidence] = []
    step = chunk_size - overlap
    for index, start in enumerate(range(0, len(words), step)):
        window = words[start : start + chunk_size]
        if not window:
            break
        chunks.append(
            Evidence(
                text=" ".join(window),
                source=source,
                citation=f"{source}:chunk-{index + 1}",
                metadata={"chunk": str(index + 1)},
            )
        )
        if start + chunk_size >= len(words):
            break
    return chunks


STRATEGY_EVIDENCE = [
    Evidence(
        "Target senior/staff full-stack and AI application work; avoid commodity frontend positioning.",
        "strategy",
        "strategy:positioning",
    ),
    Evidence(
        "Ask for the approved C2C range before volunteering a number; target $130–145/hr with higher AI bands.",
        "strategy",
        "strategy:rate",
    ),
    Evidence(
        "Prefer client → prime vendor → S-Corp and investigate every vendor layer.",
        "strategy",
        "strategy:vendor-chain",
    ),
    Evidence(
        "Python, FastAPI, LangGraph, RAG, MCP, evals, and observability close common AI-role gaps.",
        "strategy",
        "strategy:ai-skills",
    ),
]


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9+#.]+", text.lower()) if len(token) > 2}


def _vector(text: str, dimensions: int = 64) -> list[float]:
    values = [0.0] * dimensions
    for token in _tokens(text):
        values[sum(ord(char) for char in token) % dimensions] += 1.0
    magnitude = sqrt(sum(value * value for value in values)) or 1.0
    return [value / magnitude for value in values]


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def retrieve(
    posting: JobPostingIn,
    limit: int = 3,
    source: str | None = None,
    corpus: list[Evidence] | None = None,
) -> list[Evidence]:
    query = f"{posting.title} {posting.description}"
    query_tokens, query_vector = _tokens(query), _vector(query)
    candidates = [
        item for item in (corpus or STRATEGY_EVIDENCE) if source is None or item.source == source
    ]

    def score(item: Evidence) -> tuple[float, str]:
        item_tokens = _tokens(item.text)
        lexical = len(query_tokens & item_tokens) / max(1, len(query_tokens | item_tokens))
        semantic = _cosine(query_vector, _vector(item.text))
        return (0.65 * lexical + 0.35 * semantic, item.citation)

    return sorted(candidates, key=score, reverse=True)[: max(0, limit)]


def rank_evidence(
    query: str, corpus: list[Evidence], limit: int = 5
) -> list[tuple[float, Evidence]]:
    """Deterministic hybrid ranker shared by candidate and role retrieval.

    This is deliberately inspectable while provider embeddings are optional. The
    returned score is evidence similarity, not a claim that a person is hired
    or qualified.
    """
    query_tokens, query_vector = _tokens(query), _vector(query)
    ranked: list[tuple[float, Evidence]] = []
    for item in corpus:
        item_tokens = _tokens(item.text)
        lexical = len(query_tokens & item_tokens) / max(1, len(query_tokens | item_tokens))
        semantic = _cosine(query_vector, _vector(item.text))
        ranked.append((round((0.65 * lexical + 0.35 * semantic) * 100, 1), item))
    return sorted(ranked, key=lambda item: (item[0], item[1].citation), reverse=True)[
        : max(0, limit)
    ]


def role_evidence(posting: JobPostingIn) -> list[Evidence]:
    """Keep role constraints first-class, then create citeable description chunks."""
    metadata = (
        f"{posting.title} at {posting.company}. Location: {posting.location}. "
        f"Rate: {posting.rate_min or 'unknown'} to {posting.rate_max or 'unknown'} per hour."
    )
    return [Evidence(metadata, "role", "role:metadata", {"section": "metadata"})] + [
        Evidence(chunk.text, "role", f"role:description-{index + 1}", {"section": "description"})
        for index, chunk in enumerate(chunk_document(posting.description, "role-description"))
    ]


def candidate_evidence(items: list[CandidateEvidenceIn]) -> list[Evidence]:
    return [
        Evidence(
            item.text,
            "candidate",
            f"candidate:{item.source_ref}",
            {"kind": item.kind, "heading": item.heading, **item.metadata},
        )
        for item in items
    ]


def _location_disqualifier(posting: JobPostingIn, profile: CandidateProfileUpdate) -> str | None:
    location = posting.location.lower()
    preferences = " ".join(profile.location_preferences).lower()
    if "india" in location and "india" not in preferences:
        return "Role is explicitly Remote India; candidate preference does not include India."
    if "canada" in location and "canada" not in preferences:
        return "Role is explicitly Remote Canada; candidate preference does not include Canada."
    if (
        any(term in location for term in ("united states", "u.s.", " usa", " us "))
        and "u.s" not in preferences
        and "us" not in preferences
    ):
        return "Role is explicitly U.S.-limited; candidate preference does not include U.S."
    return None


def match_candidate_to_role(
    posting: JobPostingIn,
    profile: CandidateProfileUpdate,
    evidence_items: list[CandidateEvidenceIn],
    role_chunks: list[Evidence] | None = None,
) -> dict:
    """Return an evidence-backed match without inferring unsupported experience."""
    disqualifiers: list[str] = []
    location_issue = _location_disqualifier(posting, profile)
    if location_issue:
        disqualifiers.append(location_issue)
    chunks = role_chunks or role_evidence(posting)
    role_text = " ".join(chunk.text for chunk in chunks)
    lowered = role_text.lower()
    if profile.c2c_preference and any(
        term in lowered for term in ("no c2c", "w2 only", "no third parties")
    ):
        disqualifiers.append("Posting explicitly rejects C2C / third-party engagement.")
    if profile.rate_floor and posting.rate_max and posting.rate_max < profile.rate_floor:
        disqualifiers.append(
            f"Posted rate ceiling ${posting.rate_max}/hr is below the ${profile.rate_floor}/hr floor."
        )
    candidate_chunks = candidate_evidence(evidence_items)
    ranked = rank_evidence(role_text, candidate_chunks, limit=5)
    role_ranked = rank_evidence(" ".join(item.text for item in candidate_chunks), chunks, limit=3)
    matches = [
        {
            "citation": item.citation,
            "heading": (item.metadata or {}).get("heading", "Candidate evidence"),
            "kind": (item.metadata or {}).get("kind", "experience"),
            "text": item.text,
            "similarity": score,
            "basis": "explicit resume/project evidence",
        }
        for score, item in ranked
        if score >= 8
    ]
    skill_gaps = [skill for skill in profile.skills if skill.lower() not in lowered]
    mentioned_skills = [skill for skill in profile.skills if skill.lower() in lowered]
    qualification = "blocked" if disqualifiers else "strong" if len(matches) >= 3 else "partial"
    return {
        "qualification": qualification,
        "disqualifiers": disqualifiers,
        "matched_evidence": matches,
        "matched_role_evidence": [
            {
                "citation": item.citation,
                "section": (item.metadata or {}).get("section", "description"),
                "text": item.text,
                "similarity": score,
            }
            for score, item in role_ranked
            if score >= 8
        ],
        "tailored_evidence": matches[:3],
        "explicit_skills_in_role": mentioned_skills,
        "candidate_skills_not_mentioned": skill_gaps,
        "confidence": "explicit" if matches else "insufficient_evidence",
        "method": "hard_filters_then_lexical_and_deterministic_semantic_retrieval",
    }
