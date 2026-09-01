from unittest.mock import ANY
from uuid import uuid4

import pytest

from app import ingestion_service
from app.models import C2CStatus, N8NBatch, ScreenedJob
from tests.factories import make_posting


@pytest.fixture(autouse=True)
def direct_graph_for_unit_tests(monkeypatch):
    async def run(_tenant, graph, posting, profile, _policy, **_kwargs):
        return await graph.ainvoke({"posting": posting, "profile": profile})

    monkeypatch.setattr(ingestion_service, "metered_screening", run)


def screened_job(score=85, status=C2CStatus.confirmed):
    return ScreenedJob(
        posting=make_posting(),
        c2c_status=status,
        fit_score=score,
        skill_matches=["python"],
        skill_gaps=[],
        reasons=["Strong match"],
        risks=[],
        recommended_action="Review",
    )


class Graph:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    async def ainvoke(self, _state):
        self.calls += 1
        return {"result": self.result}


@pytest.mark.asyncio
async def test_batch_persists_qualified_jobs_and_completes_event(monkeypatch):
    graph = Graph(screened_job())
    completed = []
    job_id = str(uuid4())
    monkeypatch.setattr(ingestion_service, "claim_ingestion_event", async_value(("claimed", None)))
    monkeypatch.setattr(ingestion_service, "find_job_by_fingerprint", async_value(None))
    monkeypatch.setattr(ingestion_service, "upsert_job", async_value(job_id))

    async def complete(*args):
        completed.append(args)

    monkeypatch.setattr(ingestion_service, "complete_ingestion_event", complete)
    batch = N8NBatch(run_id="run-0001", jobs=[make_posting()])
    result = await ingestion_service.ingest_batch("tenant", batch, graph)
    assert result["persisted"] == 1
    assert result["qualified"] == 1
    assert result["job_ids"] == [job_id]
    assert completed[0][3] == "completed"


@pytest.mark.asyncio
async def test_duplicate_job_skips_screening_and_ai_work(monkeypatch):
    graph = Graph(screened_job())
    existing = str(uuid4())
    monkeypatch.setattr(ingestion_service, "claim_ingestion_event", async_value(("claimed", None)))
    monkeypatch.setattr(ingestion_service, "find_job_by_fingerprint", async_value(existing))
    monkeypatch.setattr(ingestion_service, "complete_ingestion_event", async_value(None))
    batch = N8NBatch(run_id="run-0002", jobs=[make_posting()])
    result = await ingestion_service.ingest_batch("tenant", batch, graph)
    assert result["duplicates"] == 1
    assert result["screened"] == 0
    assert graph.calls == 0


@pytest.mark.asyncio
async def test_refresh_existing_rescreens_and_upserts(monkeypatch):
    graph = Graph(screened_job())
    existing = str(uuid4())
    monkeypatch.setattr(ingestion_service, "claim_ingestion_event", async_value(("claimed", None)))
    monkeypatch.setattr(ingestion_service, "find_job_by_fingerprint", async_value(existing))
    monkeypatch.setattr(ingestion_service, "upsert_job", async_value(existing))
    monkeypatch.setattr(ingestion_service, "complete_ingestion_event", async_value(None))
    batch = N8NBatch(run_id="run-refresh-0001", jobs=[make_posting()], refresh_existing=True)
    result = await ingestion_service.ingest_batch("tenant", batch, graph)
    assert result["persisted"] == 1
    assert result["duplicates"] == 1
    assert graph.calls == 1


@pytest.mark.asyncio
async def test_completed_event_returns_saved_summary_without_processing(monkeypatch):
    previous = {"run_id": "run-0003", "persisted": 2}
    monkeypatch.setattr(
        ingestion_service, "claim_ingestion_event", async_value(("completed", previous))
    )
    graph = Graph(screened_job())
    batch = N8NBatch(run_id="run-0003", jobs=[make_posting()])
    result = await ingestion_service.ingest_batch("tenant", batch, graph)
    assert result == {**previous, "replayed": True}
    assert graph.calls == 0


@pytest.mark.asyncio
async def test_unqualified_job_is_persisted_as_passed(monkeypatch):
    graph = Graph(screened_job(score=20, status=C2CStatus.rejected))
    moved = []
    job_id = str(uuid4())
    monkeypatch.setattr(ingestion_service, "claim_ingestion_event", async_value(("claimed", None)))
    monkeypatch.setattr(ingestion_service, "find_job_by_fingerprint", async_value(None))
    monkeypatch.setattr(ingestion_service, "upsert_job", async_value(job_id))
    monkeypatch.setattr(ingestion_service, "complete_ingestion_event", async_value(None))

    async def move(*args):
        moved.append(args)

    monkeypatch.setattr(ingestion_service, "move_job", move)
    batch = N8NBatch(run_id="run-0004", jobs=[make_posting()])
    result = await ingestion_service.ingest_batch("tenant", batch, graph)
    assert result["qualified"] == 0
    assert moved == [("tenant", ANY, "passed")]


@pytest.mark.asyncio
async def test_personal_batch_retains_unqualified_job_in_pipeline(monkeypatch):
    graph = Graph(screened_job(score=20, status=C2CStatus.likely))
    moved = []
    job_id = str(uuid4())
    monkeypatch.setattr(ingestion_service, "claim_ingestion_event", async_value(("claimed", None)))
    monkeypatch.setattr(ingestion_service, "find_job_by_fingerprint", async_value(None))
    monkeypatch.setattr(ingestion_service, "upsert_job", async_value(job_id))
    monkeypatch.setattr(ingestion_service, "complete_ingestion_event", async_value(None))

    async def move(*args):
        moved.append(args)

    monkeypatch.setattr(ingestion_service, "move_job", move)
    batch = N8NBatch(
        run_id="run-retain-0001",
        jobs=[make_posting()],
        retain_all_in_pipeline=True,
    )
    result = await ingestion_service.ingest_batch("tenant", batch, graph)
    assert result["retained_in_pipeline"] == 1
    assert moved == [("tenant", ANY, "new")]


def async_value(value):
    async def result(*_args, **_kwargs):
        return value

    return result
