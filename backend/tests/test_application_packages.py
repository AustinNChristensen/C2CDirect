from app.application_packages import build_application_package
from app.retrieval import match_candidate_to_role
from tests.factories import make_candidate, make_posting


def test_application_package_only_uses_cited_candidate_evidence():
    candidate = make_candidate()
    posting = make_posting()
    match = match_candidate_to_role(posting, candidate, candidate.evidence)

    package = build_application_package(posting, candidate, match)

    assert package["resume_evidence"]
    assert all(item["citation"].startswith("candidate:") for item in package["resume_evidence"])
    assert "Draft only" in package["disclaimer"]
    assert "Confirm engagement classification" in package["verification"][0]


def test_application_package_requests_rate_verification_when_absent():
    candidate = make_candidate()
    posting = make_posting(rate_min=None, rate_max=None)
    package = build_application_package(
        posting, candidate, match_candidate_to_role(posting, candidate, candidate.evidence)
    )

    assert any("hourly rate range" in item for item in package["verification"])
