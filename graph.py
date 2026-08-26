"""Grafo jerárquico: el supervisor rutea; los especialistas vuelven a él.

``route_from_supervisor`` devuelve un ``Literal`` con nombres de nodo: eso es
lo que pide la consigna para las aristas condicionales. ``FINISH`` se mapea a
``writer``, que pisa ``output.md`` y termina en ``END``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import RetryPolicy

from agents.analyst_agent import make_analyst_node
from agents.research_agent import make_researcher_node
from agents.retry import NODE_RETRY, node_error_handler
from agents.supervisor import make_supervisor_node
from agents.writer import make_writer_node
from config import RECURSION_LIMIT
from state import OrchestratorState, initial_fields

NodeFn = Callable[[OrchestratorState], dict]
Route = Literal["researcher", "analyst", "writer"]


def route_from_supervisor(state: OrchestratorState) -> Route:
    """Lee ``next_agent`` y lo traduce a un destino del grafo."""
    nxt = state.get("next_agent")
    if nxt in ("researcher", "analyst"):
        return nxt
    return "writer"


def build_graph(
    llm: BaseChatModel | None = None,
    *,
    supervisor: NodeFn | None = None,
    researcher: NodeFn | None = None,
    analyst: NodeFn | None = None,
    writer: NodeFn | None = None,
    retry_policy: RetryPolicy | None = NODE_RETRY,
) -> CompiledStateGraph:
    if supervisor is None or researcher is None or analyst is None:
        if llm is None:
            from clients.factory import build_role_models

            models = build_role_models()
        else:
            models = {"supervisor": llm, "researcher": llm, "analyst": llm}
        supervisor = supervisor or make_supervisor_node(models["supervisor"])
        researcher = researcher or make_researcher_node(models["researcher"])
        analyst = analyst or make_analyst_node(models["analyst"])
    writer = writer or make_writer_node()

    builder = StateGraph(OrchestratorState)
    if retry_policy is not None:
        builder.set_node_defaults(
            retry_policy=retry_policy,
            error_handler=node_error_handler,
        )
    builder.add_node("supervisor", supervisor)
    builder.add_node("researcher", researcher)
    builder.add_node("analyst", analyst)
    builder.add_node("writer", writer, retry_policy=None, error_handler=None)
    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "researcher": "researcher",
            "analyst": "analyst",
            "writer": "writer",
        },
    )
    builder.add_edge("researcher", "supervisor")
    builder.add_edge("analyst", "supervisor")
    builder.add_edge("writer", END)
    return builder.compile()


def invoke_config() -> dict:
    return {"recursion_limit": RECURSION_LIMIT}


def stream_query(
    graph: CompiledStateGraph,
    query: str,
    on_hop: Callable[[str], None] | None = None,
) -> tuple[list[str], dict]:
    """Corre el grafo en stream: hops de nodos padre + estado final."""
    hops: list[str] = []
    final: dict | None = None
    for mode, data in graph.stream(
        {**initial_fields(), "messages": [HumanMessage(content=query)]},
        invoke_config(),
        stream_mode=["updates", "values"],
    ):
        if mode == "updates":
            for node in data:
                if node.startswith("__"):
                    continue
                hops.append(node)
                if on_hop is not None:
                    on_hop(node)
        else:
            final = data
    if final is None:
        raise RuntimeError("el grafo no emitió estado final")
    return hops, final


def run_query(graph: CompiledStateGraph, query: str) -> dict:
    return graph.invoke(
        {**initial_fields(), "messages": [HumanMessage(content=query)]},
        invoke_config(),
    )
