"""Agente de análisis: puntúa sentimiento sobre ``research_notes``.

La fórmula vive en ``compute_sentiment_score`` (determinista). El LLM solo
cuenta menciones y llama la tool: no inventa el score.
"""

from __future__ import annotations

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

from agents.context import last_ai_text
from state import OrchestratorState

ANALYST_PROMPT = (
    "Sos un analista. No busques en la web. Trabajás solo con las notas de "
    "investigación que te pasan. Contá cuántas menciones son positivas, "
    "negativas o neutrales (cada hallazgo o quote cuenta una vez) y llamá "
    "puntuar_sentimiento con esos enteros. Después redactá un análisis corto "
    "en español: label, score, y 2-3 evidencias tomadas de las notas. "
    "Si no hay notas, decí que no hay evidencia."
)


def compute_sentiment_score(
    positivos: int, negativos: int, neutrales: int
) -> dict:
    """Score en [-1, 1] = (positivos - negativos) / total."""
    if min(positivos, negativos, neutrales) < 0:
        return {"error": "los conteos no pueden ser negativos"}
    total = positivos + negativos + neutrales
    if total == 0:
        return {
            "label": "neutral",
            "score": 0.0,
            "total": 0,
            "error": "sin evidencia",
        }
    score = (positivos - negativos) / total
    if score > 0.15:
        label = "positivo"
    elif score < -0.15:
        label = "negativo"
    else:
        label = "neutral"
    return {
        "label": label,
        "score": round(score, 3),
        "total": total,
        "positivos": positivos,
        "negativos": negativos,
        "neutrales": neutrales,
    }


@tool
def puntuar_sentimiento(
    menciones_positivas: int,
    menciones_negativas: int,
    menciones_neutrales: int,
) -> dict:
    """Calcula el score de sentimiento a partir de conteos de menciones.

    Contá en las notas cuántos hallazgos/quotes son positivos, negativos o
    neutrales y pasá esos enteros (>= 0). No inventes conteos.

    Returns:
        Dict con label (positivo|neutral|negativo), score en [-1, 1] y total.
        Si no hay menciones, incluye error "sin evidencia".
    """
    return compute_sentiment_score(
        menciones_positivas, menciones_negativas, menciones_neutrales
    )


def build_analyst_agent(llm: BaseChatModel):
    return create_agent(llm, tools=[puntuar_sentimiento], system_prompt=ANALYST_PROMPT)


def analyst_turn(state: OrchestratorState, agent) -> dict:
    notes = (state.get("research_notes") or "").strip()
    if not notes:
        empty = "No hay notas de investigación: no puedo puntuar sentimiento."
        return {
            "messages": [AIMessage(content=empty, name="analyst")],
            "analysis": empty,
            "last_agent": "analyst",
        }
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Analizá el sentimiento de estas notas de investigación."
                        f"\n\n{notes}"
                    ),
                }
            ]
        }
    )
    analysis = last_ai_text(result["messages"])
    return {
        "messages": [AIMessage(content=analysis, name="analyst")],
        "analysis": analysis,
        "last_agent": "analyst",
    }


def make_analyst_node(llm: BaseChatModel):
    agent = build_analyst_agent(llm)

    def analyst_node(state: OrchestratorState) -> dict:
        return analyst_turn(state, agent)

    return analyst_node
