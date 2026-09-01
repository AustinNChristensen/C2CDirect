from contextlib import contextmanager
from time import perf_counter
from uuid import uuid4

import structlog
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

log = structlog.get_logger()
provider = TracerProvider(resource=Resource.create({"service.name": "c2cdirect-api"}))
provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("c2cdirect.agent")


@contextmanager
def agent_run(operation: str, tenant_id: str = "local"):
    trace_id, started = uuid4().hex, perf_counter()
    with tracer.start_as_current_span(
        operation,
        attributes={
            "app.trace_id": trace_id,
            "app.tenant_id": tenant_id,
            "gen_ai.operation.name": operation,
        },
    ) as span:
        record = {"trace_id": trace_id, "operation": operation, "policy_decisions": []}
        try:
            yield record, span
            span.set_attribute("app.status", "succeeded")
        except Exception as exc:
            span.record_exception(exc)
            span.set_attribute("app.status", "failed")
            raise
        finally:
            record["latency_ms"] = round((perf_counter() - started) * 1000, 2)
            log.info("agent_run_complete", **record)
