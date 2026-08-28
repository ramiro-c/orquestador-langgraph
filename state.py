"""Estado compartido del orquestador jerárquico (pre-entrega 6).

``MessagesState`` ya trae ``messages`` con reducer ``add_messages`` (append).
Los campos extra usan el reducer default: cada update **reemplaza** el valor.
Eso es lo que queremos para slots de especialistas: el researcher no pisa
``analysis``, y un re-run del analyst no duplica el brief anterior.
"""

from __future__ import annotations

from typing import Literal

from langgraph.graph import MessagesState

AgentName = Literal["researcher", "analyst"]
NextAgent = Literal["researcher", "analyst", "FINISH"]

# Freno anti-bucle: el grafo incrementa ``step_count`` en cada visita al
# supervisor y corta a FINISH si se alcanza este tope.
MAX_STEPS = 6


class OrchestratorState(MessagesState):
    """Contrato entre supervisor y especialistas.

    ``next_agent`` es lo que leen las aristas condicionales (nombres de nodo).
    ``research_notes`` / ``analysis`` son los slots por agente: quién aportó qué.
    """

    next_agent: NextAgent
    research_notes: str
    analysis: str
    last_agent: str
    step_count: int
    last_error: str
    output_path: str


def initial_fields() -> dict:
    """Defaults para el primer ``invoke``. ``messages`` lo pone el caller."""
    return {
        "next_agent": "FINISH",
        "research_notes": "",
        "analysis": "",
        "last_agent": "",
        "step_count": 0,
        "last_error": "",
        "output_path": "",
    }
