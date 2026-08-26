"""Los wrappers aíslan contexto: cada especialista ve solo su tarea."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from agents.analyst_agent import analyst_turn
from agents.research_agent import researcher_turn
from state import initial_fields


class FakeAgent:
    def __init__(self, reply: str = "brief"):
        self.reply = reply
        self.seen: list = []

    def invoke(self, payload):
        self.seen.append(payload)
        return {"messages": [AIMessage(content=self.reply)]}


def _state(**overrides):
    return {
        **initial_fields(),
        "messages": [HumanMessage(content="¿Qué se dice de LangGraph esta semana?")],
        **overrides,
    }


def _task_text(payload: dict) -> str:
    message = payload["messages"][0]
    if isinstance(message, dict):
        return message["content"]
    return message[1]


def test_researcher_no_ve_analysis_ni_el_historial_del_grafo():
    agent = FakeAgent("notas tavily")
    out = researcher_turn(
        _state(
            analysis="NO DEBERIA APARECER",
            messages=[
                HumanMessage(content="¿Qué se dice de LangGraph esta semana?"),
                AIMessage(content="ruido del supervisor"),
            ],
        ),
        agent,
    )
    task = _task_text(agent.seen[0])
    assert "LangGraph" in task
    assert "NO DEBERIA APARECER" not in task
    assert "ruido del supervisor" not in task
    assert "no rechaces" in task.lower()
    assert out["research_notes"] == "notas tavily"
    assert out["last_agent"] == "researcher"
    assert out["messages"][0].name == "researcher"


def test_researcher_ignora_el_pedido_de_sentimiento():
    agent = FakeAgent("brief")
    researcher_turn(
        _state(
            messages=[
                HumanMessage(
                    content="Noticias de Grok vs Hermes y el sentimiento de la gente"
                )
            ]
        ),
        agent,
    )
    task = _task_text(agent.seen[0])
    assert "Grok" in task
    assert "ignorá" in task.lower() or "ignora" in task.lower()
    assert "no rechaces" in task.lower()


def test_researcher_refina_si_ya_hay_notas():
    agent = FakeAgent("notas v2")
    researcher_turn(_state(research_notes="notas v1 incompletas"), agent)
    task = _task_text(agent.seen[0])
    assert "notas v1 incompletas" in task
    assert "refiná" in task.lower() or "específic" in task.lower()


def test_analyst_solo_ve_research_notes():
    agent = FakeAgent("análisis ok")
    out = analyst_turn(
        _state(
            research_notes="Hallazgo: LangGraph es estable.",
            messages=[
                HumanMessage(content="¿Qué se dice de LangGraph esta semana?"),
                AIMessage(content="ruido del supervisor"),
            ],
        ),
        agent,
    )
    task = _task_text(agent.seen[0])
    assert "LangGraph es estable" in task
    assert "ruido del supervisor" not in task
    assert out["analysis"] == "análisis ok"
    assert out["last_agent"] == "analyst"


def test_analyst_sin_notas_no_invoca_al_agente():
    agent = FakeAgent("no deberia")
    out = analyst_turn(_state(research_notes=""), agent)
    assert agent.seen == []
    assert "no hay notas" in out["analysis"].lower()
    assert out["last_agent"] == "analyst"
