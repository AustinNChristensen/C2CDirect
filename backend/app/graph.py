from typing import TypedDict

from langchain_core.runnables import RunnableLambda
from langgraph.graph import END, StateGraph

from .evaluations import EvaluationResult, evaluate_screening
from .guardrails import GuardrailDecision, inspect_posting
from .model_routing import ModelTarget, select_model
from .model_runtime import (
    RuntimeUsage,
    configured,
    enrich_screening,
    runtime_estimate,
    runtime_status,
)
from .models import BudgetPolicy, CostEstimate, JobPostingIn, ScreenedJob, SearchProfile
from .retrieval import retrieve
from .scoring import screen


class ScreeningState(TypedDict, total=False):
    posting: JobPostingIn
    profile: SearchProfile
    result: ScreenedJob
    evidence: list[str]
    citations: list[str]
    cost_estimate: CostEstimate
    policy: BudgetPolicy
    guardrail: GuardrailDecision
    evaluation: EvaluationResult
    model_target: ModelTarget
    model_usage: RuntimeUsage
    runtime_config: dict
    approval_required: bool


def guardrail_node(state: ScreeningState):
    decision = inspect_posting(state["posting"])
    posting = state["posting"]
    if decision.redacted_description != posting.description:
        posting = posting.model_copy(update={"description": decision.redacted_description})
    return {"guardrail": decision, "posting": posting}


def safety_route(state: ScreeningState):
    return "score" if state["guardrail"].allowed else "unsafe"


def unsafe_node(state: ScreeningState):
    result = screen(state["posting"], state["profile"]).model_copy(
        update={"recommended_action": "Quarantined: unsafe instructions detected in posting"}
    )
    return {
        "result": result,
        "evidence": [],
        "approval_required": True,
        "cost_estimate": CostEstimate(
            model="local-rules",
            estimated_input_tokens=0,
            estimated_output_tokens=0,
            estimated_cost_usd=0,
            allowed=False,
            gate_reason="prompt_injection_detected",
        ),
        "model_target": select_model(0, available_providers=(), sensitive_data=True),
    }


def score_node(state: ScreeningState):
    return {"result": screen(state["posting"], state["profile"])}


def evidence_node(state: ScreeningState):
    evidence = retrieve(state["posting"])
    return {
        "evidence": [item.text for item in evidence],
        "citations": [item.citation for item in evidence],
    }


def cost_gate_node(state: ScreeningState):
    posting = state["posting"]
    config = state.get("runtime_config")
    status = runtime_status(config)
    target = ModelTarget(status["provider"], status["model"], "custom", "self_hosted_configuration")
    estimate = runtime_estimate(
        max(500, len(posting.description) // 3),
        600,
        state.get("policy", BudgetPolicy()),
        config,
    )
    return {"cost_estimate": estimate, "model_target": target}


def gate_route(state: ScreeningState):
    return "retrieve_evidence" if state["cost_estimate"].allowed else "blocked"


def blocked_node(state: ScreeningState):
    result = state["result"].model_copy(
        update={"recommended_action": f"Blocked by cost gate: {state['cost_estimate'].gate_reason}"}
    )
    return {"result": result, "evidence": []}


async def model_enrichment_node(state: ScreeningState):
    config = state.get("runtime_config")
    result, usage = await enrich_screening(
        state["posting"], state["profile"], state["result"], config
    )
    if configured(config) and usage.status == "succeeded":
        estimate = state["cost_estimate"].model_copy(
            update={
                "estimated_input_tokens": usage.input_tokens,
                "estimated_output_tokens": usage.output_tokens,
                "estimated_cost_usd": usage.actual_cost_usd,
            }
        )
        return {"result": result, "model_usage": usage, "cost_estimate": estimate}
    return {"result": result, "model_usage": usage}


def model_enrichment_node_sync(state: ScreeningState):
    """Keep the deterministic graph usable by synchronous local tooling and tests."""
    config = state.get("runtime_config")
    status = runtime_status(config)
    return {
        "model_usage": RuntimeUsage(
            status["provider"],
            status["model"],
            0,
            0,
            0,
            0,
            "skipped" if not configured(config) else "async_required",
        )
    }


def evaluation_node(state: ScreeningState):
    evidence = state.get("evidence", [])
    result = state["result"]
    evaluation = evaluate_screening(
        result.reasons,
        evidence,
        citations=state.get("citations", []),
        safety_passed=state["guardrail"].allowed,
    )
    return {"evaluation": evaluation}


def approval_node(state: ScreeningState):
    estimate = state["cost_estimate"]
    policy = state.get("policy", BudgetPolicy())
    requires_approval = estimate.estimated_cost_usd >= policy.require_approval_above_usd or state[
        "result"
    ].recommended_action.lower().startswith(("contact", "apply", "submit"))
    return {"approval_required": requires_approval}


def build_graph():
    graph = StateGraph(ScreeningState)
    graph.add_node("guard_input", guardrail_node)
    graph.add_node("score", score_node)
    graph.add_node("retrieve_evidence", evidence_node)
    graph.add_node("cost_gate", cost_gate_node)
    graph.add_node("blocked", blocked_node)
    graph.add_node(
        "model_enrichment",
        RunnableLambda(model_enrichment_node_sync, afunc=model_enrichment_node),
    )
    graph.add_node("unsafe", unsafe_node)
    graph.add_node("evaluate", evaluation_node)
    graph.add_node("approval", approval_node)
    graph.set_entry_point("guard_input")
    graph.add_conditional_edges("guard_input", safety_route, {"score": "score", "unsafe": "unsafe"})
    graph.add_edge("score", "cost_gate")
    graph.add_conditional_edges(
        "cost_gate", gate_route, {"retrieve_evidence": "retrieve_evidence", "blocked": "blocked"}
    )
    graph.add_edge("retrieve_evidence", "model_enrichment")
    graph.add_edge("model_enrichment", "evaluate")
    graph.add_edge("evaluate", "approval")
    graph.add_edge("approval", END)
    graph.add_edge("blocked", END)
    graph.add_edge("unsafe", END)
    return graph.compile()


screening_graph = build_graph()
