"""RetryPolicy: transitorios se reintentan; 403 y bugs no."""

from __future__ import annotations

import uuid

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import NodeError
from langgraph.types import RetryPolicy

from agents.retry import is_transient_error, make_error_handler, node_error_handler
from graph import build_graph, run_query
from state import initial_fields


def test_provider_returned_error_es_transitorio():
    assert is_transient_error(RuntimeError("Provider returned error"))
    assert is_transient_error(Exception("502 overloaded"))


def test_connection_error_es_transitorio():
    assert is_transient_error(ConnectionError("red caída"))


def test_forbidden_no_se_reintenta():
    class ForbiddenResponseError(Exception):
        pass

    assert not is_transient_error(
        ForbiddenResponseError("inkling is only available on agentic harnesses")
    )


def test_value_error_no_se_reintenta():
    assert not is_transient_error(ValueError("schema inválido"))


def test_error_handler_cierra_con_last_error():
    err = NodeError(node="supervisor", error=RuntimeError("Provider returned error"))
    cmd = node_error_handler(initial_fields(), err)
    assert cmd.goto == "writer"
    assert "supervisor" in cmd.update["last_error"]
    assert cmd.update["next_agent"] == "FINISH"


def test_make_error_handler_default_sink_es_writer():
    err = NodeError(node="supervisor", error=RuntimeError("Provider returned error"))
    cmd = make_error_handler()(initial_fields(), err)
    assert cmd.goto == "writer"


def test_make_error_handler_con_hitl_manda_a_approval():
    err = NodeError(node="researcher", error=RuntimeError("Provider returned error"))
    cmd = make_error_handler("approval")(initial_fields(), err)
    assert cmd.goto == "approval"
    assert "researcher" in cmd.update["last_error"]
    assert cmd.update["next_agent"] == "FINISH"


def test_grafo_compensa_tras_agotar_retries():
    def boom(_state):
        raise RuntimeError("Provider returned error")

    graph = build_graph(
        supervisor=boom,
        researcher=lambda s: {},
        analyst=lambda s: {},
        writer=lambda s: {"last_agent": "writer"},
        retry_policy=RetryPolicy(max_attempts=1, retry_on=is_transient_error),
    )
    result = run_query(graph, "¿Qué se dice de LangGraph?")
    assert result["next_agent"] == "FINISH"
    assert "Provider returned error" in result["last_error"]
    assert result["last_agent"] == "writer"


def test_grafo_hitl_pausa_en_approval_tras_agotar_retries():
    writer_calls: list = []

    def boom(_state):
        raise RuntimeError("Provider returned error")

    def writer(state):
        writer_calls.append(state)
        return {"last_agent": "writer"}

    graph = build_graph(
        supervisor=boom,
        researcher=lambda s: {},
        analyst=lambda s: {},
        writer=writer,
        retry_policy=RetryPolicy(max_attempts=1, retry_on=is_transient_error),
        checkpointer=InMemorySaver(),
        enable_hitl=True,
    )
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = graph.invoke({**initial_fields(), "messages": []}, config)

    assert writer_calls == []
    assert graph.get_state(config).next == ("approval",)
    assert "Provider returned error" in result["last_error"]
