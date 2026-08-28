"""Grafo con HITL: FINISH -> approval -> writer, con InMemorySaver, sin LLM/Tavily."""

from __future__ import annotations

import uuid

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from graph import build_graph, run_query
from state import initial_fields


def _dummy_nodes(writer_calls: list):
    def supervisor(state):
        return {"next_agent": "FINISH", "last_agent": "supervisor"}

    def researcher(_state):
        return {}

    def analyst(_state):
        return {}

    def writer(state):
        writer_calls.append(state)
        return {"last_agent": "writer"}

    return supervisor, researcher, analyst, writer


def _hitl_config() -> dict:
    return {"configurable": {"thread_id": str(uuid.uuid4())}}


def test_enable_hitl_sin_checkpointer_falla():
    supervisor, researcher, analyst, writer = _dummy_nodes([])
    with pytest.raises(ValueError):
        build_graph(
            supervisor=supervisor,
            researcher=researcher,
            analyst=analyst,
            writer=writer,
            retry_policy=None,
            enable_hitl=True,
        )


def test_hitl_pausa_antes_del_writer():
    writer_calls: list = []
    supervisor, researcher, analyst, writer = _dummy_nodes(writer_calls)
    graph = build_graph(
        supervisor=supervisor,
        researcher=researcher,
        analyst=analyst,
        writer=writer,
        retry_policy=None,
        checkpointer=InMemorySaver(),
        enable_hitl=True,
    )
    config = _hitl_config()

    result = graph.invoke({**initial_fields(), "messages": []}, config)

    assert "__interrupt__" in result
    assert graph.get_state(config).next == ("approval",)
    assert writer_calls == []


def test_hitl_resume_corre_writer():
    writer_calls: list = []
    supervisor, researcher, analyst, writer = _dummy_nodes(writer_calls)
    graph = build_graph(
        supervisor=supervisor,
        researcher=researcher,
        analyst=analyst,
        writer=writer,
        retry_policy=None,
        checkpointer=InMemorySaver(),
        enable_hitl=True,
    )
    config = _hitl_config()
    graph.invoke({**initial_fields(), "messages": []}, config)

    result = graph.invoke(Command(resume=True), config)

    assert writer_calls != []
    assert result["last_agent"] == "writer"
    assert graph.get_state(config).next == ()


def test_build_graph_sin_hitl_conserva_topologia():
    writer_calls: list = []
    supervisor, researcher, analyst, writer = _dummy_nodes(writer_calls)
    graph = build_graph(
        supervisor=supervisor,
        researcher=researcher,
        analyst=analyst,
        writer=writer,
        retry_policy=None,
    )
    result = run_query(graph, "¿Qué se dice de LangGraph?")
    assert writer_calls != []
    assert result["last_agent"] == "writer"
    assert "approval" not in graph.get_graph().nodes
