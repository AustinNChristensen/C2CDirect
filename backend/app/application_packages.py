"""Human-approved application packages assembled only from cited candidate evidence."""

from .models import CandidateProfileUpdate, JobPostingIn


def build_application_package(posting: JobPostingIn, candidate: CandidateProfileUpdate, match: dict) -> dict:
    """Create an honest draft; it never claims skills absent from candidate evidence."""
    resume_evidence = match.get("tailored_evidence", [])[:4]
    role_evidence = match.get("role_evidence", [])[:3]
    disqualifiers = match.get("disqualifiers", [])
    verification = [
        "Confirm engagement classification (C2C, W-2, or other) before applying.",
        "Confirm work-location jurisdiction and work-authorization requirements.",
    ]
    if posting.rate_min is None and posting.rate_max is None:
        verification.append("Ask for the hourly rate range before investing in a full application.")
    if match.get("candidate_skills_not_mentioned"):
        verification.append("Do not claim unmentioned skills; address relevant gaps only after review.")
    evidence_lines = " ".join(item["text"] for item in resume_evidence[:2])
    cover_note = (
        f"I am interested in the {posting.title} opportunity at {posting.company}. "
        f"My relevant experience includes: {evidence_lines or 'reviewed experience available in my resume.'} "
        "I would welcome the chance to confirm the engagement structure, location eligibility, and role priorities."
    )
    return {
        "resume_evidence": resume_evidence,
        "role_evidence": match.get("matched_role_evidence", role_evidence),
        "gaps": disqualifiers + [
            f"Role does not explicitly mention: {skill}" for skill in match.get("candidate_skills_not_mentioned", [])[:5]
        ],
        "verification": verification,
        "cover_note": cover_note,
        "qualification": match.get("qualification", "partial"),
        "disclaimer": "Draft only. Review every claim and submit manually.",
    }
