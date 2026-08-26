"""Rúbrica del supervisor: reglas duras, sin LLM."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from agents.supervisor import SupervisorDecision, apply_rubric, supervisor_turn
from state import MAX_STEPS, initial_fields


def test_sin_notes_nunca_finish():
    assert (
        apply_rubric(
            research_notes="",
            analysis="",
            step_count=1,
            proposed="FINISH",
        )
        == "researcher"
    )


def test_sin_analysis_finish_cae_a_analyst():
    assert (
        apply_rubric(
            research_notes="hallazgos con fuentes",
            analysis="",
            step_count=2,
            proposed="FINISH",
        )
        == "analyst"
    )


def test_sin_analysis_puede_refinar_researcher():
    assert (
        apply_rubric(
            research_notes="muy poco",
            analysis="",
            step_count=2,
            proposed="researcher",
        )
        == "researcher"
    )


def test_ambos_slots_respeta_finish():
    assert (
        apply_rubric(
            research_notes="brief",
            analysis="positivo 0.7",
            step_count=3,
            proposed="FINISH",
        )
        == "FINISH"
    )


def test_tope_de_pasos_gana():
    assert (
        apply_rubric(
            research_notes="",
            analysis="",
            step_count=MAX_STEPS,
            proposed="researcher",
        )
        == "FINISH"
    )


def test_last_error_fuerza_finish():
    assert (
        apply_rubric(
            research_notes="",
            analysis="",
            step_count=1,
            proposed="researcher",
            last_error="Provider returned error",
        )
        == "FINISH"
    )


class _FakeStructured:
    def __init__(self, decision: SupervisorDecision):
        self.decision = decision
        self.calls = 0

    def invoke(self, _messages):
        self.calls += 1
        return self.decision


class _FakeLLM:
    def __init__(self, next_agent="FINISH", rationale="listo"):
        self.structured = _FakeStructured(
            SupervisorDecision(next_agent=next_agent, rationale=rationale)
        )

    def with_structured_output(self, _schema):
        return self.structured


def _state(**overrides):
    return {
        **initial_fields(),
        "messages": [HumanMessage(content="¿Qué se dice de LangGraph?")],
        **overrides,
    }


def test_supervisor_no_llama_llm_si_hay_last_error():
    llm = _FakeLLM(next_agent="researcher")
    out = supervisor_turn(_state(last_error="Provider returned error"), llm)
    assert llm.structured.calls == 0
    assert out["next_agent"] == "FINISH"
    assert out["last_agent"] == "supervisor"
    llm = _FakeLLM(next_agent="researcher")
    out = supervisor_turn(_state(step_count=MAX_STEPS - 1), llm)
    assert llm.structured.calls == 0
    assert out["next_agent"] == "FINISH"
    assert out["step_count"] == MAX_STEPS
    assert out["last_agent"] == "supervisor"


def test_supervisor_corrige_finish_sin_notes_y_anota_rubrica():
    llm = _FakeLLM(next_agent="FINISH", rationale="ya está")
    out = supervisor_turn(_state(), llm)
    assert out["next_agent"] == "researcher"
    assert "rúbrica" in out["messages"][0].content
    assert llm.structured.calls == 1


def test_supervisor_snapshot_no_manda_el_chat_del_grafo():
    captured = []

    class Spy(_FakeStructured):
        def invoke(self, messages):
            captured.extend(messages)
            return super().invoke(messages)

    llm = _FakeLLM()
    llm.structured = Spy(SupervisorDecision(next_agent="researcher", rationale="faltan notes"))
    supervisor_turn(
        _state(
            messages=[
                HumanMessage(content="¿Qué se dice de LangGraph?"),
                AIMessage(content="ruido interno que el supervisor no debería reenviar crudo"),
            ]
        ),
        llm,
    )
    blob = "\n".join(getattr(m, "content", "") for m in captured)
    assert "LangGraph" in blob
    assert "ruido interno que el supervisor no debería reenviar crudo" not in blob
