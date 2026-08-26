"""Topología del grafo: delegación researcher → analyst → writer → END, sin LLM."""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from agents.writer import make_writer_node, render_brief
from graph import build_graph, route_from_supervisor, run_query, stream_query
from state import initial_fields


def _noop_writer(_state):
    return {"last_agent": "writer"}


def test_route_finish_va_a_writer():
    assert route_from_supervisor({**initial_fields(), "next_agent": "FINISH"}) == "writer"


def test_route_nombres_de_nodo():
    assert route_from_supervisor({**initial_fields(), "next_agent": "researcher"}) == "researcher"
    assert route_from_supervisor({**initial_fields(), "next_agent": "analyst"}) == "analyst"


def test_flujo_feliz_researcher_luego_analyst():
    calls: list[str] = []

    def supervisor(state):
        calls.append("supervisor")
        notes = (state.get("research_notes") or "").strip()
        analysis = (state.get("analysis") or "").strip()
        if not notes:
            nxt = "researcher"
        elif not analysis:
            nxt = "analyst"
        else:
            nxt = "FINISH"
        return {
            "next_agent": nxt,
            "last_agent": "supervisor",
            "step_count": int(state.get("step_count") or 0) + 1,
        }

    def researcher(_state):
        calls.append("researcher")
        return {"research_notes": "brief tavily", "last_agent": "researcher"}

    def analyst(_state):
        calls.append("analyst")
        return {"analysis": "positivo 0.7", "last_agent": "analyst"}

    def writer(_state):
        calls.append("writer")
        return {"last_agent": "writer"}

    graph = build_graph(
        supervisor=supervisor,
        researcher=researcher,
        analyst=analyst,
        writer=writer,
    )
    result = run_query(graph, "¿Qué se dice de LangGraph esta semana?")

    assert calls == [
        "supervisor",
        "researcher",
        "supervisor",
        "analyst",
        "supervisor",
        "writer",
    ]
    assert result["research_notes"] == "brief tavily"
    assert result["analysis"] == "positivo 0.7"
    assert result["next_agent"] == "FINISH"
    assert result["step_count"] == 3
    assert result["last_agent"] == "writer"
    assert isinstance(result["messages"][0], HumanMessage)

    hops, streamed = stream_query(graph, "¿Qué se dice de LangGraph esta semana?")
    assert hops == [
        "supervisor",
        "researcher",
        "supervisor",
        "analyst",
        "supervisor",
        "writer",
    ]
    assert streamed["analysis"] == "positivo 0.7"


def test_writer_pisa_output_md(tmp_path):
    dest = tmp_path / "output.md"
    graph = build_graph(
        supervisor=lambda s: {
            "next_agent": "FINISH",
            "research_notes": "hallazgos",
            "analysis": "positivo 0.2",
        },
        researcher=lambda s: {},
        analyst=lambda s: {},
        writer=make_writer_node(dest),
        retry_policy=None,
    )
    run_query(graph, "¿Qué se dice de LangGraph esta semana?")
    text = dest.read_text(encoding="utf-8")
    assert "# Brief de mercado" in text
    assert "LangGraph" in text
    assert "hallazgos" in text
    assert "positivo 0.2" in text


def test_render_brief_incluye_last_error():
    blob = render_brief(
        {
            **initial_fields(),
            "messages": [HumanMessage(content="consulta")],
            "research_notes": "notas",
            "last_error": "429",
        }
    )
    assert "## last_error" in blob
    assert "429" in blob


def test_mermaid_incluye_rombo_del_supervisor():
    graph = build_graph(
        supervisor=lambda s: {"next_agent": "FINISH"},
        researcher=lambda s: {},
        analyst=lambda s: {},
        writer=_noop_writer,
    )
    mermaid = graph.get_graph().draw_mermaid()
    assert "supervisor" in mermaid
    assert "researcher" in mermaid
    assert "analyst" in mermaid
    assert "writer" in mermaid
