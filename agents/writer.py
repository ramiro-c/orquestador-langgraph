"""Nodo sink: pisa ``output.md`` con el research (notes + analysis)."""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import AIMessage

from agents.context import user_query
from config import BASE_DIR
from state import OrchestratorState

OUTPUT_PATH = BASE_DIR / "output.md"


def render_brief(state: OrchestratorState) -> str:
    query = user_query(state.get("messages") or []) or "(sin consulta)"
    notes = (state.get("research_notes") or "").strip() or "(vacío)"
    analysis = (state.get("analysis") or "").strip() or "(vacío)"
    last_error = (state.get("last_error") or "").strip()
    parts = [
        "# Research",
        "",
        "## Consulta",
        "",
        query,
        "",
        "## research_notes",
        "",
        notes,
        "",
        "## analysis",
        "",
        analysis,
        "",
    ]
    if last_error:
        parts.extend(["## last_error", "", last_error, ""])
    return "\n".join(parts)


def writer_turn(state: OrchestratorState, path: Path) -> dict:
    path.write_text(render_brief(state), encoding="utf-8")
    return {
        "messages": [AIMessage(content=f"Research escrito en {path.name}", name="writer")],
        "last_agent": "writer",
    }


def make_writer_node(path: Path | None = None):
    dest = path or OUTPUT_PATH

    def writer_node(state: OrchestratorState) -> dict:
        return writer_turn(state, dest)

    return writer_node
