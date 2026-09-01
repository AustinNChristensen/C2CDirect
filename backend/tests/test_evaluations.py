from app.evaluations import evaluate_screening


def test_evaluation_rejects_ungrounded_reasons():
    result = evaluate_screening(
        ["Unrelated unsupported assertion"], ["C2C rate and Python evidence"]
    )
    assert not result.passed


def test_evaluation_tracks_citations_and_safety():
    result = evaluate_screening(
        ["Python evidence supports the recommendation"],
        ["Python evidence supports the recommendation"],
        citations=["resume:project-1"],
    )
    assert result.passed
    assert result.citation_coverage == 1
    assert result.safety_passed


def test_safety_failure_fails_evaluation_even_when_grounded():
    result = evaluate_screening(
        ["Python evidence supports the recommendation"],
        ["Python evidence supports the recommendation"],
        safety_passed=False,
    )
    assert not result.passed
