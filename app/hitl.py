"""Nodo HITL: pausa el grafo antes del writer para que un humano lo apruebe."""

from __future__ import annotations

from langgraph.types import interrupt

from agents.context import user_query
from state import OrchestratorState


def approval_node(state: OrchestratorState) -> dict:
    """Expone notes/analysis y se pausa; ``Command(resume=...)`` la destraba."""
    interrupt(
        {
            "action": "write_research",
            "query": user_query(state.get("messages") or []),
            "research_notes": state.get("research_notes") or "",
            "analysis": state.get("analysis") or "",
            "last_error": state.get("last_error") or "",
        }
    )
    return {"last_agent": "approval"}
