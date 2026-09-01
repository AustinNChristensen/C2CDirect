import pytest
from pydantic import ValidationError

from app.models import RecruiterContactIn, RecruiterContactPatch


def test_recruiter_contact_requires_valid_stage_and_email():
    contact = RecruiterContactIn(name="Jamie Recruiter", email="jamie@example.com")
    assert contact.relationship_stage == "target"
    with pytest.raises(ValidationError):
        RecruiterContactIn(name="Jamie Recruiter", email="not-an-email")
    with pytest.raises(ValidationError):
        RecruiterContactIn(name="Jamie Recruiter", relationship_stage="submitted")


def test_follow_up_can_be_explicitly_cleared():
    patch = RecruiterContactPatch(next_follow_up_at=None, mark_contacted=True)
    assert "next_follow_up_at" in patch.model_fields_set
    assert patch.mark_contacted
