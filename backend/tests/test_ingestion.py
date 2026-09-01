from app.ingestion import content_fingerprint, enrich_posting, normalize_email_alert
from tests.factories import make_posting


def test_email_alert_normalization_is_deterministic():
    body = "Company: Acme\nLocation: Remote\nC2C contract with Python FastAPI and LangGraph for twelve months."
    first = normalize_email_alert("Job alert: AI Engineer", body)
    second = normalize_email_alert("Job alert: AI Engineer", body)
    assert first.company == "Acme"
    assert content_fingerprint(first) == content_fingerprint(second)


def test_extracts_hourly_range_duration_and_engagement_terms():
    posting = make_posting().model_copy(
        update={
            "rate_min": None,
            "rate_max": None,
            "description": "Remote 6-8 month contract at $100-$120/hr. W2, 1099, or C2C accepted. "
            "Build production Python and TypeScript systems.",
        }
    )
    enriched = enrich_posting(posting)
    assert (enriched.rate_min, enriched.rate_max) == (100, 120)
    assert enriched.contract_duration == "6-8 month"
    assert enriched.engagement_type == "C2C / 1099 / W2"


def test_structured_rate_is_not_overwritten_by_description():
    posting = make_posting().model_copy(
        update={"rate_min": 150, "rate_max": 175, "description": "Contract pays $80-$90/hr."}
    )
    enriched = enrich_posting(posting)
    assert (enriched.rate_min, enriched.rate_max) == (150, 175)


def test_extracts_single_hourly_rate():
    posting = make_posting().model_copy(
        update={"rate_min": None, "rate_max": None, "description": "Rate: $135/hour on C2C."}
    )
    enriched = enrich_posting(posting)
    assert (enriched.rate_min, enriched.rate_max) == (135, 135)
