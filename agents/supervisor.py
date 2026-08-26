"""Supervisor: router + rúbrica. No investiga ni analiza; solo decide el próximo nodo.

La decisión del LLM es un ``Literal`` (nombres de nodo). ``apply_rubric`` la
corrige si viola las reglas duras: sin notes no hay FINISH, y ``MAX_STEPS``
corta el bucle. Eso es el antídoto al "Supervisor Infinito" de la consigna.
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from agents.context import user_query
from state import MAX_STEPS, NextAgent, OrchestratorState

SUPERVISOR_PROMPT = """Sos el supervisor de un orquestador de brief de mercado.
No busques en la web ni puntúes sentimiento. Elegí el próximo agente.

Rúbrica (en orden, la primera que aplique gana):
1. Si research_notes está vacío → researcher.
2. Si hay notes y analysis está vacío → analyst.
   Excepción: notes claramente insuficientes (muy cortas, sin fuentes) → researcher otra vez.
3. Si hay notes y analysis con label y score → FINISH.
4. Si el analysis dice que no hay evidencia o contradice las notes → analyst (refinar)
   o researcher (faltan datos). Nunca FINISH en ese caso.
5. Nunca elijas un agente que no exista. Opciones: researcher, analyst, FINISH.

Respondé solo con next_agent y una rationale corta (una frase).
"""


class SupervisorDecision(BaseModel):
    next_agent: NextAgent = Field(
        description="Nodo siguiente: researcher, analyst o FINISH."
    )
    rationale: str = Field(description="Por qué esa elección, una frase.")


def apply_rubric(
    research_notes: str,
    analysis: str,
    step_count: int,
    proposed: NextAgent,
    last_error: str = "",
) -> NextAgent:
    """Reglas duras encima del LLM. El grafo nunca ve un next_agent ilegal."""
    if last_error.strip():
        return "FINISH"
    if step_count >= MAX_STEPS:
        return "FINISH"
    notes = research_notes.strip()
    analysis_text = analysis.strip()
    if not notes:
        return "researcher"
    if not analysis_text and proposed == "FINISH":
        return "analyst"
    return proposed


def _snapshot(state: OrchestratorState) -> str:
    notes = (state.get("research_notes") or "").strip() or "(vacío)"
    analysis = (state.get("analysis") or "").strip() or "(vacío)"
    last_agent = state.get("last_agent") or "(nadie)"
    step_count = int(state.get("step_count") or 0)
    last_error = (state.get("last_error") or "").strip() or "(ninguno)"
    return (
        f"Consulta: {user_query(state['messages'])}\n"
        f"last_agent: {last_agent}\n"
        f"step_count: {step_count}/{MAX_STEPS}\n"
        f"last_error: {last_error}\n\n"
        f"research_notes:\n{notes}\n\n"
        f"analysis:\n{analysis}"
    )


def supervisor_turn(state: OrchestratorState, llm: BaseChatModel) -> dict:
    step_count = int(state.get("step_count") or 0) + 1
    last_error = (state.get("last_error") or "").strip()
    if last_error:
        rationale = f"Hay un last_error: no reintento el mismo nodo. {last_error}"
        next_agent: NextAgent = "FINISH"
    elif step_count >= MAX_STEPS:
        rationale = f"Tope de {MAX_STEPS} pasos: cierro para no loopear."
        next_agent = "FINISH"
    else:
        decision = llm.with_structured_output(SupervisorDecision).invoke(
            [
                SystemMessage(content=SUPERVISOR_PROMPT),
                HumanMessage(content=_snapshot({**state, "step_count": step_count})),
            ]
        )
        next_agent = apply_rubric(
            research_notes=state.get("research_notes") or "",
            analysis=state.get("analysis") or "",
            step_count=step_count,
            proposed=decision.next_agent,
            last_error=last_error,
        )
        rationale = decision.rationale
        if next_agent != decision.next_agent:
            rationale = f"{rationale} [rúbrica: {decision.next_agent} → {next_agent}]"

    return {
        "messages": [AIMessage(content=rationale, name="supervisor")],
        "next_agent": next_agent,
        "step_count": step_count,
        "last_agent": "supervisor",
    }


def make_supervisor_node(llm: BaseChatModel):
    def supervisor_node(state: OrchestratorState) -> dict:
        return supervisor_turn(state, llm)

    return supervisor_node
