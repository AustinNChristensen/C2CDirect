import json
from pathlib import Path

from .models import JobPostingIn, SearchProfile
from .scoring import screen


def run_dataset(path: Path) -> dict:
    cases = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    results = []
    for case in cases:
        result = screen(JobPostingIn.model_validate(case["posting"]), SearchProfile())
        expected = case["expected"]
        passed = result.c2c_status == expected["c2c_status"]
        if "minimum_score" in expected:
            passed = passed and result.fit_score >= expected["minimum_score"]
        if "maximum_score" in expected:
            passed = passed and result.fit_score <= expected["maximum_score"]
        results.append({"name": case["name"], "passed": passed, "score": result.fit_score})
    return {"total": len(results), "passed": sum(r["passed"] for r in results), "results": results}
