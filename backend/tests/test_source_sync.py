from uuid import uuid4

import pytest

from app import source_sync
from app.connectors import ConnectorTarget
from app.models import C2CStatus, SearchProfile
from app.provenance import JobObservation, ProviderDefinition, ProviderType
from app.scoring import screen
from tests.factories import make_posting


@pytest.fixture(autouse=True)
def direct_graph_for_unit_tests(monkeypatch):
    async def run(_tenant, graph, posting, profile, _policy, **_kwargs):
        return await graph.ainvoke({"posting": posting, "profile": profile})

    monkeypatch.setattr(source_sync, "metered_screening", run)


class Connector:
    provider = ProviderDefinition(
        slug="greenhouse",
        name="Greenhouse",
        provider_type=ProviderType.employer_ats,
        intake_method="public_api",
        canonical_domain="boards.greenhouse.io",
        terms_status="approved",
        baseline_authority=90,
        direct_source_capable=True,
    )

    def provider_for(self, _target):
        return self.provider

    async def fetch(self, _target):
        return [
            JobObservation(
                provider_slug="greenhouse",
                provider_job_id="42",
                requisition_id="REQ-42",
                posting=make_posting(),
                end_client_name="Acme",
                engagement_type="contract",
                parser_version="v1",
                confidence=0.95,
            )
        ]


@pytest.mark.asyncio
async def test_sync_rescreens_and_enriches_existing_canonical_job(monkeypatch):
    job_id = uuid4()
    recorded = []
    monkeypatch.setattr(source_sync, "connector_for", lambda *_: Connector())
    monkeypatch.setattr(source_sync, "upsert_provider", async_value(str(uuid4())))
    monkeypatch.setattr(source_sync, "start_source_sync_run", async_value(str(uuid4())))
    monkeypatch.setattr(source_sync, "finish_source_sync_run", async_value(None))
    monkeypatch.setattr(
        source_sync,
        "find_job_by_canonical_key",
        async_value({"id": job_id, "fit_score": 88, "c2c_status": C2CStatus.likely}),
    )
    monkeypatch.setattr(source_sync, "upsert_job", async_value(str(job_id)))

    class Graph:
        calls = 0

        async def ainvoke(self, state):
            self.calls += 1
            return {"result": screen(state["posting"], state["profile"])}

    graph = Graph()
    monkeypatch.setattr(source_sync, "screening_graph", graph)

    async def record(*args):
        recorded.append(args)
        return str(uuid4())

    monkeypatch.setattr(source_sync, "record_job_observation", record)
    result = await source_sync.sync_target(
        "tenant",
        ConnectorTarget(adapter="greenhouse", slug="acme", organization_name="Acme"),
        client=object(),
    )
    assert result["created"] == 0
    assert result["enriched"] == 1
    assert graph.calls == 1
    assert recorded[0][2] == str(job_id)


def async_value(value):
    async def result(*_args, **_kwargs):
        return value

    return result


def test_observation_relevance_prioritizes_target_engineering_work():
    observation = JobObservation(
        provider_slug="greenhouse",
        provider_job_id="42",
        posting=make_posting(
            title="Staff AI Platform Engineer",
            location="Remote - United States",
            description="Build production agent systems using Python, FastAPI, LangGraph, MCP, and AWS.",
        ),
        parser_version="v1",
        confidence=0.95,
    )

    assert source_sync.observation_relevance(observation, SearchProfile()) >= 6
    assert source_sync.observation_matches_query(observation, "agent FastAPI")
    assert not source_sync.observation_matches_query(observation, "kubernetes")


@pytest.mark.asyncio
async def test_registry_sync_is_bounded_and_reports_partial_failures(monkeypatch):
    calls = []

    async def sync(_tenant, target, _profile, _client, **kwargs):
        calls.append((target.slug, kwargs["max_observations"]))
        if target.slug == "broken":
            raise __import__("httpx").ConnectError("offline")
        return {
            "target": target.slug,
            "selected": kwargs["max_observations"],
            "created": 2,
            "enriched": 1,
        }

    monkeypatch.setattr(source_sync, "sync_target", sync)
    targets = [
        ConnectorTarget(adapter="ashby", slug="first", organization_name="First"),
        ConnectorTarget(adapter="ashby", slug="broken", organization_name="Broken"),
        ConnectorTarget(adapter="ashby", slug="third", organization_name="Third"),
    ]
    result = await source_sync.sync_registry("tenant", targets, total_limit=7, per_target_limit=5)

    assert calls == [("first", 5), ("broken", 2), ("third", 2)]
    assert result["selected"] == 7
    assert result["created"] == 4
