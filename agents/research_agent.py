"""Agente de investigación: TavilySearch, escribe solo ``research_notes``.

El ReAct interno puede tener muchos mensajes (AI + tool). El nodo wrapper
descarta ese historial y publica un brief en el slot del state. El analyst
nunca ve las tool calls de Tavily.
"""

from __future__ import annotations

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

from agents.context import last_ai_text, user_query
from config import TAVILY_API_KEY
from state import OrchestratorState

RESEARCHER_PROMPT = (
    "Sos un investigador. Tu única herramienta es la búsqueda web (Tavily). "
    "Siempre buscá y armá el brief: nunca rechaces la consulta. "
    "Si el usuario pide sentimiento, recomendaciones u otra cosa, ignorá esa "
    "parte: otro agente se encarga. Vos solo hechos. "
    "No analices sentimiento, no des recomendaciones, no inventes fuentes. "
    "Devolvé un brief en español con: (1) hallazgos en bullets, "
    "(2) quotes cortos, (3) fuentes con título y URL. "
    "Si te pasan notas previas, refiná la búsqueda; no copies el brief igual."
)


def build_research_agent(llm: BaseChatModel):
    from langchain_tavily import TavilySearch

    kwargs: dict = {"max_results": 5, "search_depth": "basic", "include_answer": True}
    if TAVILY_API_KEY:
        kwargs["tavily_api_key"] = TAVILY_API_KEY
    tavily = TavilySearch(**kwargs)
    return create_agent(llm, tools=[tavily], system_prompt=RESEARCHER_PROMPT)


def _task_from_state(state: OrchestratorState) -> str:
    query = user_query(state["messages"])
    notes = (state.get("research_notes") or "").strip()
    task = (
        "Armá el brief de hechos/noticias. Si la consulta pide sentimiento u "
        "otra cosa, ignorá esa parte: no rechaces, no analices. "
        f"\n\nConsulta:\n{query}"
    )
    if notes:
        task += (
            "\n\nNotas previas (refiná con una query más específica, "
            f"no copies igual):\n{notes}"
        )
    return task


def researcher_turn(state: OrchestratorState, agent) -> dict:
    """Invoca el ReAct con la tarea aislada y publica ``research_notes``."""
    result = agent.invoke(
        {"messages": [{"role": "user", "content": _task_from_state(state)}]}
    )
    notes = last_ai_text(result["messages"])
    return {
        "messages": [AIMessage(content=notes, name="researcher")],
        "research_notes": notes,
        "last_agent": "researcher",
    }


def make_researcher_node(llm: BaseChatModel):
    agent = build_research_agent(llm)

    def researcher_node(state: OrchestratorState) -> dict:
        return researcher_turn(state, agent)

    return researcher_node
