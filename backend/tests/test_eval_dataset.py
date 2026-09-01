from pathlib import Path

from app.eval_runner import run_dataset


def test_regression_dataset_passes():
    report = run_dataset(Path(__file__).parents[1] / "evals" / "cases.jsonl")
    assert report["passed"] == report["total"], report
